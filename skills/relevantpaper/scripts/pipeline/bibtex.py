from __future__ import annotations

import re
from typing import Any


def bibtex_key(record: dict[str, Any]) -> str:
    author = "anon"
    if record.get("authors"):
        name = record["authors"][0].get("name") if isinstance(record["authors"][0], dict) else str(record["authors"][0])
        author = re.sub(r"[^A-Za-z0-9]", "", name.split()[-1] if name else "anon").lower() or "anon"
    year = record.get("year") or "nd"
    title_word = re.sub(r"[^A-Za-z0-9]", "", (record.get("title") or "paper").split()[0]).lower() or "paper"
    return f"{author}{year}{title_word}"


def escape(value: object) -> str:
    return str(value or "").replace("{", "\\{").replace("}", "\\}")


def to_bibtex(records: list[dict[str, Any]]) -> str:
    entries: list[str] = []
    used: dict[str, int] = {}
    for record in records:
        key = bibtex_key(record)
        used[key] = used.get(key, 0) + 1
        if used[key] > 1:
            key = f"{key}{used[key]}"
        authors = " and ".join(a.get("name", "") if isinstance(a, dict) else str(a) for a in record.get("authors", []))
        fields = {
            "title": record.get("title"),
            "author": authors,
            "year": record.get("year"),
            "doi": record.get("doi"),
            "journal": (record.get("venue") or {}).get("name"),
            "url": (record.get("open_access") or {}).get("landing_page_url"),
        }
        lines = [f"@article{{{key},"]
        for name, value in fields.items():
            if value:
                lines.append(f"  {name} = {{{escape(value)}}},")
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries) + ("\n" if entries else "")
