from __future__ import annotations

from datetime import datetime, timezone
from math import log10
from typing import Any


RELATION_SCORES = {
    "seed": 1.0,
    "cites_seed": 0.90,
    "referenced_by_seed": 0.80,
    "related_to_seed": 0.75,
    "semantic_match": 0.70,
    "keyword_only": 0.35,
}


def relation_score(record: dict[str, Any]) -> float:
    labels = [r.get("relation") for r in record.get("relations_to_seed", [])]
    return max([RELATION_SCORES.get(label, 0.35) for label in labels] or [0.0])


def recency_score(year: int | None) -> float:
    if not year:
        return 0.3
    age = datetime.now(timezone.utc).year - int(year)
    if age <= 2:
        return 1.0
    if age <= 5:
        return 0.8
    if age <= 10:
        return 0.5
    return 0.3


def score_record(record: dict[str, Any]) -> dict[str, Any]:
    rel = relation_score(record)
    semantic = 0.8 if any(r.get("relation") == "semantic_match" for r in record.get("relations_to_seed", [])) else 0.45
    topic = 0.75 if record.get("topics") else 0.20
    recency = recency_score(record.get("year"))
    citation = min(1.0, log10((record.get("citation_count") or 0) + 1) / 3.0)
    venue = 0.6 if record.get("venue", {}).get("name") else 0.2
    oa = 1.0 if record.get("open_access", {}).get("is_oa") else 0.0
    retraction = 1.0 if record.get("is_retracted") else 0.0
    paratext = 1.0 if record.get("is_paratext") else 0.0
    final = (
        0.30 * rel
        + 0.20 * semantic
        + 0.15 * topic
        + 0.10 * recency
        + 0.10 * citation
        + 0.05 * venue
        + 0.05 * oa
        - 0.50 * retraction
        - 0.20 * paratext
    )
    record["scores"] = {
        "final": round(max(0.0, final), 4),
        "relation": round(rel, 4),
        "semantic": round(semantic, 4),
        "topic": round(topic, 4),
        "recency": round(recency, 4),
        "citation": round(citation, 4),
        "venue_signal": round(venue, 4),
        "open_access": round(oa, 4),
        "retraction_penalty": retraction,
        "paratext_penalty": paratext,
    }
    relations = sorted({r.get("relation") for r in record.get("relations_to_seed", []) if r.get("relation")})
    record["ranking_reason"] = f"Relations: {', '.join(relations) or 'none'}; citations: {record.get('citation_count', 0)}; OA: {bool(oa)}."
    return record


def rank_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((score_record(r) for r in records), key=lambda r: r["scores"]["final"], reverse=True)
