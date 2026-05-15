"""Quick LLM debug script."""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from app.agent.llm import call_json, call_cheap, load_skill_text

async def main():
    # Test 1: Basic call
    print("=== Test 1: Basic cheap call ===")
    r = await call_cheap("Say hello in one word.")
    print(f"Response: {r!r}")

    # Test 2: JSON mode
    print("\n=== Test 2: JSON call ===")
    r = await call_json(
        'Extract slots from this conversation:\n'
        'user: I need a personality test for a senior software engineer, under 30 minutes\n\n'
        'Return JSON: {"role": "string or null", "seniority": "string or null", '
        '"duration_max_min": "int or null", "test_types_wanted": ["list of codes"]}'
    )
    print(f"Parsed: {r}")

    # Test 3: SKILL load
    print("\n=== Test 3: SKILL.md ===")
    skill = load_skill_text()
    print(f"SKILL.md length: {len(skill)} chars")

asyncio.run(main())
