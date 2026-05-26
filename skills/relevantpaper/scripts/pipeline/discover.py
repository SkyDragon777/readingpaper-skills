from __future__ import annotations

from typing import Any


def relation(seed: dict[str, Any], label: str, source: str, evidence: str) -> dict[str, str]:
    return {"seed_id": seed["seed_id"], "relation": label, "source": source, "evidence": evidence}


def semantic_query(seed: dict[str, Any]) -> str:
    parts = [seed.get("title") or "", seed.get("abstract") or ""]
    parts.extend(seed.get("key_claims") or [])
    parts.extend(seed.get("methods") or [])
    parts.extend(seed.get("datasets") or [])
    return " ".join(p for p in parts if p)[:1200]


def discover_candidates(resolved_seeds: list[dict[str, Any]], client: Any, config: dict[str, Any]) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, int]]:
    discovery = config["discovery"]
    max_per = discovery.get("max_per_seed", {})
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    counts = {"backward": 0, "forward": 0, "related": 0, "semantic": 0}
    for seed in resolved_seeds:
        oid = seed.get("openalex_id")
        work = seed.get("_work")
        if not oid or not work:
            continue
        if discovery.get("include_backward"):
            works = client.get_referenced_works(work)[: int(max_per.get("backward", 80))]
            counts["backward"] += len(works)
            candidates.extend((w, relation(seed, "referenced_by_seed", "openalex", f"referenced_works:{oid}")) for w in works)
        if discovery.get("include_forward"):
            works = client.get_citing_works(oid, per_page=int(max_per.get("forward", 80)))
            counts["forward"] += len(works)
            candidates.extend((w, relation(seed, "cites_seed", "openalex", f"filter=cites:{oid}")) for w in works)
        if discovery.get("include_related"):
            works = client.get_related_works(oid, per_page=int(max_per.get("related", 80)))
            counts["related"] += len(works)
            candidates.extend((w, relation(seed, "related_to_seed", "openalex", f"related_to:{oid}")) for w in works)
        if discovery.get("include_semantic"):
            query = semantic_query(seed)
            works = client.semantic_search(query, filters={}, per_page=int(max_per.get("semantic", 80))) if query else []
            counts["semantic"] += len(works)
            candidates.extend((w, relation(seed, "semantic_match", "openalex", "search.semantic")) for w in works)
    return candidates[: int(discovery.get("max_candidates", 200))], counts
