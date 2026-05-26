from __future__ import annotations

from pathlib import Path

from .schema import utc_now


class RunLog:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.events: list[dict[str, str]] = []

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        self.events.append({"level": "warning", "message": message, "created_at": utc_now()})

    def info(self, message: str) -> None:
        self.events.append({"level": "info", "message": message, "created_at": utc_now()})

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"[{e['created_at']}] {e['level'].upper()}: {e['message']}" for e in self.events]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
