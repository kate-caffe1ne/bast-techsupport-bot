from pathlib import Path

# API and Network Configuration
API_URL = "https://cnr.bast.ru/api/v2/catalog.json"
HEADERS = {"Accept": "application/json"}
REQUEST_TIMEOUT = 30.0

# Concurrency settings
# Reduced to 1. The bast.ru server aggressively blocks/drops connections 
# if we open multiple Playwright tabs simultaneously.
MAX_CONCURRENT_TASKS = 1

# Project structure
# Note: Since config is now one level deeper in src/bast_parser, we need to adjust BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "knowledge_base"