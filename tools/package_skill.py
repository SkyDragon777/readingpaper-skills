from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def copy_shared(skill_dir: Path, build_dir: Path) -> None:
    shared = build_dir / "references" / "shared_schemas"
    shared.mkdir(parents=True, exist_ok=True)
    for schema in (ROOT / "schemas").glob("*.json"):
        shutil.copy2(schema, shared / schema.name)


def package_skill(name: str, out_dir: Path) -> Path:
    skill_dir = ROOT / "skills" / name
    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"Skill not found: {skill_dir}")
    staging = out_dir / f"{name}-package"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(skill_dir, staging)
    copy_shared(skill_dir, staging)
    archive = out_dir / f"{name}.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in staging.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(staging.parent))
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Package a readingpaper skill as a zip archive.")
    parser.add_argument("skill", choices=["finalpaper", "relevantpaper", "synopticpaper"])
    parser.add_argument("--out-dir", default="dist")
    args = parser.parse_args()
    out_dir = (ROOT / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = package_skill(args.skill, out_dir)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
