<<SKILL>>

Rerank these candidates against the slots and pick the best 1 to 10 items.

Slots:
{slots_json}

Candidates (id, name, test_type, duration_minutes, summary):
{candidates_table}

Apply the rubric in SKILL §5 strictly:
1) Hard match on test_types_wanted if specified.
2) Role-skill match.
3) Seniority fit.
4) Duration fit.
5) Diverse coverage if multiple test types implied.
6) Prefer (New) tests for tech.

Return ONLY a JSON array of objects, no commentary:

[
  {{"catalog_id": <int>, "reason": "<one sentence why>"}},
  ...
]

- Length: 1 to 10. Order best-to-worst.
- Use only ids that appear in the candidates table.
- Reasons must reference fields from the candidate, not your prior knowledge.
