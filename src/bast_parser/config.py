from pathlib import Path

# API and Network Configuration
API_URL = "https://cnr.bast.ru/api/v2/catalog.json"
HEADERS = {"Accept": "application/json"}
REQUEST_TIMEOUT = 30.0

# Concurrency settings
# Установлено значение 1. Как только мы ставим 2, сервер bast.ru
# обрывает соединения (net::ERR_TIMED_OUT и net::ERR_ABORTED), расценивая
# параллельные запросы от Playwright как атаку.
MAX_CONCURRENT_TASKS = 1

# Project structure
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "knowledge_base"