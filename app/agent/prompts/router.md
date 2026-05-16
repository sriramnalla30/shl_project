<<SKILL>>

You decide what the agent should do on its NEXT turn.

Conversation so far ({turn_count} turns used out of 8 max):
{messages_compact}

Currently known slots:
{slots_json}

Possible intents:
- "clarify"   : ask one focused question to fill a critical missing slot
- "extract"   : the user just gave new constraints; re-derive slots and continue
- "compare"   : the user asked to compare two named assessments
- "recommend" : we have enough; produce a 1-10 shortlist
- "refuse"    : out of scope; politely decline

Rules:
- If turn_count <= 1 AND role is missing in slots, choose "clarify".
- If role is known in slots, ALWAYS prefer "recommend" over "clarify".
- If the user just gave new constraints (test type, duration, skills, level), choose "extract".
- If the latest user message names two assessments with "vs" or "difference between", choose "compare".
- Default to "recommend" whenever you have ANY role information — committing imperfect recommendations beats returning none.

Answer with exactly one word from the list above.
