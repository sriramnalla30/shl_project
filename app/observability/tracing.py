"""
LangSmith tracing setup — one function, no-op if env var not set.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def init_tracing() -> None:
    """Initialize LangSmith tracing if API key is available."""
    api_key = os.getenv("LANGSMITH_API_KEY", "")
    if api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "shl-recommender")
        logger.info("LangSmith tracing enabled (project=%s)", os.environ["LANGCHAIN_PROJECT"])
    else:
        logger.info("LangSmith tracing disabled (no API key)")
