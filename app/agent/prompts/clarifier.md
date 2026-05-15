<<SKILL>>

The agent needs to ask the user ONE focused question to fill the slot:
{target_slot}

Currently known:
{slots_json}

Write a single conversational sentence asking for {target_slot}.
- No greeting, no preamble.
- Acknowledge what you already know in at most one short clause.
- Maximum 25 words.

Return ONLY the question text. No JSON, no quotes.
