from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import requests

from common.schema import safe_slug, utc_now
from pipeline.pdf_discovery import discover_pdf_url, is_disallowed_url


def download_pdfs(records: list[dict[str, Any]], output_dir: Path, max_downloads: int = 40, timeout: int = 30, verify_pdf_header: bool = True) -> list[dict[str, Any]]:
    papers_dir = output_dir / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    downloads: list[dict[str, Any]] = []
    attempted = 0
    for record in records:
        url, source = discover_pdf_url(record)
        manifest = {
            "paper_id": record["paper_id"],
            "title": record.get("title"),
            "download_status": "unavailable",
            "pdf_url": url,
            "source": source,
            "file": None,
            "sha256": None,
            "bytes": 0,
            "retrieved_at": utc_now(),
            "failure_reason": None,
        }
        if not url:
            manifest["failure_reason"] = "no verified legal open-access PDF URL"
            record["download"] = {"status": "unavailable", "file": None, "sha256": None, "bytes": 0, "source": None, "failure_reason": manifest["failure_reason"]}
            downloads.append(manifest)
            continue
        if attempted >= max_downloads:
            manifest["download_status"] = "skipped"
            manifest["failure_reason"] = "max_downloads reached"
            record["download"] = {"status": "skipped", "file": None, "sha256": None, "bytes": 0, "source": source, "failure_reason": manifest["failure_reason"]}
            downloads.append(manifest)
            continue
        if is_disallowed_url(url):
            manifest["download_status"] = "rejected"
            manifest["failure_reason"] = "disallowed source"
            record["download"] = {"status": "rejected", "file": None, "sha256": None, "bytes": 0, "source": source, "failure_reason": manifest["failure_reason"]}
            downloads.append(manifest)
            continue
        attempted += 1
        try:
            response = requests.get(url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "readingpaper-skills/0.1"})
            manifest["http_status"] = response.status_code
            manifest["content_type"] = response.headers.get("content-type")
            response.raise_for_status()
            content = response.content
            if verify_pdf_header and not content.startswith(b"%PDF"):
                raise ValueError("response did not start with %PDF")
            digest = hashlib.sha256(content).hexdigest()
            year = record.get("year") or "undated"
            title = safe_slug(record.get("title") or record["paper_id"], 60)
            path = papers_dir / f"{year}_{title}.pdf"
            path.write_bytes(content)
            rel = path.as_posix()
            manifest.update({"download_status": "downloaded", "file": rel, "sha256": digest, "bytes": len(content)})
            record["download"] = {"status": "downloaded", "file": rel, "sha256": digest, "bytes": len(content), "source": source, "failure_reason": None}
        except Exception as exc:
            manifest["download_status"] = "failed"
            manifest["failure_reason"] = str(exc)
            record["download"] = {"status": "failed", "file": None, "sha256": None, "bytes": 0, "source": source, "failure_reason": str(exc)}
        downloads.append(manifest)
    return downloads
