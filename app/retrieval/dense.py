"""
Dense retrieval — load FAISS index and query with bge-small-en-v1.5.
Pure function, no LLM, no I/O after boot.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_index = None
_ids: np.ndarray | None = None
_model = None


def load_dense(data_dir: Path) -> None:
    """Load FAISS index and embedding model. Called once at startup."""
    global _index, _ids, _model

    import faiss
    from sentence_transformers import SentenceTransformer

    index_path = data_dir / "faiss.index"
    ids_path = data_dir / "ids.npy"

    _index = faiss.read_index(str(index_path))
    _ids = np.load(str(ids_path))
    logger.info("FAISS index loaded (%d vectors)", _index.ntotal)

    _model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    logger.info("Embedding model loaded")


def dense_topk(query: str, k: int = 30) -> list[tuple[int, float]]:
    """
    Embed query and return top-k results as (catalog_id, score) pairs.
    """
    if _index is None or _model is None:
        logger.error("Dense retrieval not loaded")
        return []

    embedding = _model.encode([query], normalize_embeddings=True)
    embedding = np.array(embedding, dtype=np.float32)
    scores, indices = _index.search(embedding, k)

    results = []
    for i in range(len(indices[0])):
        idx = int(indices[0][i])
        score = float(scores[0][i])
        if idx >= 0 and idx < len(_ids):
            results.append((int(_ids[idx]), score))
    return results
