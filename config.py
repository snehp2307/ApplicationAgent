"""
============================================
BULK AI JOB OUTREACH BOT - Configuration
============================================
Loads all settings from .env file and provides
centralized configuration for the entire system.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================
# REQUIRED CREDENTIALS
# ============================================

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
RESUME_PATH = os.getenv("RESUME_PATH", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


# ============================================
# BATCH CONFIGURATION
# ============================================

# How many companies to process per batch
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))

# Delay between individual emails (seconds) - randomized in this range
MIN_DELAY_BETWEEN_EMAILS = int(os.getenv("MIN_DELAY_BETWEEN_EMAILS", "30"))
MAX_DELAY_BETWEEN_EMAILS = int(os.getenv("MAX_DELAY_BETWEEN_EMAILS", "120"))

# Delay between batches (minutes)
BATCH_DELAY_MINUTES = int(os.getenv("BATCH_DELAY_MINUTES", "10"))

# Target number of companies to find
TARGET_COMPANY_COUNT = int(os.getenv("TARGET_COMPANY_COUNT", "150"))

# Maximum retries for failed email sends
MAX_RETRIES = 3

# Gmail daily send limit (standard Gmail = 500/day)
GMAIL_DAILY_LIMIT = 500


# ============================================
# MISTRAL AI SETTINGS
# ============================================

MISTRAL_MODEL = "mistral-large-latest"
MISTRAL_TEMPERATURE = 0.7
MISTRAL_MAX_TOKENS = 1024


# ============================================
# OUTPUT FILES
# ============================================

OUTPUT_DIR = "output"
SENT_LOG_FILE = os.path.join(OUTPUT_DIR, "sent_log.csv")
FAILED_LOG_FILE = os.path.join(OUTPUT_DIR, "failed_log.csv")
COMPANIES_FILE = os.path.join(OUTPUT_DIR, "companies_found.csv")
FULL_LOG_FILE = os.path.join(OUTPUT_DIR, "activity_log.txt")


# ============================================
# SEARCH SETTINGS
# ============================================

# Number of search queries to run per batch
SEARCHES_PER_BATCH = 10

# LinkedIn-ONLY search settings (NO other sources allowed)
JOB_SOURCE = "LINKEDIN_ONLY"
LINKEDIN_RESULTS_PER_QUERY = int(os.getenv("LINKEDIN_RESULTS_PER_QUERY", "20"))
LINKEDIN_MIN_MATCH_SCORE = int(os.getenv("LINKEDIN_MIN_MATCH_SCORE", "20"))

# Common email patterns to try for companies
EMAIL_PATTERNS = [
    "careers@{domain}",
    "hr@{domain}",
    "jobs@{domain}",
    "recruiting@{domain}",
    "talent@{domain}",
    "hiring@{domain}",
    "recruitment@{domain}",
    "apply@{domain}",
    "resume@{domain}",
    "people@{domain}",
    "info@{domain}",
]


# ============================================
# VALIDATION
# ============================================

def validate_config():
    """Validate that all required settings are configured."""
    errors = []

    if not MISTRAL_API_KEY or MISTRAL_API_KEY == "your_mistral_api_key_here":
        errors.append("MISTRAL_API_KEY is not set in .env file")

    if not GMAIL_EMAIL or GMAIL_EMAIL == "your.email@gmail.com":
        errors.append("GMAIL_EMAIL is not set in .env file")

    if not GMAIL_APP_PASSWORD or GMAIL_APP_PASSWORD == "your_16_char_app_password":
        errors.append("GMAIL_APP_PASSWORD is not set in .env file")

    if not RESUME_PATH or RESUME_PATH == "C:/Users/YourName/Documents/resume.pdf":
        errors.append("RESUME_PATH is not set in .env file")

    if not TAVILY_API_KEY or TAVILY_API_KEY == "your_tavily_api_key_here":
        errors.append("TAVILY_API_KEY is not set in .env file")

    if RESUME_PATH and RESUME_PATH != "C:/Users/YourName/Documents/resume.pdf":
        if not os.path.exists(RESUME_PATH):
            errors.append(f"Resume file not found at: {RESUME_PATH}")

    if errors:
        print("\n❌ CONFIGURATION ERRORS:")
        print("=" * 50)
        for err in errors:
            print(f"  ⚠  {err}")
        print("=" * 50)
        print("\n📝 Fix these in your .env file (copy from .env.example)")
        print("   Then run again: python main.py\n")
        sys.exit(1)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("✅ Configuration validated successfully!")
    return True
