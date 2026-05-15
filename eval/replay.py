"""
Stateless replay harness — feeds conversation traces through /chat and
captures recommendations for metric computation.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0


async def replay_one(messages: list[dict], client: httpx.AsyncClient) -> dict:
    """Send a single chat request and return the response."""
    payload = {"messages": messages}
    r = await client.post(f"{BASE_URL}/chat", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


async def replay_trace(trace: list[dict], client: httpx.AsyncClient) -> list[dict]:
    """Replay a multi-turn trace, accumulating messages."""
    results = []
    accumulated: list[dict] = []
    for msg in trace:
        accumulated.append(msg)
        if msg["role"] == "user":
            resp = await replay_one(accumulated, client)
            results.append(resp)
            # Add assistant reply to accumulated for next turn
            accumulated.append({"role": "assistant", "content": resp["reply"]})
    return results


async def run_eval(traces_dir: Path) -> dict:
    """Run all traces and collect results."""
    traces = []
    for f in sorted(traces_dir.glob("*.json")):
        with open(f, "r", encoding="utf-8") as fp:
            traces.append((f.stem, json.load(fp)))

    logger.info("Loaded %d traces from %s", len(traces), traces_dir)

    results = {}
    async with httpx.AsyncClient() as client:
        for name, trace in traces:
            start = time.time()
            try:
                responses = await replay_trace(trace, client)
                elapsed = time.time() - start
                results[name] = {
                    "status": "ok",
                    "responses": responses,
                    "elapsed_s": elapsed,
                }
                logger.info("  %s: OK (%.1fs, %d responses)", name, elapsed, len(responses))
            except Exception as e:
                elapsed = time.time() - start
                results[name] = {"status": "error", "error": str(e), "elapsed_s": elapsed}
                logger.error("  %s: FAIL (%.1fs) — %s", name, elapsed, e)

    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    traces_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eval/traces")
    results = asyncio.run(run_eval(traces_dir))
    print(json.dumps(results, indent=2))
