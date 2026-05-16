Apply this rubric strictly, in priority order:

1) Hard match on test_types_wanted if specified. Discard non-matching types.

2) CORE INSTRUMENT PRIORITY (highest weight):
   - If the slots mention personality (P), leadership, management, sales,
     or any role that involves behavioral assessment, you MUST include
     "Occupational Personality Questionnaire OPQ32r" in your shortlist
     if it appears in the candidates. This is the foundational instrument
     that all OPQ-derived reports depend on.
   - Prefer broad/universal reports (e.g., "Universal Competency Report",
     "Leadership Report", "Sales Report") over narrow variants (e.g.,
     "Manager Plus Report", "Profile Report", "Action Planner Report")
     unless the user's role specifically matches the narrow variant.

3) Role-skill match: prefer assessments whose name closely matches the
   role keywords from slots.

4) Seniority fit: for senior/leadership roles, include leadership-specific
   reports alongside OPQ32r.

5) Skills audits and re-skilling queries: include "Global Skills Assessment"
   and "Global Skills Development Report" — these are the catalog's
   foundational skills products.

6) Duration fit: if duration_max_min is set, prefer items that fit.

7) Diverse coverage: if multiple test types are implied, include at least
   one of each.

8) Bundle pattern: when including an OPQ-derived report (e.g., OPQ Leadership
   Report, OPQ MQ Sales Report), also include OPQ32r itself — hiring
   managers need the foundational instrument that produces the report.

Return ONLY a JSON array of objects, no commentary:

[
  {{"catalog_id": <int>, "reason": "<one sentence why>"}},
  ...
]

- Length: 5 to 10 items. Order best-to-worst.
- Aim for 6-8 items for a well-rounded battery.
- Use only ids that appear in the candidates table.
- Reasons must reference fields from the candidate, not your prior knowledge.