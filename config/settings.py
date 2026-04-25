"""
Centralized application settings and constants.
All model configuration, API parameters, and application defaults live here.
"""

from pathlib import Path

# ============================================================
# Project Paths
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
APPLICATIONS_DIR = DATA_DIR / "applications"
CACHE_DIR = DATA_DIR / "cache"
APPLICATIONS_LOG = DATA_DIR / "applications_log.json"
USER_PROFILE_PATH = CONFIG_DIR / "user_profile.json"
API_LOG_PATH = DATA_DIR / "api_calls.log"

# ============================================================
# NVIDIA NIM API Configuration
# ============================================================
NVIDIA_MODEL = "nvidia/nemotron-3-super-120b-a12b"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# ============================================================
# Temperature & Token Settings
# ============================================================
EXTRACTION_TEMPERATURE = 0.1
GENERATION_TEMPERATURE = 0.7
SYNTHESIS_TEMPERATURE = 0.4

MAX_TOKENS_EXTRACTION = 2048
MAX_TOKENS_GENERATION = 4096
MAX_TOKENS_SYNTHESIS = 2048

# ============================================================
# Scraping Configuration
# ============================================================
SCRAPE_DELAY_SECONDS = 1.5
SCRAPE_TIMEOUT_SECONDS = 30
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ============================================================
# Cache Configuration
# ============================================================
RESEARCH_CACHE_TTL = 86400  # 24 hours in seconds
PAGE_CACHE_TTL = 86400      # 24 hours
API_CACHE_TTL = 3600        # 1 hour for API responses

# ============================================================
# Retry Configuration
# ============================================================
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # Base seconds for exponential backoff

# ============================================================
# Cover Letter Defaults
# ============================================================
MIN_LETTER_WORDS = 200
MAX_LETTER_WORDS = 400
TARGET_LETTER_WORDS = 300

# ============================================================
# Display
# ============================================================
SEPARATOR = "─" * 50
HEADER_WIDTH = 50

# ============================================================
# Company Research Page Paths
# ============================================================
COMPANY_PAGE_PATHS = [
    "/about",
    "/about-us",
    "/careers",
    "/blog",
]

# Maximum characters to keep from scraped pages (saves tokens)
MAX_PAGE_CONTENT_LENGTH = 2000
