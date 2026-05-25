import logging
import httpx
from bs4 import BeautifulSoup
import html2text
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import re

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
            # Добавляем таймаут на запуск самого браузера для диагностики
            timeout=60000, # 60 секунд
            args=[
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                # Явное отключение DBus
                '--disable-dbus'
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
        if _browser is None or not _browser.is_connected():
            logger.info("Browser is disconnected, re-initializing...")
            await close_browser()
            await init_browser()
            
        context = None
        try:
            context = await _browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            try:
                await page.wait_for_selector('div.tab-content', timeout=20000)
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
            
            # --- Custom Content Cleaning ---
            
            # 1. Remove the product image gallery
            gallery = soup.find('div', class_='product-gallery')
            if gallery:
                gallery.decompose()

            # 2. Format breadcrumbs
            breadcrumbs_div = soup.find('div', class_='crumbs-field')
            breadcrumbs_text = ""
            if breadcrumbs_div:
                crumbs = [a.get_text(strip=True) for a in breadcrumbs_div.find_all('a') if a.get_text(strip=True)]
                if len(crumbs) > 1:
                    breadcrumbs_text = " / ".join(crumbs[1:])
                breadcrumbs_div.decompose()

            # 3. Extract and format product options/variants
            options_div = soup.find('div', class_='product-options')
            options_text = ""
            if options_div:
                option_nodes = []
                
                # Попытка 1: извлечь div элементы 3-го уровня вложенности
                # (соответствует body > ... > div.product-options.mt-4 > div > div > div)
                level_1 = options_div.find_all('div', recursive=False)
                for div1 in level_1:
                    level_2 = div1.find_all('div', recursive=False)
                    for div2 in level_2:
                        option_nodes.extend(div2.find_all('div', recursive=False))
                
                # Попытка 2: если вложенных div-ов нет, ищем <label>
                if not option_nodes:
                    option_nodes = options_div.find_all('label')
                
                # Попытка 3: если нет label, ищем просто <span>
                if not option_nodes:
                    option_nodes = options_div.find_all('span')
                
                if option_nodes:
                    options = []
                    for node in option_nodes:
                        # get_text(separator=" ") гарантирует, что 1500 и ВА,
                        # если они на разных строках или в разных тегах внутри ноды,
                        # объединятся через пробел, а не разорвутся.
                        text = node.get_text(separator=" ", strip=True)
                        text = re.sub(r'\s+', ' ', text) # убираем множественные пробелы
                        if text and text.lower() not in ["разновидности:", "опции:", "варианты:"]:
                            options.append(text)
                    
                    # Удаляем дубликаты (актуально, если собирали по <span> и они были вложенными)
                    seen = set()
                    unique_options = []
                    for opt in options:
                        if opt not in seen:
                            unique_options.append(opt)
                            seen.add(opt)
                            
                    options_text = " / ".join(unique_options)

                options_div.decompose() # Remove the original div to avoid duplication
            
            # 4. Target the main content area
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
            
            # Prepend the formatted breadcrumbs and options to the final markdown
            final_markdown = f"**Путь:** {breadcrumbs_text}\n\n"
            if options_text:
                final_markdown += f"**Разновидности:** {options_text}\n\n"
            final_markdown += h.handle(cleaned_html)

            return final_markdown
            
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
            if "has been closed" in str(e) or "Target closed" in str(e):
                await close_browser()
            
            if attempt < retries - 1:
                continue
            break

    return ""