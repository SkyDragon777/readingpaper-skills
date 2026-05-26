from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sync() -> None:
    for skill in ["finalpaper", "relevantpaper", "synopticpaper"]:
        target = ROOT / "skills" / skill / "references" / "shared_schemas"
        target.mkdir(parents=True, exist_ok=True)
        for schema in (ROOT / "schemas").glob("*.json"):
            shutil.copy2(schema, target / schema.name)


if __name__ == "__main__":
    sync()
    print("synced shared schemas")
