from __future__ import annotations

from pathlib import Path
from typing import Any

from common.http import CachedJsonClient
from common.schema import normalize_doi


class CrossrefClient:
    base_url = "https://api.crossref.org"

    def __init__(self, cache_dir: Path, mailto: str | None = None, plus_token: str | None = None, timeout: int = 30):
        self.mailto = mailto
        self.plus_token = plus_token
        self.http = CachedJsonClient(self.base_url, cache_dir / "crossref", timeout=timeout)

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": "readingpaper-skills/0.1"}
        if self.mailto:
            headers["User-Agent"] += f" (mailto:{self.mailto})"
        if self.plus_token:
            headers["Crossref-Plus-API-Token"] = f"Bearer {self.plus_token}"
        return headers

    def get_work_by_doi(self, doi: str) -> dict[str, Any] | None:
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        params = {"mailto": self.mailto} if self.mailto else {}
        try:
            return self.http.get_json(f"/works/{normalized}", params, self._headers()).get("message")
        except Exception:
            return None

    def search_by_title(self, title: str) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query.title": title, "rows": 5}
        if self.mailto:
            params["mailto"] = self.mailto
        try:
            return self.http.get_json("/works", params, self._headers()).get("message", {}).get("items", [])
        except Exception:
            return []
