<<SKILL>>

Extract structured slots from the entire conversation history below.

History (oldest first):
{messages_compact}

Return ONLY a JSON object with this exact shape (omit unknown values as null
or empty list — do not invent):

{{
  "role": <string|null>,
  "seniority": <"junior"|"mid"|"senior"|"lead"|null>,
  "duration_max_min": <int|null>,
  "test_types_wanted": <list of letter codes from {{"A","B","C","D","E","K","P","S"}}>,
  "test_types_avoided": <list>,
  "language": <string|null>,
  "remote_required": <bool|null>,
  "must_haves": <list of short strings>,
  "must_avoids": <list of short strings>
}}

Rules:
- If the user contradicts an earlier statement, the LATER message wins.
- Map natural language to letter codes (e.g. "personality" -> "P", "coding" -> "K").
- Do NOT add anything that is not explicitly supported by the conversation.
