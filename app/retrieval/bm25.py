"""
BM25 retrieval — load pickled index and query.
Pure function, no LLM, no I/O after boot.
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

_bm25 = None
_catalog: list[dict] = []


def load_bm25(data_dir: Path, catalog: list[dict]) -> None:
    """Load the BM25 index from disk. Called once at startup."""
    global _bm25, _catalog
    _catalog = catalog
    bm25_path = data_dir / "bm25.pkl"
    with open(bm25_path, "rb") as f:
        _bm25 = pickle.load(f)
    logger.info("BM25 index loaded (%d docs)", len(_catalog))


def bm25_topk(query: str, k: int = 30) -> list[tuple[int, float]]:
    """
    Query BM25 and return top-k results as (catalog_id, score) pairs.
    """
    if _bm25 is None:
        logger.error("BM25 not loaded")
        return []
    tokens = query.lower().split()
    scores = _bm25.get_scores(tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [(idx, float(scores[idx])) for idx in top_indices if scores[idx] > 0]
