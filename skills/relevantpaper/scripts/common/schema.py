from __future__ import annotations

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


SEED_SCHEMA_VERSION = "readingpaper.seed_papers.v1"
LITERATURE_INDEX_SCHEMA_VERSION = "readingpaper.literature_index.v1"
DOWNLOAD_MANIFEST_SCHEMA_VERSION = "readingpaper.download_manifest.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    doi = doi.strip().lower()
    return doi or None


def normalize_arxiv_id(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    text = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", text, flags=re.I)
    text = re.sub(r"\.pdf$", "", text, flags=re.I)
    text = re.sub(r"^arxiv:\s*", "", text, flags=re.I)
    return text.strip() or None


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    text = value.casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(a: str | None, b: str | None) -> float:
    aa = normalize_title(a)
    bb = normalize_title(b)
    if not aa or not bb:
        return 0.0
    return SequenceMatcher(None, aa, bb).ratio()


def first_author_name(authors: list[Any] | None) -> str:
    if not authors:
        return ""
    first = authors[0]
    if isinstance(first, dict):
        return str(first.get("name") or "").strip()
    return str(first).strip()


def safe_slug(value: str, max_len: int = 80) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return (text[:max_len].strip("-") or "paper")


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_seed(raw: dict[str, Any], index: int = 1, source: str = "manual") -> dict[str, Any]:
    title = str(raw.get("title") or "").strip()
    doi = normalize_doi(raw.get("doi"))
    arxiv_id = normalize_arxiv_id(raw.get("arxiv_id") or raw.get("arxiv"))
    needs_review = bool(raw.get("needs_review", False)) or not bool(doi or arxiv_id or title)
    confidence = raw.get("metadata_confidence") or ("high" if doi else "medium" if title else "low")
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
        needs_review = True
    provenance = dict(raw.get("provenance") or {})
    provenance.setdefault("source", source)
    if raw.get("source_file"):
        provenance.setdefault("extracted_from", raw.get("source_file"))
    return {
        "seed_id": raw.get("seed_id") or f"seed-{index:03d}",
        "source_file": raw.get("source_file"),
        "title": title,
        "authors": [str(a.get("name") if isinstance(a, dict) else a) for a in ensure_list(raw.get("authors")) if a],
        "year": raw.get("year"),
        "doi": doi,
        "arxiv_id": arxiv_id,
        "abstract": raw.get("abstract"),
        "keywords": [str(v) for v in ensure_list(raw.get("keywords"))],
        "key_claims": [str(v) for v in ensure_list(raw.get("key_claims") or raw.get("claims"))],
        "methods": [str(v) for v in ensure_list(raw.get("methods"))],
        "datasets": [str(v) for v in ensure_list(raw.get("datasets"))],
        "metadata_confidence": confidence,
        "needs_review": needs_review,
        "provenance": provenance,
    }


def seed_envelope(seed_papers: list[dict[str, Any]], created_by: str = "finalpaper") -> dict[str, Any]:
    return {
        "schema_version": SEED_SCHEMA_VERSION,
        "created_by": created_by,
        "created_at": utc_now(),
        "seed_papers": seed_papers,
    }


def load_json(path: str | Path) -> Any:
    import json

    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: str | Path, data: Any) -> None:
    import json

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
