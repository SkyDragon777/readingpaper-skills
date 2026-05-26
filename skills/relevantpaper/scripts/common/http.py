from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from .schema import load_json, safe_slug, write_json


class CachedJsonClient:
    def __init__(self, base_url: str, cache_dir: Path, api_key: str | None = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def _cache_path(self, path: str, params: dict[str, Any]) -> Path:
        key = safe_slug(path + "-" + urlencode(sorted((k, str(v)) for k, v in params.items() if v is not None)), 160)
        return self.cache_dir / f"{key}.json"

    def get_json(self, path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        query = dict(params or {})
        cache_path = self._cache_path(path, query)
        if cache_path.exists():
            return load_json(cache_path)
        url = self.base_url + path
        delay = 1.0
        for attempt in range(4):
            response = self.session.get(url, params=query, headers=headers, timeout=self.timeout)
            if response.status_code == 429 and attempt < 3:
                time.sleep(delay)
                delay *= 2
                continue
            response.raise_for_status()
            data = response.json()
            write_json(cache_path, data)
            return data
        raise RuntimeError(f"GET {url} failed after retries")
