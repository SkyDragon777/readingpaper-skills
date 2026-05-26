from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = {
    "relevantpaper": [
        "outputs/relevantpaper/literature_index.json",
        "outputs/relevantpaper/literature_index.csv",
        "outputs/relevantpaper/candidate_papers.json",
        "outputs/relevantpaper/references.bib",
        "outputs/relevantpaper/download_manifest.json",
        "outputs/relevantpaper/run_report.md",
    ],
    "synopticpaper": [
        "outputs/synopticpaper/synoptic_review.md",
        "outputs/synopticpaper/evidence_map.json",
        "outputs/synopticpaper/research_gaps.md",
        "outputs/synopticpaper/reading_plan.md",
    ],
}


def validate(project_dir: Path, skill: str) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED[skill]:
        if not (project_dir / rel).exists():
            errors.append(f"Missing {rel}")
    for rel in [p for p in REQUIRED[skill] if p.endswith(".json")]:
        path = project_dir / rel
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"Invalid JSON {rel}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate readingpaper output files.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--skill", choices=sorted(REQUIRED), required=True)
    args = parser.parse_args()
    errors = validate(Path(args.project_dir), args.skill)
    if errors:
        print("\n".join(errors))
        return 2
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
