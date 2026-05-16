"""
LLM wrapper — Groq primary (70B for heavy, 8B for cheap) with Gemini fallback.

Every call is wrapped in asyncio.wait_for with a per-call budget.
Structured output via JSON mode where supported.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from groq import AsyncGroq, APIStatusError, RateLimitError

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Gemini SDK (optional fallback) ───────────────────────────────────────────
try:
    from google import genai
    _gemini_available = True
except ImportError:
    _gemini_available = False

# ── Globals (initialized lazily) ─────────────────────────────────────────────
_groq_client: AsyncGroq | None = None
_gemini_client: Any = None
_skill_text: str = ""


def _get_groq() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        settings = get_settings()
        _groq_client = AsyncGroq(api_key=settings.groq_api_key)
    return _groq_client


def _get_gemini_client():
    """Get or create a Gemini client."""
    global _gemini_client
    if _gemini_client is None and _gemini_available:
        settings = get_settings()
        if settings.gemini_api_key:
            _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def load_skill_text() -> str:
    """Load SKILL.md once at boot."""
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
    """Load a prompt .md file from app/agent/prompts/."""
    from pathlib import Path
    prompt_path = Path(__file__).parent / "prompts" / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    text = prompt_path.read_text(encoding="utf-8")
    # Inject SKILL.md where <<SKILL>> marker appears
    if "<<SKILL>>" in text:
        # Escape braces in SKILL.md so they survive .format() calls downstream
        skill = load_skill_text().replace("{", "{{").replace("}", "}}")
        text = text.replace("<<SKILL>>", skill)
    return text


def _extract_json(text: str) -> Any:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try direct parse first
    text = text.strip()
    if text.startswith("```"):
        # Strip code block markers
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object/array in the text
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse JSON from LLM response: %s", text[:200])
        return None


async def _gemini_call(
    prompt: str,
    system: str = "",
    max_tokens: int = 1024,
    temperature: float = 0.1,
    timeout: float = 20.0,
) -> str:
    """Final fallback when both Groq main and cheap models fail."""
    client = _get_gemini_client()
    if client is None:
        raise RuntimeError("Gemini not available (no API key or SDK not installed)")
    settings = get_settings()
    model_name = settings.gemini_model

    full_prompt = f"{system}\n\n{prompt}" if system else prompt

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
        return resp.text or ""
    except asyncio.TimeoutError:
        logger.warning("Gemini %s timed out after %.1fs", model_name, timeout)
        raise
    except Exception as e:
        logger.warning("Gemini %s failed: %s", model_name, e)
        raise


async def _groq_call(
    prompt: str,
    model: str | None = None,
    system: str = "",
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.1,
    timeout: float = 15.0,
) -> str:
    """Make a Groq API call with timeout and fallback chain:
    main -> cheap -> Gemini."""
    settings = get_settings()
    model = model or settings.groq_model_main
    client = _get_groq()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": model,
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
        return resp.choices[0].message.content or ""
    except (RateLimitError, APIStatusError) as e:
        logger.warning("Groq %s failed (%s), trying fallback...", model, e)
        if model == settings.groq_model_main:
            try:
                return await _groq_call(
                    prompt, model=settings.groq_model_cheap,
                    system=system, json_mode=json_mode,
                    max_tokens=max_tokens, temperature=temperature,
                    timeout=timeout,
                )
            except Exception:
                pass
        # Both Groq models failed -> try Gemini
        if settings.gemini_api_key and _gemini_available:
            logger.warning("Both Groq models exhausted, falling back to Gemini %s", settings.gemini_model)
            return await _gemini_call(prompt, system=system, max_tokens=max_tokens,
                                     temperature=temperature, timeout=timeout)
        raise
    except asyncio.TimeoutError:
        logger.warning("Groq %s timed out after %.1fs, trying fallback...", model, timeout)
        if model == settings.groq_model_main:
            try:
                return await _groq_call(
                    prompt, model=settings.groq_model_cheap,
                    system=system, json_mode=json_mode,
                    max_tokens=max_tokens, temperature=temperature,
                    timeout=timeout,
                )
            except Exception:
                pass
        # Both Groq models failed -> try Gemini
        if settings.gemini_api_key and _gemini_available:
            logger.warning("Both Groq models timed out, falling back to Gemini %s", settings.gemini_model)
            return await _gemini_call(prompt, system=system, max_tokens=max_tokens,
                                     temperature=temperature, timeout=timeout)
        raise


async def call_main(prompt: str, system: str = "", json_mode: bool = False,
                    max_tokens: int = 1024, temperature: float = 0.1) -> str:
    """Call the main (70B) model."""
    settings = get_settings()
    return await _groq_call(
        prompt, model=settings.groq_model_main,
        system=system, json_mode=json_mode,
        max_tokens=max_tokens, temperature=temperature,
        timeout=settings.per_call_timeout,
    )


async def call_cheap(prompt: str, system: str = "", json_mode: bool = False,
                     max_tokens: int = 256, temperature: float = 0.0) -> str:
    """Call the cheap (8B) model."""
    settings = get_settings()
    return await _groq_call(
        prompt, model=settings.groq_model_cheap,
        system=system, json_mode=json_mode,
        max_tokens=max_tokens, temperature=temperature,
        timeout=settings.per_call_timeout,
    )


async def call_json(prompt: str, system: str = "",
                    model: str | None = None, max_tokens: int = 1024) -> Any:
    """Call LLM with JSON mode and parse the result."""
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


def extract_json_from_text(text: str) -> Any:
    """Sync helper to extract JSON from text."""
    return _extract_json(text)
