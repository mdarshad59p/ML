"""
Central config loader. Reads everything from environment variables
(loaded from .env locally via python-dotenv, or set directly in
Render's dashboard when deployed).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = _get_admin_ids()
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

# Optional third-party API keys — features degrade gracefully if empty
REMOVEBG_API_KEY = os.getenv("REMOVEBG_API_KEY", "")
AUDD_API_KEY = os.getenv("AUDD_API_KEY", "")
TINYURL_API_KEY = os.getenv("TINYURL_API_KEY", "")
SCREENSHOT_API_KEY = os.getenv("SCREENSHOT_API_KEY", "")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
TENOR_API_KEY = os.getenv("TENOR_API_KEY", "")

# Economy defaults
DAILY_COIN_REWARD = 20
REFERRAL_COIN_REWARD = 15
DEFAULT_LANGUAGE = "en"

SUPPORTED_LANGUAGES = {
    "bn": "বাংলা",
    "en": "English",
    "hi": "हिन्दी",
    "ur": "اردو",
    "ar": "العربية",
    "es": "Español",
    "id": "Bahasa Indonesia",
    "ru": "Русский",
    "zh": "中文",
    "fr": "Français",
}

DB_PATH = os.getenv("DB_PATH", "maya_bot.db")

if not BOT_TOKEN:
    print("⚠️  WARNING: BOT_TOKEN is not set. The bot will not be able to start.")
