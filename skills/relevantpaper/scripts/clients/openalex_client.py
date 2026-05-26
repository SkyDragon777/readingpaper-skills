from __future__ import annotations

from pathlib import Path
from typing import Any

from common.http import CachedJsonClient
from common.schema import normalize_doi


class OpenAlexClient:
    base_url = "https://api.openalex.org"

    def __init__(self, cache_dir: Path, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key
        self.http = CachedJsonClient(self.base_url, cache_dir / "openalex", api_key=api_key, timeout=timeout)

    def _params(self, **params: Any) -> dict[str, Any]:
        data = {k: v for k, v in params.items() if v is not None}
        if self.api_key:
            data["api_key"] = self.api_key
        return data

    def get_work_by_doi(self, doi: str) -> dict[str, Any] | None:
        normalized = normalize_doi(doi)
        if not normalized:
            return None
        try:
            return self.http.get_json(f"/works/doi:{normalized}", self._params())
        except Exception:
            return None

    def search_works_by_title(self, title: str, per_page: int = 5) -> list[dict[str, Any]]:
        try:
            data = self.http.get_json("/works", self._params(search=title, per_page=per_page))
            return data.get("results", [])
        except Exception:
            return []

    def get_work(self, openalex_id: str) -> dict[str, Any] | None:
        oid = str(openalex_id).rstrip("/").split("/")[-1]
        try:
            return self.http.get_json(f"/works/{oid}", self._params())
        except Exception:
            return None

    def get_works_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        clean = [str(i).rstrip("/").split("/")[-1] for i in ids if i]
        if not clean:
            return []
        try:
            data = self.http.get_json("/works", self._params(filter="openalex:" + "|".join(clean), per_page=len(clean)))
            return data.get("results", [])
        except Exception:
            works = [self.get_work(oid) for oid in clean]
            return [w for w in works if w]

    def get_referenced_works(self, work: dict[str, Any]) -> list[dict[str, Any]]:
        ids = work.get("referenced_works") or []
        return self.get_works_by_ids(ids)

    def get_citing_works(self, openalex_id: str, per_page: int = 80) -> list[dict[str, Any]]:
        oid = str(openalex_id).rstrip("/").split("/")[-1]
        try:
            data = self.http.get_json("/works", self._params(filter=f"cites:{oid}", per_page=per_page, sort="cited_by_count:desc"))
            return data.get("results", [])
        except Exception:
            return []

    def get_related_works(self, openalex_id: str, per_page: int = 80) -> list[dict[str, Any]]:
        work = self.get_work(openalex_id)
        ids = (work or {}).get("related_works") or []
        if ids:
            return self.get_works_by_ids(ids[:per_page])
        oid = str(openalex_id).rstrip("/").split("/")[-1]
        try:
            data = self.http.get_json("/works", self._params(filter=f"related_to:{oid}", per_page=per_page))
            return data.get("results", [])
        except Exception:
            return []

    def semantic_search(self, query: str, filters: dict[str, Any] | None = None, per_page: int = 80) -> list[dict[str, Any]]:
        params = {"search": query[:1200], "per_page": per_page}
        filter_parts: list[str] = []
        for key, value in (filters or {}).items():
            if value is not None:
                filter_parts.append(f"{key}:{value}")
        if filter_parts:
            params["filter"] = ",".join(filter_parts)
        try:
            data = self.http.get_json("/works", self._params(**params))
            return data.get("results", [])
        except Exception:
            return []
