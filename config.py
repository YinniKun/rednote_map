"""
Configuration Manager for Xiaohongshu Discord Bot.
Loads environment variables and sets up project configuration defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if available
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application Configuration Settings."""

    # Discord Settings
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_GUILD_ID: Optional[int] = int(os.getenv("DISCORD_GUILD_ID")) if os.getenv("DISCORD_GUILD_ID") else None
    ALLOWED_CHANNEL_IDS: list[int] = [
        int(cid.strip()) for cid in os.getenv("ALLOWED_CHANNEL_IDS", "").split(",") if cid.strip()
    ]

    # LLM Settings (Supports OpenAI / Gemini / Anthropic / Custom OpenAI-compatible API)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()  # 'openai', 'gemini', 'anthropic', 'custom'
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    LLM_BASE_URL: Optional[str] = os.getenv("LLM_BASE_URL", None)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Google Maps API Settings
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # Google Sheets / My Maps Pinning Settings
    PINNER_STRATEGY: str = os.getenv("PINNER_STRATEGY", "sheets").lower()  # 'sheets', 'kml', 'playwright', 'none'
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    KML_OUTPUT_FILE: str = os.getenv("KML_OUTPUT_FILE", "saved_places.kml")

    # Scraper Settings
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    )

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration and return missing config warnings."""
        warnings = []
        if not cls.DISCORD_BOT_TOKEN:
            warnings.append("DISCORD_BOT_TOKEN is missing!")
        if not cls.LLM_API_KEY:
            warnings.append("LLM_API_KEY (or OPENAI_API_KEY) is missing!")
        if not cls.GOOGLE_MAPS_API_KEY:
            warnings.append("GOOGLE_MAPS_API_KEY is missing (falling back to mock geocoding if not set).")
        if cls.PINNER_STRATEGY == "sheets" and not cls.GOOGLE_SHEETS_ID:
            warnings.append("GOOGLE_SHEETS_ID is missing for 'sheets' pinner strategy.")
        return warnings


config = Config()
