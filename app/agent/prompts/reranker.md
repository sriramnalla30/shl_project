<<SKILL>>

Rerank these candidates against the slots and pick the best 1 to 10 items.

Slots:
{slots_json}

Candidates (id, name, test_type, duration_minutes, summary):
{candidates_table}

Apply this rubric strictly, in priority order:
1) Hard match on test_types_wanted if specified. Discard non-matching types.
2) Role-skill match: prefer assessments whose name or description closely matches the role.
3) Seniority fit: for senior/leadership roles, include leadership-specific reports (e.g., Leadership Report, Manager Plus).
4) For personality roles: include the core instrument (e.g., OPQ32r) AND its specialized reports (e.g., Leadership Report, Universal Competency Report).
5) Duration fit: if duration_max_min is set, prefer items that fit within budget.
6) Diverse coverage: if multiple test types are implied, include at least one of each type.
7) For technical skills: prefer assessments marked "(New)" in name over older versions.
8) Include BOTH the assessment instrument AND its most relevant reports — hiring managers need the full solution.

Return ONLY a JSON array of objects, no commentary:

[
  {{"catalog_id": <int>, "reason": "<one sentence why>"}},
  ...
]

- Length: 1 to 10. Order best-to-worst.
- Aim for 5-7 items for a well-rounded battery.
- Use only ids that appear in the candidates table.
- Reasons must reference fields from the candidate, not your prior knowledge.
