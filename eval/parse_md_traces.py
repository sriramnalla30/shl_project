"""
Parse SHL sample conversation markdown files into a structured format
that the replay harness can consume.

Each .md file looks like:
    ## Conversation
    ### Turn 1
    **User**
    > <user message, possibly multi-line with > prefix>
    **Agent**
    <agent reply text>
    | # | Name | ... | URL |  (optional table of recommendations)
    | 1 | OPQ32r | ... | <https://www.shl.com/...> |
    _`end_of_conversation`: **true|false**_
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

USER_BLOCK = re.compile(r"\*\*User\*\*\s*(.*?)(?=\*\*Agent\*\*|$)", re.S)
AGENT_BLOCK = re.compile(r"\*\*Agent\*\*\s*(.*?)(?=### Turn|\Z)", re.S)
TURN_HEADING = re.compile(r"###\s*Turn\s*(\d+)", re.I)
EOC_RE = re.compile(r"`end_of_conversation`:\s*\*\*(true|false)\*\*", re.I)
URL_RE = re.compile(r"https?://www\.shl\.com/[^\s)>\]\"|]+")
QUOTE_LINE = re.compile(r"^>\s?", re.M)


def _clean_user_text(block: str) -> str:
    """Strip leading > markers from blockquote-formatted user messages."""
    text = QUOTE_LINE.sub("", block.strip())
    return text.strip()


def parse_conversation(md_text: str) -> list[dict]:
    """Return a list of turns. Each turn has user, agent_reply, agent_urls, end_of_conversation."""
    # Split by turn headings
    parts = TURN_HEADING.split(md_text)
    # parts looks like: [preamble, "1", body1, "2", body2, ...]
    turns = []
    for i in range(1, len(parts), 2):
        turn_no = int(parts[i])
        body = parts[i + 1] if i + 1 < len(parts) else ""

        u_match = USER_BLOCK.search(body)
        a_match = AGENT_BLOCK.search(body)
        if not u_match:
            continue
        user_text = _clean_user_text(u_match.group(1))
        agent_text = a_match.group(1).strip() if a_match else ""

        urls = []
        seen = set()
        for u in URL_RE.findall(agent_text):
            u_norm = u.rstrip(">").rstrip("/").rstrip(",")
            if u_norm not in seen:
                seen.add(u_norm)
                urls.append(u_norm)

        eoc_match = EOC_RE.search(agent_text)
        eoc = eoc_match.group(1).lower() == "true" if eoc_match else False

        turns.append({
            "turn": turn_no,
            "user": user_text,
            "agent_reply": agent_text,
            "agent_urls": urls,
            "end_of_conversation": eoc,
        })
    return turns


def trace_to_eval_record(file_path: Path) -> dict:
    """Convert a markdown conversation into an eval record:
       - id (filename stem)
       - user_turns: ordered list of user messages
       - expected_urls: URLs from the FINAL turn that has end_of_conversation=true,
                        falling back to the last turn's URLs.
    """
    text = file_path.read_text(encoding="utf-8")
    turns = parse_conversation(text)
    user_turns = [t["user"] for t in turns]

    expected = []
    for t in reversed(turns):
        if t["end_of_conversation"] and t["agent_urls"]:
            expected = t["agent_urls"]
            break
    if not expected:
        for t in reversed(turns):
            if t["agent_urls"]:
                expected = t["agent_urls"]
                break

    return {
        "id": file_path.stem,
        "user_turns": user_turns,
        "expected_urls": expected,
        "n_turns": len(user_turns),
    }


def load_all_traces(traces_dir: Path) -> list[dict]:
    return [trace_to_eval_record(f) for f in sorted(traces_dir.glob("*.md"))]


if __name__ == "__main__":
    import json
    import sys
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "sample_conversations/GenAI_SampleConversations")
    records = load_all_traces(d)
    for r in records:
        print(f"{r['id']}: {r['n_turns']} user turns, {len(r['expected_urls'])} expected URLs")
    print(json.dumps(records[0], indent=2))
