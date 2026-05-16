"""
LLM wrapper — Multi-key Groq + Multi-key Gemini with rotating failover.

Pulls all GROQ_API_KEY_* and GEMINI_API_KEY_* env vars. On rate-limit or
timeout, automatically rotates to the next available key. Falls back from
Groq pool → Gemini pool only after all Groq keys are exhausted.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from groq import AsyncGroq, APIStatusError, RateLimitError

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Gemini SDK (optional) ────────────────────────────────────────────────────
try:
    from google import genai
    _gemini_available = True
except ImportError:
    _gemini_available = False

# ── Multi-key pools ──────────────────────────────────────────────────────────
def _collect_keys(prefix: str) -> list[str]:
    """Collect all environment variables matching PREFIX_1, PREFIX_2, etc.
    Falls back to PREFIX (no number) if numbered keys aren't set."""
    keys = []
    for i in range(1, 20):  # support up to 20 keys
        v = os.getenv(f"{prefix}_{i}")
        if v:
            keys.append(v)
    if not keys:
        v = os.getenv(prefix)
        if v:
            keys.append(v)
    return keys

_GROQ_KEYS: list[str] = _collect_keys("GROQ_API_KEY")
_GEMINI_KEYS: list[str] = _collect_keys("GEMINI_API_KEY")
_groq_clients: list[AsyncGroq] = [AsyncGroq(api_key=k) for k in _GROQ_KEYS]
_gemini_clients: list[Any] = []
if _gemini_available:
    _gemini_clients = [genai.Client(api_key=k) for k in _GEMINI_KEYS]

# Rotation pointers (so we don't always start with key 1)
_groq_cursor = 0
_gemini_cursor = 0

logger.info("LLM pool initialized: %d Groq keys, %d Gemini keys",
            len(_groq_clients), len(_gemini_clients))

# ── Skill / prompt loading (unchanged) ───────────────────────────────────────
_skill_text: str = ""

def load_skill_text() -> str:
    global _skill_text
    if not _skill_text:
        from pathlib import Path
        skill_path = Path(__file__).parent / "prompts" / "_shared" / "SKILL.md"
        if skill_path.exists():
            _skill_text = skill_path.read_text(encoding="utf-8")
        else:
            logger.warning("SKILL.md not found at %s", skill_path)
            _skill_text = ""
    return _skill_text

def load_prompt(name: str) -> str:
    from pathlib import Path
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    text = prompt_path.read_text(encoding="utf-8")
    if "<<SKILL>>" in text:
        skill = load_skill_text().replace("{", "{{").replace("}", "}}")
        text = text.replace("<<SKILL>>", skill)
    return text

def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        # Strip code block markers
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse JSON from LLM response: %s", text[:200])
        return None

def extract_json_from_text(text: str) -> Any:
    return _extract_json(text)

# ── Multi-key Gemini call with rotation ──────────────────────────────────────
async def _gemini_call_with_rotation(
    prompt: str, system: str, max_tokens: int, temperature: float, timeout: float
) -> str:
    global _gemini_cursor
    if not _gemini_clients:
        raise RuntimeError("No Gemini keys available")

    settings = get_settings()
    model_name = getattr(settings, "gemini_model", "gemini-2.0-flash")
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    last_error: Exception | None = None

    for attempt in range(len(_gemini_clients)):
        idx = (_gemini_cursor + attempt) % len(_gemini_clients)
        client = _gemini_clients[idx]
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents=full_prompt,
                    config={
                        "max_output_tokens": max_tokens,
                        "temperature": temperature,
                    },
                ),
                timeout=timeout,
            )
            # On success, advance cursor to the NEXT key for the next call
            _gemini_cursor = (idx + 1) % len(_gemini_clients)
            return resp.text or ""
        except Exception as e:
            logger.warning("Gemini key #%d failed: %s", idx + 1, str(e)[:120])
            last_error = e
            continue

    raise last_error or RuntimeError("All Gemini keys exhausted")

# ── Multi-key Groq call with rotation + Gemini failover ──────────────────────
async def _groq_call(
    prompt: str,
    model: str | None = None,
    system: str = "",
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.1,
    timeout: float = 15.0,
) -> str:
    global _groq_cursor

    if not _groq_clients:
        # No Groq keys at all — try Gemini directly
        if _gemini_clients:
            logger.warning("No Groq keys, routing to Gemini pool")
            return await _gemini_call_with_rotation(prompt, system, max_tokens, temperature, timeout)
        raise RuntimeError("No LLM keys configured (Groq or Gemini)")

    settings = get_settings()
    primary_model = model or settings.groq_model_main
    cheap_model = settings.groq_model_cheap
    last_rate_limit_error: Exception | None = None

    # Try each Groq key with the primary model
    for attempt in range(len(_groq_clients)):
        idx = (_groq_cursor + attempt) % len(_groq_clients)
        client = _groq_clients[idx]
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": primary_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(**kwargs),
                timeout=timeout,
            )
            _groq_cursor = (idx + 1) % len(_groq_clients)
            return resp.choices[0].message.content or ""
        except (RateLimitError, APIStatusError) as e:
            logger.warning("Groq key #%d (%s) rate-limited: %s",
                           idx + 1, primary_model, str(e)[:120])
            last_rate_limit_error = e
            continue
        except asyncio.TimeoutError:
            logger.warning("Groq key #%d (%s) timed out", idx + 1, primary_model)
            continue

    # All Groq primary-model keys exhausted. Try the cheap model on each key.
    if primary_model != cheap_model:
        for attempt in range(len(_groq_clients)):
            idx = (_groq_cursor + attempt) % len(_groq_clients)
            client = _groq_clients[idx]
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            kwargs = {
                "model": cheap_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            try:
                resp = await asyncio.wait_for(
                    client.chat.completions.create(**kwargs),
                    timeout=timeout,
                )
                _groq_cursor = (idx + 1) % len(_groq_clients)
                logger.info("Recovered via Groq key #%d cheap model", idx + 1)
                return resp.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Groq key #%d (cheap model) failed: %s",
                               idx + 1, str(e)[:120])
                continue

    # All Groq keys/models exhausted → Gemini pool
    if _gemini_clients:
        logger.warning("All Groq keys exhausted, falling back to Gemini pool")
        return await _gemini_call_with_rotation(prompt, system, max_tokens, temperature, timeout)

    raise last_rate_limit_error or RuntimeError("All LLM keys exhausted")

async def call_main(prompt: str, system: str = "", json_mode: bool = False,
                    max_tokens: int = 1024, temperature: float = 0.1) -> str:
    settings = get_settings()
    return await _groq_call(
        prompt, model=settings.groq_model_main,
        system=system, json_mode=json_mode,
        max_tokens=max_tokens, temperature=temperature,
        timeout=settings.per_call_timeout,
    )

async def call_cheap(prompt: str, system: str = "", json_mode: bool = False,
                     max_tokens: int = 256, temperature: float = 0.0) -> str:
    settings = get_settings()
    return await _groq_call(
        prompt, model=settings.groq_model_cheap,
        system=system, json_mode=json_mode,
        max_tokens=max_tokens, temperature=temperature,
        timeout=settings.per_call_timeout,
    )

async def call_json(prompt: str, system: str = "",
                    model: str | None = None, max_tokens: int = 1024) -> Any:
    raw = await _groq_call(
        prompt, model=model, system=system,
        json_mode=True, max_tokens=max_tokens,
        timeout=get_settings().per_call_timeout,
    )
    result = _extract_json(raw)
    if result is None:
        logger.error("JSON parse failed, raw: %s", raw[:300])
        return {}
    return result