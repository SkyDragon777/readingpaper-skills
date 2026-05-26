from __future__ import annotations

from .schema import utc_now


def provenance(source: str, **extra: object) -> dict[str, object]:
    data: dict[str, object] = {"sources": [source], "retrieved_at": utc_now()}
    data.update(extra)
    return data
