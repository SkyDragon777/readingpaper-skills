from __future__ import annotations

from pathlib import Path
from typing import Any

from common.http import CachedJsonClient


class SemanticScholarClient:
    base_url = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, cache_dir: Path, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key
        self.http = CachedJsonClient(self.base_url, cache_dir / "semantic_scholar", timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key} if self.api_key else {}

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        try:
            return self.http.get_json(path, params or {}, self._headers())
        except Exception:
            return None

    def get_paper_by_doi(self, doi: str) -> dict[str, Any] | None:
        return self._get(f"/paper/DOI:{doi}", {"fields": "title,year,authors,citationCount,references,citations,externalIds"})

    def get_paper_by_arxiv(self, arxiv_id: str) -> dict[str, Any] | None:
        return self._get(f"/paper/ARXIV:{arxiv_id}", {"fields": "title,year,authors,citationCount,references,citations,externalIds"})

    def get_recommendations(self, seed_ids: list[str]) -> list[dict[str, Any]]:
        if not seed_ids:
            return []
        data = self._get("/recommendations", {"positivePaperIds": ",".join(seed_ids), "fields": "title,year,authors,externalIds"})
        return (data or {}).get("recommendedPapers", [])

    def get_citations_or_references(self, paper_id: str) -> dict[str, list[dict[str, Any]]]:
        data = self._get(f"/paper/{paper_id}", {"fields": "references,citations"})
        return {"references": (data or {}).get("references", []), "citations": (data or {}).get("citations", [])}
