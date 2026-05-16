"""
Stateless replay harness over the markdown sample conversations.
For each .md trace, extract the user turns via parse_md_traces, send them
sequentially through /chat (full history per call), and compute Recall@10
against the URLs the ideal agent committed to in the final shortlist turn.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

from eval.parse_md_traces import load_all_traces
from eval.recall import recall_at_k, mean_recall_at_k

load_dotenv()

from pathlib import Path
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "eval.log"

# Configure both file and console logging
_handler_file = logging.FileHandler(_LOG_FILE, mode="w", encoding="utf-8")  # fresh each run
_handler_file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s | %(message)s"))
_handler_console = logging.StreamHandler()
_handler_console.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler_file, _handler_console])

logger = logging.getLogger(__name__)
logger.info("Eval log file: %s", _LOG_FILE)

BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8000")
TIMEOUT = 60.0
MAX_TURNS = 8
INTER_TRACE_DELAY_S = float(os.getenv("INTER_TRACE_DELAY_S", "3"))


async def post_chat(messages: list[dict], client: httpx.AsyncClient) -> dict:
    r = await client.post(f"{BASE_URL}/chat", json={"messages": messages}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


async def replay_record(record: dict, client: httpx.AsyncClient) -> dict:
    history: list[dict] = []
    final_recs: list[str] = []
    latencies: list[float] = []
    turns_used = 0

    for user_msg in record["user_turns"][:MAX_TURNS]:
        history.append({"role": "user", "content": user_msg})
        turns_used += 1
        t0 = time.time()
        try:
            resp = await post_chat(history, client)
        except Exception as e:
            logger.error("%s: /chat failed on turn %d — %s", record["id"], turns_used, e)
            break
        latencies.append(time.time() - t0)
        history.append({"role": "assistant", "content": resp.get("reply", "")})
        recs = resp.get("recommendations") or []
        if recs:
            final_recs = [r["url"] for r in recs]
        if turns_used >= MAX_TURNS:
            break

    expected = record["expected_urls"]
    recall = recall_at_k(final_recs, expected, k=10) if expected else None
    return {
        "id": record["id"],
        "turns_used": turns_used,
        "final_recs": final_recs,
        "n_expected": len(expected),
        "recall_at_10": recall,
        "latency_median_s": sorted(latencies)[len(latencies)//2] if latencies else None,
        "latency_max_s": max(latencies) if latencies else None,
    }


async def main() -> None:
    import sys
    traces_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sample_conversations/GenAI_SampleConversations")
    out_path = Path("eval_report.md")

    records = load_all_traces(traces_dir)
    logger.info("Loaded %d traces from %s", len(records), traces_dir)

    async with httpx.AsyncClient() as client:
        try:
            h = await client.get(f"{BASE_URL}/health", timeout=120)
            h.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Server not reachable at {BASE_URL}: {e}")

        results = []
        for i, rec in enumerate(records):
            if i > 0 and INTER_TRACE_DELAY_S > 0:
                logger.info("Sleeping %.1fs between traces (rate-limit pacing)", INTER_TRACE_DELAY_S)
                await asyncio.sleep(INTER_TRACE_DELAY_S)
            logger.info("Replaying %s (%d user turns expected)", rec["id"], rec["n_turns"])
            res = await replay_record(rec, client)
            results.append(res)
            r10 = f"{res['recall_at_10']:.2f}" if res["recall_at_10"] is not None else "n/a"
            logger.info("  -> turns=%d, recall@10=%s, recs=%d, expected=%d",
                        res["turns_used"], r10, len(res["final_recs"]), res["n_expected"])

    expected_lookup = {r["id"]: r["expected_urls"] for r in records}
    scored = [(r["final_recs"], expected_lookup[r["id"]])
              for r in results if r["recall_at_10"] is not None]
    mean_recall = mean_recall_at_k(scored, k=10) if scored else None

    lines = ["# Eval Report -- Markdown Trace Replay\n"]
    lines.append(f"- Server: `{BASE_URL}`")
    lines.append(f"- Traces evaluated: **{len(results)}**")
    if mean_recall is not None:
        lines.append(f"- **Mean Recall@10: {mean_recall:.3f}**")
    median_lats = [r["latency_median_s"] for r in results if r["latency_median_s"]]
    if median_lats:
        lines.append(f"- Median per-turn latency: {sum(median_lats)/len(median_lats):.2f}s")
        lines.append(f"- Worst per-turn latency: {max((r['latency_max_s'] or 0) for r in results):.2f}s")
    lines.append("\n## Per-trace\n")
    lines.append("| trace | turns | recall@10 | recs | n_expected | median_lat |")
    lines.append("|-------|-------|-----------|------|------------|------------|")
    for r in results:
        rec = f"{r['recall_at_10']:.2f}" if r["recall_at_10"] is not None else "n/a"
        lat = f"{r['latency_median_s']:.1f}s" if r["latency_median_s"] else "n/a"
        lines.append(f"| {r['id']} | {r['turns_used']} | {rec} | {len(r['final_recs'])} | {r['n_expected']} | {lat} |")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written to %s", out_path)
    if mean_recall is not None:
        print(f"\nMean Recall@10: {mean_recall:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
