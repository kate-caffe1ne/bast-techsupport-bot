import httpx
import logging
from typing import List

from src.bast_parser.config import API_URL, HEADERS
from src.bast_parser.models.product import CatalogResponse, Offer

logger = logging.getLogger(__name__)

async def fetch_products(client: httpx.AsyncClient) -> List[Offer]:
    """Fetches the catalog from the API and returns a flat list of product offers."""
    try:
        logger.info(f"Fetching catalog from {API_URL}")
        response = await client.get(API_URL, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        catalog_data = CatalogResponse.model_validate(data)
        
        products = []
        for section in catalog_data.catalog:
            for subsection in section.subsections:
                if subsection.offer and subsection.offer.removed == 'false':
                    products.append(subsection.offer)
        
        logger.info(f"Successfully fetched and parsed {len(products)} active products.")
        return products

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while fetching catalog: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during API request: {e}")
    
    return []