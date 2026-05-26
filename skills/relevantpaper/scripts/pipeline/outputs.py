from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from common.schema import DOWNLOAD_MANIFEST_SCHEMA_VERSION, LITERATURE_INDEX_SCHEMA_VERSION, utc_now, write_json
from pipeline.bibtex import to_bibtex


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["paper_id", "title", "year", "doi", "openalex_id", "citation_count", "final_score", "download_status", "ranking_reason"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({
                "paper_id": record.get("paper_id"),
                "title": record.get("title"),
                "year": record.get("year"),
                "doi": record.get("doi"),
                "openalex_id": record.get("openalex_id"),
                "citation_count": record.get("citation_count"),
                "final_score": (record.get("scores") or {}).get("final"),
                "download_status": (record.get("download") or {}).get("status"),
                "ranking_reason": record.get("ranking_reason"),
            })


def make_literature_index(project_dir: Path, seeds: list[dict[str, Any]], records: list[dict[str, Any]], summary: dict[str, Any], backend_status: dict[str, Any]) -> dict[str, Any]:
    clean_seeds = [{k: v for k, v in seed.items() if k != "_work"} for seed in seeds]
    return {
        "schema_version": LITERATURE_INDEX_SCHEMA_VERSION,
        "created_by": "relevantpaper",
        "project_dir": str(project_dir),
        "created_at": utc_now(),
        "seeds": clean_seeds,
        "papers": records,
        "summary": summary,
        "backend_status": backend_status,
    }


def make_download_manifest(downloads: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_version": DOWNLOAD_MANIFEST_SCHEMA_VERSION, "created_by": "relevantpaper", "created_at": utc_now(), "downloads": downloads}


def write_run_report(path: Path, backend_status: dict[str, Any], summary: dict[str, Any], discovery_counts: dict[str, int], downloads: list[dict[str, Any]], unresolved: list[dict[str, Any]], manual_review: list[dict[str, Any]], warnings: list[str]) -> None:
    rows = ["| Backend | Status | Authentication | Notes |", "|---|---|---|---|"]
    notes = {"openalex": "primary backend", "semantic_scholar": "optional augmentation", "crossref": "DOI validation", "arxiv": "metadata/PDFs"}
    for name, status in backend_status.items():
        rows.append(f"| {name} | {status.get('status')} | {status.get('auth')} | {notes.get(name, '')} |")
    failed = [d for d in downloads if d.get("download_status") in {"failed", "rejected", "unavailable"}]
    text = [
        "# relevantpaper Run Report",
        "",
        "## Backend Configuration",
        *rows,
        "",
        "## Seed Resolution Summary",
        f"- Seeds: {summary.get('seed_count', 0)}",
        f"- Resolved: {summary.get('resolved_seed_count', 0)}",
        f"- Unresolved: {len(unresolved)}",
        "",
        "## Candidate Discovery Summary by Relation Type",
        *[f"- {k}: {v}" for k, v in discovery_counts.items()],
        "",
        "## Deduplication Summary",
        f"- Raw candidates: {summary.get('candidate_count_raw', 0)}",
        f"- Deduped candidates: {summary.get('candidate_count_deduped', 0)}",
        "",
        "## Ranking Summary",
        f"- Ranked papers: {summary.get('ranked_count', 0)}",
        f"- Manual review items: {summary.get('manual_review_count', 0)}",
        "",
        "## PDF Download Summary",
        f"- Downloaded: {summary.get('downloaded_count', 0)}",
        f"- Failed/unavailable/rejected: {len(failed)}",
        "",
        "## Failed Downloads",
        *[f"- {d.get('paper_id')}: {d.get('download_status')} ({d.get('failure_reason')})" for d in failed[:50]],
        "",
        "## Unresolved Seeds",
        *[f"- {s.get('seed_id')}: {s.get('title')} ({s.get('resolution', {}).get('confidence')})" for s in unresolved],
        "",
        "## Manual Review Items",
        *[f"- {p.get('paper_id')}: {p.get('title')}" for p in manual_review[:50]],
        "",
        "## Safety / Access Notes",
        "- Only legal open-access PDF URLs are attempted.",
        "- Piracy, paywall bypassing, shared credentials, cookies, and institutional scraping are disallowed.",
        *[f"- Warning: {w}" for w in warnings],
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(text), encoding="utf-8")


def write_outputs(output_dir: Path, project_dir: Path, seeds: list[dict[str, Any]], records: list[dict[str, Any]], downloads: list[dict[str, Any]], summary: dict[str, Any], backend_status: dict[str, Any], discovery_counts: dict[str, int], unresolved: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manual_review = [r for r in records if r.get("needs_review")]
    index = make_literature_index(project_dir, seeds, records, summary, backend_status)
    write_json(output_dir / "candidate_papers.json", records)
    write_json(output_dir / "literature_index.json", index)
    write_csv(output_dir / "literature_index.csv", records)
    (output_dir / "references.bib").write_text(to_bibtex(records), encoding="utf-8")
    write_json(output_dir / "download_manifest.json", make_download_manifest(downloads))
    write_run_report(output_dir / "run_report.md", backend_status, summary, discovery_counts, downloads, unresolved, manual_review, warnings)
    return index
