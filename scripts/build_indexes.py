"""
build_indexes.py — Offline script that reads the raw SHL product catalog,
normalizes field names to match the design docs, and produces:
  data/catalog.json   — normalized catalog
  data/bm25.pkl       — pickled BM25Okapi index
  data/faiss.index    — FAISS IndexFlatIP (384-dim)
  data/ids.npy        — row-id ↔ catalog index alignment
  data/url_allowlist.txt — one URL per line
"""
from __future__ import annotations

import json
import logging
import pickle
import re
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
RAW_CATALOG = PROJECT_DIR.parent / "shl_product_catalog.json"  # workspace root
DATA_DIR = PROJECT_DIR / "data"

# ── Key-category → letter-code mapping ────────────────────────────────────
KEY_TO_CODE: dict[str, str] = {
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Assessment Exercises": "E",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Simulations": "S",
}


def parse_duration(raw: str) -> int | None:
    """Extract integer minutes from strings like '30 minutes', '7 minutes', ''."""
    if not raw:
        return None
    m = re.search(r"(\d+)", raw)
    return int(m.group(1)) if m else None


def normalize_catalog(raw_records: list[dict]) -> list[dict]:
    """Transform raw scraped records into the normalized schema."""
    normalized = []
    for idx, r in enumerate(raw_records):
        # Map keys (full category names) → letter codes
        keys_raw = r.get("keys", [])
        letter_codes = sorted(set(
            KEY_TO_CODE.get(k, "")
            for k in keys_raw
        ) - {""})
        test_type_str = " ".join(letter_codes) if letter_codes else ""

        normalized.append({
            "id": idx,
            "entity_id": r.get("entity_id", ""),
            "name": r.get("name", ""),
            "url": r.get("link", ""),
            "test_type": test_type_str,
            "test_type_codes": letter_codes,
            "description": r.get("description", ""),
            "duration_minutes": parse_duration(r.get("duration", "")),
            "duration_raw": r.get("duration", ""),
            "job_levels": r.get("job_levels", []),
            "remote_supported": r.get("remote", "no").lower() == "yes",
            "adaptive": r.get("adaptive", "no").lower() == "yes",
            "languages": r.get("languages", []),
            "keys_raw": keys_raw,
        })
    return normalized


def build_bm25(catalog: list[dict], out_path: Path) -> None:
    """Tokenize name + description, build BM25 index, pickle it."""
    from rank_bm25 import BM25Okapi

    corpus = []
    for rec in catalog:
        text = f"{rec['name']} {rec['description']}"
        tokens = text.lower().split()
        corpus.append(tokens)

    bm25 = BM25Okapi(corpus)
    with open(out_path, "wb") as f:
        pickle.dump(bm25, f)
    logger.info("BM25 index saved → %s (%d docs)", out_path, len(corpus))


def build_faiss(catalog: list[dict], index_path: Path, ids_path: Path) -> None:
    """Embed name + description with bge-small-en-v1.5, build FAISS index."""
    import faiss
    from sentence_transformers import SentenceTransformer

    logger.info("Loading BAAI/bge-small-en-v1.5 …")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    texts = [f"{rec['name']} {rec['description']}" for rec in catalog]
    logger.info("Embedding %d texts …", len(texts))
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(index_path))
    ids = np.arange(len(catalog), dtype=np.int64)
    np.save(str(ids_path), ids)
    logger.info("FAISS index saved → %s (%d vectors, dim=%d)", index_path, len(catalog), dim)
    logger.info("IDs saved → %s", ids_path)


def build_url_allowlist(catalog: list[dict], out_path: Path) -> None:
    """Write one URL per line."""
    urls = []
    for rec in catalog:
        url = rec.get("url", "").strip()
        if url:
            urls.append(url)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(urls) + "\n")
    logger.info("URL allowlist saved → %s (%d URLs)", out_path, len(urls))


def main() -> None:
    # ── Load raw catalog ─────────────────────────────────────────────────
    if not RAW_CATALOG.exists():
        logger.error("Raw catalog not found at %s", RAW_CATALOG)
        sys.exit(1)

    with open(RAW_CATALOG, "r", encoding="utf-8") as f:
        raw = json.loads(f.read(), strict=False)
    logger.info("Loaded %d raw records from %s", len(raw), RAW_CATALOG)

    # ── Normalize ────────────────────────────────────────────────────────
    catalog = normalize_catalog(raw)
    logger.info("Normalized %d records", len(catalog))

    # ── Write outputs ────────────────────────────────────────────────────
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    catalog_path = DATA_DIR / "catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    logger.info("Normalized catalog saved → %s", catalog_path)

    build_bm25(catalog, DATA_DIR / "bm25.pkl")
    build_faiss(catalog, DATA_DIR / "faiss.index", DATA_DIR / "ids.npy")
    build_url_allowlist(catalog, DATA_DIR / "url_allowlist.txt")

    logger.info("✅ All indexes built successfully.")


if __name__ == "__main__":
    main()
