# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install CPU-only PyTorch FIRST — prevents pip from pulling 400MB+ of CUDA libs
# This alone saves ~300MB RAM at runtime (critical for Render free-tier 512MB limit)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml README.md ./
COPY app/ app/
RUN pip install --no-cache-dir .

# Pre-download the embedding model so startup is fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

# ── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

COPY app/ app/
COPY data/ data/
# Fail fast if indexes weren't built locally
RUN test -f data/url_allowlist.txt || (echo "ERROR: run 'python scripts/build_indexes.py' before docker build" && exit 1)
COPY README.md .

ENV PYTHONUNBUFFERED=1
# Disable HF model freshness checks at runtime to speed up cold start
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HUB_OFFLINE=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
