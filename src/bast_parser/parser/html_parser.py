import logging
import httpx
from bs4 import BeautifulSoup
import html2text
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

_playwright = None
_browser = None

async def init_browser():
    global _playwright, _browser
    if _playwright is None:
        p = await async_playwright().start()
        _playwright = p
        _browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions'
            ]
        )

async def close_browser():
    global _playwright, _browser
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None

async def get_markdown_from_url(url: str, client: httpx.AsyncClient, retries: int = 3) -> str:
    """Fetches a product page and converts its specific tab content to Markdown using Playwright."""
    global _browser
    
    for attempt in range(retries):
        # Re-initialize browser if it crashed or was closed
        if _browser is None or not _browser.is_connected():
            logger.info("Browser is disconnected, re-initializing...")
            await close_browser()
            await init_browser()
            
        context = None
        page = None
        try:
            context = await _browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            # Using domcontentloaded because we need JS to execute
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            try:
                # Wait for the tab-content to exist
                await page.wait_for_selector('div.tab-content', timeout=20000)
                
                # Specifically wait for the Javascript to finish replacing "Загрузка..."
                await page.wait_for_function(
                    '''() => {
                        const el = document.querySelector("div.tab-content");
                        return el && !el.innerText.includes("Загрузка");
                    }''',
                    timeout=20000
                )
                await page.wait_for_timeout(2000)
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout waiting for 'Загрузка...' to disappear on {url}")
            
            html_content = await page.content()
            await context.close()

            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Target the specific container that holds the product information
            main_content = soup.select_one('body > div.container.p-0 > div.row.mt-1.mt-xl-5 > div.col-lg-9.order-1.order-lg-2 > main > div')
            
            if not main_content:
                main_content = soup.find('div', class_='tab-content')
                
            if main_content:
                for tag in main_content(["script", "style"]):
                    tag.extract()
                cleaned_html = str(main_content)
            else:
                logger.warning(f"Target div.tab-content not found on {url}, falling back to full page clean.")
                for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
                    tag.extract()
                cleaned_html = str(soup)

            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0 
            return h.handle(cleaned_html)
            
        except PlaywrightTimeoutError as e:
            if context:
                await context.close()
            if attempt < retries - 1:
                logger.warning(f"PlaywrightTimeoutError on attempt {attempt+1} for {url}. Retrying...")
                continue
            logger.error(f"Timeout failed to parse HTML from {url} after {retries} attempts.")
        except Exception as e:
            if context:
                try:
                    await context.close()
                except:
                    pass
            logger.error(f"Exception on attempt {attempt+1} for {url}: {e}")
            # If the browser crashed ("Target page, context or browser has been closed"), 
            # force a restart of the browser on the next retry
            if "has been closed" in str(e) or "Target closed" in str(e):
                await close_browser()
            
            if attempt < retries - 1:
                continue
            break

    return ""