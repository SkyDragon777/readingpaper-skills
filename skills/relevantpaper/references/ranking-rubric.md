# Ranking Rubric

The ranking score is heuristic. It is not a claim of absolute academic quality.

Score components:

final_score =
  0.30 * relation_score
+ 0.20 * semantic_score
+ 0.15 * topic_score
+ 0.10 * recency_score
+ 0.10 * citation_score
+ 0.05 * venue_signal
+ 0.05 * open_access_score
- 0.50 * retraction_penalty
- 0.20 * paratext_penalty

Every paper must include score components and a human-readable ranking_reason.

Prefer papers that:
- cite seed papers
- are cited by seed papers
- are semantically similar to seed abstracts/claims
- share topic/subfield/field with seed papers
- are recent, unless foundational
- have strong citation signal
- have legal OA PDF availability

Exclude or heavily penalize:
- retracted papers
- paratext
- weak keyword-only matches
- ambiguous metadata matches
