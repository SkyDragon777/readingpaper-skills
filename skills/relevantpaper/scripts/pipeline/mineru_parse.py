from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from common.mineru import MinerUFullClient, build_parse_manifest, build_reading_guide_source, safe_slug


def parse_selected_relevant_papers_with_mineru(records: list[dict[str, Any]], downloads: list[dict[str, Any]], project_dir: Path, env: dict[str, str]) -> list[dict[str, Any]]:
    skip = str(env.get("RELEVANTPAPER_SKIP_MINERU_FOR_RELEVANT", "false")).lower() in {"1", "true", "yes", "on"}
    max_parse = int(env.get("RELEVANTPAPER_MAX_MINERU_PARSE") or 8)
    mode = env.get("MINERU_PARSE_MODE") or "full"
    token = env.get("MINERU_API_TOKEN")
    download_by_id = {str(item.get("paper_id")): item for item in downloads if item.get("paper_id")}
    parsed: list[dict[str, Any]] = []
    selected = [record for record in records if (download_by_id.get(str(record.get("paper_id"))) or {}).get("download_status") == "downloaded"][:max_parse]
    selected_ids = {str(record.get("paper_id")) for record in selected}
    for record in records:
        manifest = download_by_id.get(str(record.get("paper_id")))
        if not manifest:
            continue
        if manifest.get("download_status") != "downloaded":
            manifest["parse_status"] = "not_downloaded"
            continue
        if str(record.get("paper_id")) not in selected_ids:
            manifest["parse_status"] = "parse_skipped_not_selected"
            continue
        if skip:
            manifest["parse_status"] = "parse_skipped_by_config"
            continue
        if mode != "full":
            manifest["parse_status"] = "parse_failed"
            manifest["parse_error"] = "MINERU_PARSE_MODE must be full for deep reading guides."
            continue
        if not token:
            manifest["parse_status"] = "parse_skipped_no_token"
            continue
        pdf_path = Path(str(manifest.get("file") or ""))
        if not pdf_path.is_absolute():
            pdf_path = project_dir / pdf_path
        slug = safe_slug(f"{record.get('year') or 'undated'}-{record.get('title') or record.get('paper_id')}")
        try:
            client = MinerUFullClient(token)
            parse_manifest = client.parse_pdf_to_mineru_dir(pdf_path, project_dir, "relevant", slug, record.get("paper_id"))
            mineru_dir = project_dir / parse_manifest["mineru_dir"]
            source = build_reading_guide_source(project_dir, mineru_dir, "relevantpaper", slug, record.get("paper_id"), record.get("title"), record.get("authors"), record.get("year"), record.get("doi"), record.get("arxiv_id"))
            manifest["parse_status"] = "parsed"
            manifest["mineru"] = source["mineru"]
            parsed.append({"paper_id": record.get("paper_id"), "title": record.get("title"), "paper_slug": slug, "parse_status": "parsed", "mineru": source["mineru"]})
        except Exception as exc:
            manifest["parse_status"] = "parse_failed"
            manifest["parse_error"] = str(exc)
            failure_dir = project_dir / "mineru" / "relevant" / slug
            failure_dir.mkdir(parents=True, exist_ok=True)
            build_parse_manifest(project_dir, failure_dir, "relevant", slug, str(pdf_path), record.get("paper_id"), parse_status="failed", parse_error=str(exc))
            parsed.append({"paper_id": record.get("paper_id"), "title": record.get("title"), "paper_slug": slug, "parse_status": "parse_failed", "parse_error": str(exc)})
    return parsed
