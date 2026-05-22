import asyncio
import logging
import httpx
import aiofiles
from tqdm.asyncio import tqdm

from src.bast_parser.config import OUTPUT_DIR, HEADERS, REQUEST_TIMEOUT, MAX_CONCURRENT_TASKS
from src.bast_parser.models.product import Offer
from src.bast_parser.api_client.client import fetch_products
from src.bast_parser.parser.html_parser import get_markdown_from_url, close_browser
from src.bast_parser.parser.pdf_parser import get_text_from_pdf_url
from src.bast_parser.builder.markdown_builder import create_markdown_file_content

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parser.log"),
        logging.StreamHandler()
    ]
)

async def process_product(offer: Offer, client: httpx.AsyncClient, semaphore: asyncio.Semaphore):
    """A single worker task to process one product offer."""
    async with semaphore:
        try:
            vendor_code = offer.vendorCode
            logging.info(f"Processing product with article: {vendor_code}")

            # 1. Parse product page HTML to Markdown
            product_page_md = await get_markdown_from_url(str(offer.url), client)
            if not product_page_md:
                logging.warning(f"Could not get Markdown for product {vendor_code}. Skipping.")
                return

            # 2. Parse user manual PDF if available
            manual_text = ""
            if offer.documents and offer.documents.documentsUserManual:
                manual_text = await get_text_from_pdf_url(str(offer.documents.documentsUserManual), client)
            else:
                logging.info(f"No user manual PDF found for product {vendor_code}.")

            # 3. Build the final Markdown file content
            final_content = create_markdown_file_content(offer, product_page_md, manual_text)

            # 4. Save the file asynchronously
            file_path = OUTPUT_DIR / f"{vendor_code}.md"
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(final_content)
            
            logging.info(f"Successfully saved knowledge base for article: {vendor_code}")

        except Exception as e:
            logging.error(f"An error occurred while processing article {offer.vendorCode}: {e}")

async def run_parser():
    """Main function to orchestrate the ETL process, callable from other modules."""
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)
    logging.info(f"Output directory set to: {OUTPUT_DIR}")

    # Use a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    try:
        # Use a single httpx client for all requests
        async with httpx.AsyncClient(headers=HEADERS, timeout=REQUEST_TIMEOUT, http2=True, follow_redirects=True) as client:
            products = await fetch_products(client)
            
            if not products:
                logging.warning("No products found to process. Exiting.")
                return

            tasks = [process_product(offer, client, semaphore) for offer in products]
            
            # Run tasks with a progress bar
            logging.info(f"Starting processing for {len(products)} products...")
            for f in tqdm.as_completed(tasks, total=len(tasks), desc="Generating Knowledge Base"):
                await f
    finally:
        # Clean up global playwright browser
        await close_browser()

    logging.info("ETL process completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_parser())