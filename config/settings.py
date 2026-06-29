import os
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=str(_ENV_PATH), override=True)
else:
    load_dotenv(override=True)


def get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(
                f"Missing required environment variable: {key}. "
                f"Set it in .env or export it."
        )
    return value


def get_optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# Required
GROQ_API_KEY = get_required("GROQ_API_KEY")

# Optional — SERP providers
SERPAPI_KEY = get_optional("SERPAPI_KEY", "")

# Optional — Google
PAGESPEED_API_KEY = get_optional("PAGESPEED_API_KEY", "")
CREDENTIALS_PATH = get_optional("CREDENTIALS_PATH", "credentials.json")
SHEET_NAME = get_optional("SHEET_NAME", "Keyword Tracker")
GSC_SITE_URL = get_optional("GSC_SITE_URL", "")
GA4_PROPERTY_ID = get_optional("GA4_PROPERTY_ID", "")

# Optional — SERP providers
SEARCHAPI_API_KEY = get_optional("SEARCHAPI_API_KEY", "")

# Optional — Apify (SERP enrichment, not rank fallback)
APIFY_API_KEY = get_optional("APIFY_API_KEY", "")

# Optional — Groq
GROQ_MODEL = get_optional("GROQ_MODEL", "llama-3.3-70b-versatile")

# Optional — OpenRouter (fallback when Groq fails)
OPENROUTER_API_KEY = get_optional("OPENROUTER_API_KEY", "")

# Optional — OpenPageRank (free domain authority metric)
OPENPAGERANK_API_KEY = get_optional("OPENPAGERANK_API_KEY", "")

# Upstash Redis (serverless, REST-based)
UPSTASH_REDIS_URL = get_optional("UPSTASH_REDIS_URL", "")
UPSTASH_REDIS_TOKEN = get_optional("UPSTASH_REDIS_TOKEN", "")

# Supabase Postgres (canonical DB)
SUPABASE_URL = get_optional("SUPABASE_URL", "")
SUPABASE_SSL_CERT = get_optional("SUPABASE_SSL_CERT", "")

# Security
API_AUTH_KEY = get_optional("API_AUTH_KEY", "")
CORS_ORIGINS = get_optional("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")

# Optional — Playwright proxy (socks5/http proxy for all browser sessions)
BROWSER_PROXY_URL = get_optional("BROWSER_PROXY_URL", "")

# Runtime — clamped between 1 and 9999
_MAX_KEYWORDS_RAW = int(get_optional("MAX_KEYWORDS", "999"))
MAX_KEYWORDS = max(1, min(_MAX_KEYWORDS_RAW, 9999))

# Tab names — DEPRECATED: use config.sheet_schema.TabName instead
TABS = {
    "keywords": "Keywords",
    "serp_snapshot": "SERP Snapshot",
    "ai_analysis": "AI Analysis",
    "website_insights": "Website Tracking & Insights",
}
