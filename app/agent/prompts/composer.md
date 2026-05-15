<<SKILL>>

Write the agent's reply for a RECOMMEND turn.

Slots used:
{slots_json}

Shortlist (will be returned in the JSON `recommendations` field):
{shortlist_table}

{feedback_block}

Write a JSON object with exactly these keys:

{{
  "reply": "<conversational summary, 1-3 sentences, mentioning the count and one defining theme of the shortlist; do NOT name individual items unless they are in the shortlist>",
  "recommendations": [
    {{"name": "<exact name>", "url": "<exact url>", "test_type": "<letter codes>"}},
    ... // 1-10 items, in the order from the shortlist above
  ],
  "end_of_conversation": true
}}

Rules:
- Use the EXACT names and URLs from the shortlist. No edits, no reformatting.
- end_of_conversation is true here.
- Output ONLY the JSON object.
