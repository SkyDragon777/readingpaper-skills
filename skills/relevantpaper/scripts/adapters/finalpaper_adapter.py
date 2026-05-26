from __future__ import annotations

from pathlib import Path
from typing import Any

from common.schema import load_json, normalize_seed, seed_envelope


def normalize_finalpaper_output(path: str | Path) -> dict[str, Any]:
    data = load_json(path)
    if isinstance(data, dict) and data.get("schema_version") == "readingpaper.seed_papers.v1":
        seeds = [normalize_seed(seed, i + 1, data.get("created_by") or "finalpaper") for i, seed in enumerate(data.get("seed_papers", []))]
        return seed_envelope(seeds, data.get("created_by") or "finalpaper")
    if isinstance(data, dict):
        raw = data.get("seed_papers") or data.get("papers") or data.get("records") or []
        if isinstance(raw, dict):
            raw = [raw]
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    seeds = [normalize_seed(seed, i + 1, "finalpaper") for i, seed in enumerate(raw)]
    return seed_envelope(seeds, "finalpaper")
