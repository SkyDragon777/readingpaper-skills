from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from common.schema import load_json, normalize_seed, seed_envelope


DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.I)
ARXIV_RE = re.compile(r"(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+/\d{7}(?:v\d+)?)", re.I)


def load_manual_seed_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if p.suffix.lower() == ".json":
        data = load_json(p)
        raw = data.get("seed_papers") if isinstance(data, dict) else data
        if isinstance(raw, dict):
            raw = [raw]
        return seed_envelope([normalize_seed(seed, i + 1, "manual") for i, seed in enumerate(raw or [])], "manual")
    return parse_seed_lines(p.read_text(encoding="utf-8").splitlines())


def parse_seed_lines(lines: list[str]) -> dict[str, Any]:
    seeds: list[dict[str, Any]] = []
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        doi = DOI_RE.search(text)
        arxiv = ARXIV_RE.search(text)
        raw = {"title": text}
        if doi:
            raw["doi"] = doi.group(0).rstrip(".,;")
            raw["title"] = text.replace(doi.group(0), "").strip(" -;\t") or raw["doi"]
        if arxiv:
            raw["arxiv_id"] = arxiv.group(1)
        seeds.append(normalize_seed(raw, len(seeds) + 1, "manual"))
    return seed_envelope(seeds, "manual")
