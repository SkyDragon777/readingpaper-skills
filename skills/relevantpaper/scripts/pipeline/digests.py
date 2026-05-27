from __future__ import annotations

from typing import Any

from common.schema import utc_now


PAPER_DIGESTS_SCHEMA_VERSION = "readingpaper.paper_digests.v1"


def normalize_relations(record: dict[str, Any]) -> list[str]:
    if isinstance(record.get("relations_to_seed"), list):
        labels = []
        for relation in record["relations_to_seed"]:
            if isinstance(relation, dict) and relation.get("relation"):
                labels.append(str(relation["relation"]))
            elif isinstance(relation, str):
                labels.append(relation)
        return sorted(set(labels))
    relation_to_seed = record.get("relation_to_seed")
    if isinstance(relation_to_seed, list):
        return sorted({str(item.get("relation") if isinstance(item, dict) else item) for item in relation_to_seed if item})
    if relation_to_seed:
        return [str(relation_to_seed)]
    return []


def normalize_score(record: dict[str, Any]) -> float:
    scores = record.get("scores") or {}
    if isinstance(scores, dict) and scores.get("final") is not None:
        return float(scores["final"])
    if record.get("relevance_score") is not None:
        return float(record["relevance_score"])
    return 0.0


def normalize_title(record: dict[str, Any]) -> str:
    return str(record.get("title") or record.get("display_name") or "Untitled paper")


def pdf_parse_status(record: dict[str, Any], download_by_id: dict[str, dict[str, Any]]) -> str:
    paper_id = record.get("paper_id") or record.get("id")
    manifest = download_by_id.get(str(paper_id), {})
    parse_status = manifest.get("parse_status")
    if parse_status:
        return str(parse_status)
    status = manifest.get("download_status") or (record.get("download") or {}).get("status")
    if status == "downloaded":
        return "downloaded_not_parsed"
    if status in {"failed", "rejected"}:
        return "parse_failed"
    return "not_downloaded"


def role_for_reading_guide(relations: list[str]) -> str:
    if "referenced_by_seed" in relations:
        return "foundational_for_seed"
    if "semantic_match" in relations or "related_to_seed" in relations:
        return "explains_core_concept"
    if "cites_seed" in relations:
        return "direct_successor"
    return "low_priority"


def digest_summary(record: dict[str, Any], relations: list[str]) -> str:
    parts = []
    if record.get("abstract"):
        parts.append(str(record["abstract"]))
    if record.get("ranking_reason"):
        parts.append(str(record["ranking_reason"]))
    if relations:
        parts.append("Relations to seed: " + ", ".join(relations) + ".")
    if not parts:
        parts.append(f"Metadata-only digest for {normalize_title(record)}.")
    return " ".join(parts)


def build_paper_digests(literature_index: dict[str, Any], download_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    downloads = (download_manifest or {}).get("downloads") or []
    download_by_id = {str(item.get("paper_id")): item for item in downloads if item.get("paper_id")}
    digests = []
    for record in literature_index.get("papers") or []:
        relations = normalize_relations(record)
        title = normalize_title(record)
        score = normalize_score(record)
        parse_status = pdf_parse_status(record, download_by_id)
        manifest = download_by_id.get(str(record.get("paper_id") or record.get("id")), {})
        digests.append({
            "paper_id": record.get("paper_id") or record.get("id") or title,
            "paper_slug": (manifest.get("mineru") or {}).get("mineru_dir", "").rstrip("/").split("/")[-1] if manifest.get("mineru") else None,
            "title": title,
            "year": record.get("year"),
            "doi": record.get("doi"),
            "relation_to_seed": relations,
            "role_for_reading_guide": role_for_reading_guide(relations),
            "relevance_score": score,
            "digest_status": "pdf_digest" if parse_status == "parsed" else "metadata_digest" if parse_status != "parse_failed" else "failed",
            "pdf_parse_status": parse_status,
            "mineru": manifest.get("mineru"),
            "abstract": record.get("abstract"),
            "summary": digest_summary(record, relations),
            "contributions": [],
            "methods": [],
            "datasets": [],
            "findings": [],
            "limitations": [],
            "important_figures": [],
            "important_tables": [],
            "important_equations": [],
            "why_it_matters_for_seed": record.get("ranking_reason") or ("Related by " + ", ".join(relations) if relations else "Related paper discovered by metadata search."),
        })
    return {
        "schema_version": PAPER_DIGESTS_SCHEMA_VERSION,
        "created_by": "relevantpaper",
        "created_at": utc_now(),
        "digests": digests,
    }
