from __future__ import annotations

from typing import Any

from common.schema import first_author_name, normalize_title, title_similarity


def dedupe_key(record: dict[str, Any]) -> tuple[str, str] | None:
    if record.get("doi"):
        return ("doi", record["doi"].lower())
    if record.get("openalex_id"):
        return ("openalex", record["openalex_id"])
    if record.get("arxiv_id"):
        return ("arxiv", record["arxiv_id"])
    if record.get("semantic_scholar_id"):
        return ("semantic_scholar", record["semantic_scholar_id"])
    return None


def merge_records(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for key in ["doi", "arxiv_id", "openalex_id", "semantic_scholar_id", "abstract", "publication_date"]:
        if not base.get(key) and incoming.get(key):
            base[key] = incoming[key]
    if not base.get("authors") and incoming.get("authors"):
        base["authors"] = incoming["authors"]
    for rel in incoming.get("relations_to_seed", []):
        if rel not in base["relations_to_seed"]:
            base["relations_to_seed"].append(rel)
    base["provenance"]["sources"] = sorted(set(base.get("provenance", {}).get("sources", []) + incoming.get("provenance", {}).get("sources", [])))
    base["needs_review"] = bool(base.get("needs_review") or incoming.get("needs_review"))
    if incoming.get("citation_count", 0) > base.get("citation_count", 0):
        base["citation_count"] = incoming["citation_count"]
    return base


def fuzzy_duplicate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a.get("year") and b.get("year") and a["year"] != b["year"]:
        return False
    if title_similarity(a.get("title"), b.get("title")) < 0.92:
        return False
    aa = first_author_name(a.get("authors"))
    bb = first_author_name(b.get("authors"))
    return not aa or not bb or title_similarity(aa, bb) > 0.75


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    unique: list[dict[str, Any]] = []
    for record in records:
        key = dedupe_key(record)
        if key and key in by_key:
            merge_records(by_key[key], record)
            continue
        match = next((existing for existing in unique if fuzzy_duplicate(existing, record)), None)
        if match:
            match["needs_review"] = True
            merge_records(match, record)
            continue
        unique.append(record)
        if key:
            by_key[key] = record
    return unique
