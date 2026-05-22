import asyncio
import logging
import httpx
import aiofiles
from tqdm.asyncio import tqdm
import sys
from typing import Optional, Union

from src.bast_parser.config import OUTPUT_DIR, HEADERS, REQUEST_TIMEOUT, MAX_CONCURRENT_TASKS
from src.bast_parser.models.product import Offer
from src.bast_parser.api_client.client import fetch_products
from src.bast_parser.parser.html_parser import get_markdown_from_url, close_browser
from src.bast_parser.parser.pdf_parser import get_text_from_pdf_url
from src.bast_parser.builder.markdown_builder import create_markdown_file_content

# --- Logging Configuration ---
class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg, file=sys.stderr)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

for handler in logger.handlers[:]:
    logger.removeHandler(handler)

tqdm_handler = TqdmLoggingHandler()
tqdm_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(tqdm_handler)

file_handler = logging.FileHandler("parser.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

logging.getLogger("httpx").setLevel(logging.WARNING)

# Suppress noisy asyncio and playwright logs during shutdown
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("playwright").setLevel(logging.CRITICAL)
# --- End of Logging Configuration ---


async def process_product(offer: Offer, client: httpx.AsyncClient, semaphore: asyncio.Semaphore, pbar: tqdm):
    """A single worker task to process one product offer."""
    async with semaphore:
        try:
            vendor_code = offer.vendorCode
            pbar.set_description(f"Processing article: {vendor_code}")

            product_page_md = await get_markdown_from_url(str(offer.url), client)
            if not product_page_md:
                logging.warning(f"Could not get Markdown for product {vendor_code}. Skipping.")
                return

            manual_text = ""
            if offer.documents and offer.documents.documentsUserManual:
                manual_text = await get_text_from_pdf_url(str(offer.documents.documentsUserManual), client)

            final_content = create_markdown_file_content(offer, product_page_md, manual_text)

            file_path = OUTPUT_DIR / f"{vendor_code}.md"
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(final_content)
            
        except asyncio.CancelledError:
            # This exception is raised when the main task is cancelled (e.g., by Ctrl+C).
            # We log it quietly and let the application shut down.
            logging.debug(f"Task for article {offer.vendorCode} was cancelled.")
            raise  # Re-raise to ensure the task is properly marked as cancelled
        except Exception as e:
            logging.error(f"An error occurred while processing article {offer.vendorCode}: {e}")
        finally:
            pbar.update(1)


async def run_parser(target_vendor_code: Optional[Union[str, int]] = None):
    """Main function to orchestrate the ETL process, callable from other modules."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    logging.info(f"Output directory set to: {OUTPUT_DIR}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    tasks = []

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=REQUEST_TIMEOUT, http2=True, follow_redirects=True) as client:
            products = await fetch_products(client)
            
            if not products:
                logging.warning("No products found to process. Exiting.")
                return

            if target_vendor_code is not None:
                target_str = str(target_vendor_code)
                products = [p for p in products if str(p.vendorCode) == target_str]
                if not products:
                    logging.warning(f"Product with vendorCode {target_vendor_code} not found in catalog. Exiting.")
                    return
                logging.info(f"Test mode enabled: Only parsing article {target_vendor_code}.")

            with tqdm(total=len(products), desc="Initializing...", file=sys.stdout) as pbar:
                # Create actual task objects so we can cancel them properly later if needed
                tasks = [asyncio.create_task(process_product(offer, client, semaphore, pbar)) for offer in products]
                await asyncio.gather(*tasks)

    except asyncio.CancelledError:
        # Cancel all pending tasks cleanly
        for task in tasks:
            if not task.done():
                task.cancel()
        raise

    finally:
        logging.info("Closing browser...")
        # Catch any residual playwright exceptions during shutdown
        try:
            await close_browser()
        except Exception as e:
            logging.debug(f"Exception during browser close: {e}")

    logging.info("ETL process completed successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(run_parser())
    except KeyboardInterrupt:
        print("\nПроцесс парсинга остановлен пользователем. Завершение...")
    except asyncio.CancelledError:
        print("\nПроцесс был отменен. Завершение...")