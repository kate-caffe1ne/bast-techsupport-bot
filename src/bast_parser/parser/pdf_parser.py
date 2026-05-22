import httpx
import logging
import pymupdf

logger = logging.getLogger(__name__)

async def get_text_from_pdf_url(url: str, client: httpx.AsyncClient) -> str:
    """Downloads a PDF from a URL and extracts its text content."""
    try:
        response = await client.get(url)
        response.raise_for_status()
        pdf_bytes = response.content

        text_content = []
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text_content.append(page.get_text())
        
        full_text = "\n".join(text_content)
        # Basic cleaning: remove excessive blank lines
        cleaned_text = "\n".join(line for line in full_text.splitlines() if line.strip())
        return cleaned_text

    except httpx.RequestError as e:
        logger.error(f"Failed to download PDF from {url}: {e}")
    except Exception as e:
        logger.error(f"Failed to parse PDF from {url}: {e}")
    return ""