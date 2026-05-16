"""
Stateless replay harness with LLM-driven simulated user.
Mimics the official evaluator's behavior: full conversation history per call,
simulated user reacts to the agent's actual replies based on the persona facts.
Also computes Recall@10 and writes a markdown report.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from groq import AsyncGroq

from eval.recall import recall_at_k, mean_recall_at_k

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("AGENT_BASE_URL", "http://localhost:8000")
TIMEOUT = 60.0
MAX_TURNS = 8
SIM_USER_MODEL = "llama-3.1-8b-instant"

SIM_USER_SYSTEM = """You are simulating a hiring manager talking to an SHL assessment recommender.

You ONLY know these facts about the role you're hiring for:
{facts}

Rules of behavior:
- Answer the agent's questions truthfully from the facts above.
- If asked about something not in your facts, reply: "I don't have a strong preference."
- Never volunteer information that wasn't asked for, except on your very first turn.
- On your FIRST turn, state the role you're hiring for in one short sentence (use only your facts).
- Keep replies short (1-2 sentences). Do not write in JSON.
- End the conversation by replying "thanks" once the agent has given you a list of recommendations.
"""


async def post_chat(messages: list[dict], client: httpx.AsyncClient) -> dict:
    """Send a stateless /chat request."""
    r = await client.post(f"{BASE_URL}/chat", json={"messages": messages}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


async def simulated_user_reply(
    facts: dict,
    history: list[dict],
    llm: AsyncGroq,
    first_turn: bool = False,
) -> str:
    """Get next user message from the simulated user LLM."""
    system = SIM_USER_SYSTEM.format(facts=json.dumps(facts, indent=2))
    msgs = [{"role": "system", "content": system}]
    # Translate the agent-side history into the sim user's perspective:
    # the sim user is the "user" role in the agent transcript, so from its POV
    # the agent's replies are what it should respond to.
    for m in history:
        if m["role"] == "assistant":
            msgs.append({"role": "user", "content": m["content"]})
        else:
            msgs.append({"role": "assistant", "content": m["content"]})
    if first_turn:
        msgs.append({"role": "user", "content": "Begin by stating the role you are hiring for."})
    r = await llm.chat.completions.create(
        model=SIM_USER_MODEL,
        messages=msgs,
        max_tokens=120,
        temperature=0.3,
    )
    return (r.choices[0].message.content or "").strip()


async def replay_trace_simulated(
    trace: dict,
    http_client: httpx.AsyncClient,
    llm: AsyncGroq,
) -> dict:
    """Run one full simulated conversation against /chat. Returns metrics."""
    facts = trace.get("facts") or trace.get("persona", {})
    expected = trace.get("expected_shortlist", []) or trace.get("relevant_urls", [])

    history: list[dict] = []
    first = await simulated_user_reply(facts, [], llm, first_turn=True)
    history.append({"role": "user", "content": first})

    final_recs: list[str] = []
    turns_used = 0
    latencies: list[float] = []

    for _ in range(MAX_TURNS):
        turns_used += 1
        t0 = time.time()
        try:
            resp = await post_chat(history, http_client)
        except Exception as e:
            logger.error("Trace %s: /chat failed on turn %d — %s", trace.get("id", "?"), turns_used, e)
            break
        latencies.append(time.time() - t0)
        history.append({"role": "assistant", "content": resp["reply"]})
        if resp.get("recommendations"):
            final_recs = [r["url"] for r in resp["recommendations"]]
            break
        if resp.get("end_of_conversation"):
            break
        try:
            next_msg = await simulated_user_reply(facts, history, llm)
        except Exception as e:
            logger.error("Sim user failed: %s", e)
            break
        if next_msg.lower().strip().startswith("thanks"):
            break
        history.append({"role": "user", "content": next_msg})

    recall = recall_at_k(final_recs, expected, k=10) if expected else None
    return {
        "id": trace.get("id", "unknown"),
        "turns": turns_used,
        "final_recs": final_recs,
        "expected": expected,
        "recall_at_10": recall,
        "latency_median_s": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "latency_p95_s": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else None,
        "transcript": history,
    }


def load_traces(traces_dir: Path) -> list[dict]:
    traces = []
    for f in sorted(traces_dir.glob("*.json")):
        with open(f, encoding="utf-8") as fp:
            trace = json.load(fp)
        if "id" not in trace:
            trace["id"] = f.stem
        traces.append(trace)
    return traces


async def main() -> None:
    import sys
    traces_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eval/traces")
    out_path = Path("eval_report.md")

    traces = load_traces(traces_dir)
    logger.info("Loaded %d traces from %s", len(traces), traces_dir)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY must be set for the simulated user.")
    llm = AsyncGroq(api_key=api_key)

    async with httpx.AsyncClient() as http:
        # Probe /health first
        try:
            h = await http.get(f"{BASE_URL}/health", timeout=120)
            h.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"Server not reachable at {BASE_URL}: {e}")

        results = []
        for t in traces:
            logger.info("Replaying trace: %s", t["id"])
            res = await replay_trace_simulated(t, http, llm)
            results.append(res)
            logger.info(
                "  → turns=%d, recall@10=%s, recs=%d",
                res["turns"],
                f"{res['recall_at_10']:.2f}" if res["recall_at_10"] is not None else "n/a",
                len(res["final_recs"]),
            )

    scored = [(r["final_recs"], r["expected"]) for r in results if r["expected"]]
    mean_recall = mean_recall_at_k(scored, k=10) if scored else None

    # Write markdown report
    lines = ["# Eval Report — Replay Harness\n"]
    lines.append(f"- Traces evaluated: **{len(results)}**")
    lines.append(f"- Mean Recall@10: **{mean_recall:.3f}**" if mean_recall is not None else "- Mean Recall@10: n/a")
    median_lats = [r["latency_median_s"] for r in results if r["latency_median_s"]]
    if median_lats:
        lines.append(f"- Median per-turn latency: **{sum(median_lats)/len(median_lats):.2f}s**")
    lines.append("\n## Per-trace\n")
    lines.append("| trace | turns | recall@10 | recs | median_lat |")
    lines.append("|-------|-------|-----------|------|------------|")
    for r in results:
        rec = f"{r['recall_at_10']:.2f}" if r["recall_at_10"] is not None else "n/a"
        lat = f"{r['latency_median_s']:.1f}s" if r["latency_median_s"] else "n/a"
        lines.append(f"| {r['id']} | {r['turns']} | {rec} | {len(r['final_recs'])} | {lat} |")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written to %s", out_path)
    print(f"\nMean Recall@10: {mean_recall:.3f}" if mean_recall is not None else "\nMean Recall@10: n/a")


if __name__ == "__main__":
    asyncio.run(main())
