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
# We need a custom handler to prevent tqdm from being disrupted by log messages.
class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg, file=sys.stderr)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

# Get the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove all existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add our custom handler for console output
tqdm_handler = TqdmLoggingHandler()
tqdm_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(tqdm_handler)

# Add a file handler to still save logs to a file
file_handler = logging.FileHandler("parser.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Disable httpx logging to avoid spamming the console with download progress
logging.getLogger("httpx").setLevel(logging.WARNING)
# --- End of Logging Configuration ---


async def process_product(offer: Offer, client: httpx.AsyncClient, semaphore: asyncio.Semaphore, pbar: tqdm):
    """A single worker task to process one product offer."""
    async with semaphore:
        try:
            vendor_code = offer.vendorCode
            # Use pbar.set_description() to update the progress bar with the current article
            pbar.set_description(f"Processing article: {vendor_code}")

            # 1. Parse product page HTML to Markdown
            product_page_md = await get_markdown_from_url(str(offer.url), client)
            if not product_page_md:
                logging.warning(f"Could not get Markdown for product {vendor_code}. Skipping.")
                return

            # 2. Parse user manual PDF if available
            manual_text = ""
            if offer.documents and offer.documents.documentsUserManual:
                manual_text = await get_text_from_pdf_url(str(offer.documents.documentsUserManual), client)

            # 3. Build the final Markdown file content
            final_content = create_markdown_file_content(offer, product_page_md, manual_text)

            # 4. Save the file asynchronously
            file_path = OUTPUT_DIR / f"{vendor_code}.md"
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(final_content)
            
        except Exception as e:
            logging.error(f"An error occurred while processing article {offer.vendorCode}: {e}")
        finally:
            # Update the main progress bar counter
            pbar.update(1)


async def run_parser(target_vendor_code: Optional[Union[str, int]] = None):
    """Main function to orchestrate the ETL process, callable from other modules.
    
    Args:
        target_vendor_code: If provided, only parse the product with this vendorCode.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    logging.info(f"Output directory set to: {OUTPUT_DIR}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

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

            # Initialize tqdm progress bar
            with tqdm(total=len(products), desc="Initializing...", file=sys.stdout) as pbar:
                tasks = [process_product(offer, client, semaphore, pbar) for offer in products]
                await asyncio.gather(*tasks)

    finally:
        await close_browser()

    logging.info("ETL process completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_parser())