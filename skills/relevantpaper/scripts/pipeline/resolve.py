from __future__ import annotations

from typing import Any

from common.schema import first_author_name, title_similarity
from pipeline.normalize import normalize_openalex_work, openalex_id


def match_confidence(seed: dict[str, Any], work: dict[str, Any]) -> float:
    if seed.get("doi") and str(work.get("doi") or "").lower().endswith(seed["doi"].lower()):
        return 1.0
    score = 0.0
    score += 0.55 * title_similarity(seed.get("title"), work.get("title") or work.get("display_name"))
    if seed.get("year") and seed.get("year") == work.get("publication_year"):
        score += 0.20
    work_authors = normalize_openalex_work(work).get("authors") or []
    if first_author_name(seed.get("authors")) and title_similarity(first_author_name(seed.get("authors")), first_author_name(work_authors)) > 0.75:
        score += 0.15
    if seed.get("arxiv_id") and seed.get("arxiv_id") in str(work.get("ids") or {}):
        score += 0.20
    return min(score, 0.95)


def resolve_seeds(seeds: list[dict[str, Any]], client: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for seed in seeds:
        work = None
        confidence = 0.0
        method = "unresolved"
        if seed.get("doi"):
            work = client.get_work_by_doi(seed["doi"])
            if work:
                confidence = 1.0
                method = "doi"
        if not work and seed.get("title"):
            candidates = client.search_works_by_title(seed["title"], per_page=5)
            if candidates:
                scored = sorted(((match_confidence(seed, c), c) for c in candidates), reverse=True, key=lambda item: item[0])
                confidence, work = scored[0]
                method = "title"
        if work and confidence >= 0.65:
            copy = dict(seed)
            copy["openalex_id"] = openalex_id(work.get("id"))
            copy["resolution"] = {"source": "openalex", "method": method, "confidence": round(confidence, 3)}
            if confidence < 0.85:
                copy["needs_review"] = True
            copy["_work"] = work
            resolved.append(copy)
        else:
            copy = dict(seed)
            copy["resolution"] = {"source": "openalex", "method": method, "confidence": round(confidence, 3)}
            copy["needs_review"] = True
            unresolved.append(copy)
    return resolved, unresolved
