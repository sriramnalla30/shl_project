"""
Application configuration — Pydantic Settings with env var wiring.
"""
from __future__ import annotations
from pydantic_settings import SettingsConfigDict
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    """All configuration from environment variables."""

    # LLM providers
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Observability
    langsmith_api_key: str = ""
    langchain_tracing_v2: str = "false"
    langchain_project: str = "shl-recommender"

    # Model configuration
    groq_model_main: str = "llama-3.3-70b-versatile"
    groq_model_cheap: str = "llama-3.1-8b-instant"
    gemini_model: str = "gemini-2.5-flash"

    # Timeouts (seconds)
    llm_timeout: float = 25.0
    per_call_timeout: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_url_allowlist() -> frozenset[str]:
    """Load the URL allowlist from data/url_allowlist.txt into a frozenset."""
    path = DATA_DIR / "url_allowlist.txt"
    if not path.exists():
        logger.warning("url_allowlist.txt not found at %s", path)
        return frozenset()
    urls = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            urls.add(line)
            # Also add trailing-slash and non-trailing-slash variants
            if line.endswith("/"):
                urls.add(line.rstrip("/"))
            else:
                urls.add(line + "/")
    return frozenset(urls)


def load_catalog() -> list[dict]:
    """Load the normalized catalog from data/catalog.json."""
    path = DATA_DIR / "catalog.json"
    if not path.exists():
        logger.warning("catalog.json not found at %s", path)
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.loads(f.read(), strict=False)
