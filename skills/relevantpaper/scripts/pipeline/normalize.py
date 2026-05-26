from __future__ import annotations

from typing import Any

from common.schema import normalize_arxiv_id, normalize_doi, utc_now


def abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str | None:
    if not index:
        return None
    positions: list[tuple[int, str]] = []
    for word, offsets in index.items():
        for offset in offsets:
            positions.append((offset, word))
    return " ".join(word for _, word in sorted(positions)) if positions else None


def openalex_id(value: str | None) -> str | None:
    if not value:
        return None
    return str(value).rstrip("/").split("/")[-1]


def normalize_openalex_work(work: dict[str, Any], relation: dict[str, Any] | None = None) -> dict[str, Any]:
    oid = openalex_id(work.get("id"))
    doi = normalize_doi(work.get("doi"))
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        authors.append({"name": author.get("display_name") or "", "orcid": author.get("orcid"), "openalex_id": openalex_id(author.get("id"))})
    source = work.get("primary_location", {}).get("source") or work.get("host_venue") or {}
    best_oa = work.get("best_oa_location") or {}
    primary = work.get("primary_location") or {}
    oa = work.get("open_access") or {}
    pdf_url = best_oa.get("pdf_url") or (primary.get("pdf_url") if oa.get("is_oa") else None)
    concepts = work.get("topics") or []
    topics = [
        {
            "domain": (t.get("domain") or {}).get("display_name") if isinstance(t.get("domain"), dict) else t.get("domain"),
            "field": (t.get("field") or {}).get("display_name") if isinstance(t.get("field"), dict) else t.get("field"),
            "subfield": (t.get("subfield") or {}).get("display_name") if isinstance(t.get("subfield"), dict) else t.get("subfield"),
            "topic": t.get("display_name") or t.get("topic"),
        }
        for t in concepts
        if isinstance(t, dict)
    ]
    record = {
        "paper_id": f"openalex:{oid}" if oid else (f"doi:{doi}" if doi else f"title:{work.get('title', '')[:48]}"),
        "title": work.get("title") or work.get("display_name") or "",
        "authors": authors,
        "year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "venue": {
            "name": source.get("display_name") or source.get("host_organization_name") or "",
            "type": source.get("type") or "",
            "issn": source.get("issn_l") or source.get("issn") or [],
        },
        "doi": doi,
        "arxiv_id": normalize_arxiv_id(((work.get("ids") or {}).get("arxiv"))),
        "openalex_id": oid,
        "semantic_scholar_id": None,
        "abstract": work.get("abstract") or abstract_from_inverted_index(work.get("abstract_inverted_index")),
        "citation_count": int(work.get("cited_by_count") or 0),
        "is_retracted": bool(work.get("is_retracted", False)),
        "is_paratext": bool(work.get("is_paratext", False)),
        "topics": topics,
        "relations_to_seed": [relation] if relation else [],
        "open_access": {
            "is_oa": bool(oa.get("is_oa", False)),
            "oa_status": oa.get("oa_status"),
            "best_pdf_url": pdf_url,
            "landing_page_url": best_oa.get("landing_page_url") or primary.get("landing_page_url"),
            "source": "openalex.best_oa_location" if best_oa.get("pdf_url") else "openalex.primary_location" if pdf_url else "openalex",
        },
        "download": {"status": "not_attempted", "file": None, "sha256": None, "bytes": 0, "source": None, "failure_reason": None},
        "scores": {},
        "ranking_reason": "",
        "needs_review": False,
        "provenance": {"sources": ["openalex"], "retrieved_at": utc_now()},
    }
    return record


def normalize_records(works_with_relations: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
    return [normalize_openalex_work(work, relation) for work, relation in works_with_relations]
