from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RELEVANT_COMMON = SCRIPT_DIR.parents[1] / "relevantpaper" / "scripts"
if str(RELEVANT_COMMON) not in sys.path:
    sys.path.insert(0, str(RELEVANT_COMMON))

from common.mineru import build_parse_manifest, build_reading_guide_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build reading_guide_source.json from existing MinerU output.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--mineru-dir", required=True)
    parser.add_argument("--category", default="seed", choices=["seed", "relevant"])
    parser.add_argument("--paper-slug")
    parser.add_argument("--title")
    args = parser.parse_args(argv)
    project_dir = Path(args.project_dir).resolve()
    mineru_dir = Path(args.mineru_dir)
    if not mineru_dir.is_absolute():
        mineru_dir = project_dir / mineru_dir
    slug = args.paper_slug or mineru_dir.name
    build_parse_manifest(project_dir, mineru_dir, args.category, slug)
    build_reading_guide_source(project_dir, mineru_dir, "finalpaper", slug, title=args.title)
    print(mineru_dir / "reading_guide_source.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
