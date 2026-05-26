from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


DISALLOWED_HOST_PARTS = ["sci-hub", "scihub", "libgen", "library genesis"]


def is_disallowed_url(url: str | None) -> bool:
    if not url:
        return True
    host = urlparse(url).netloc.lower()
    return any(part in host for part in DISALLOWED_HOST_PARTS)


def discover_pdf_url(record: dict[str, Any]) -> tuple[str | None, str | None]:
    if record.get("arxiv_id"):
        return f"https://arxiv.org/pdf/{record['arxiv_id']}.pdf", "arxiv"
    oa = record.get("open_access") or {}
    if oa.get("is_oa") and oa.get("best_pdf_url") and not is_disallowed_url(oa.get("best_pdf_url")):
        return oa.get("best_pdf_url"), oa.get("source") or "openalex.best_oa_location"
    return None, None
