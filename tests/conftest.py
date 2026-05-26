from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "relevantpaper" / "scripts"
SYNOPTIC = ROOT / "skills" / "synopticpaper" / "scripts"
for path in [str(SYNOPTIC), str(ROOT), str(SCRIPTS)]:
    if path not in sys.path:
        sys.path.insert(0, path)


def fixture_path(name: str) -> Path:
    return ROOT / "tests" / "fixtures" / name
