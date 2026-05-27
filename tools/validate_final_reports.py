from __future__ import annotations

import argparse
import re
from pathlib import Path


CN_REQUIRED = ["作者简介", "文章概览", "关键词", "深度概念", "逐图", "历史背景"]
EN_REQUIRED = ["Author Profiles", "Paper Overview", "Key Terms", "Deep Concept", "Figure-by-Figure", "Historical Background"]
METADATA_PATTERNS = [r"年份：", r"DOI：", r"相关性评分：", r"摘要状态：", r"PDF 状态：", r"摘要："]


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path.read_text(encoding="utf-8")


def markdown_images(text: str) -> list[str]:
    return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)


def validate_images(project_dir: Path, report_path: Path, text: str) -> list[str]:
    errors = []
    for target in markdown_images(text):
        path = (report_path.parent / target).resolve()
        if not path.exists():
            errors.append(f"Missing image target: {target}")
    return errors


def metadata_ratio(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 1.0
    count = sum(1 for line in lines if any(re.search(pattern, line) for pattern in METADATA_PATTERNS))
    return count / len(lines)


def validate(project_dir: Path) -> list[str]:
    out = project_dir / "outputs" / "synopticpaper"
    cn_path = out / "finalpaper_cn.md"
    en_path = out / "finalpaper.md"
    cn = read(cn_path)
    en = read(en_path)
    errors = []
    for term in CN_REQUIRED:
        if term not in cn:
            errors.append(f"Chinese report missing required section text: {term}")
    if "学术圈" not in cn and "学术影响" not in cn:
        errors.append("Chinese report missing academic community / impact section.")
    for term in EN_REQUIRED:
        if term not in en:
            errors.append(f"English report missing required section text: {term}")
    if "Academic Community" not in en and "Field Impact" not in en:
        errors.append("English report missing academic community / field impact section.")
    if metadata_ratio(cn) > 0.30:
        errors.append("Chinese report appears to be primarily a metadata dump.")
    seed_sources = list((project_dir / "mineru" / "seed").glob("*/reading_guide_source.json"))
    has_seed_figures = False
    for source in seed_sources:
        if '"figures": [' in source.read_text(encoding="utf-8") and '"figure_id"' in source.read_text(encoding="utf-8"):
            has_seed_figures = True
    if has_seed_figures and not markdown_images(cn):
        errors.append("Chinese report has seed figures but no Markdown image links.")
    errors.extend(validate_images(project_dir, cn_path, cn))
    errors.extend(validate_images(project_dir, en_path, en))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate synopticpaper deep final reports.")
    parser.add_argument("--project-dir", default=".")
    args = parser.parse_args()
    errors = validate(Path(args.project_dir).resolve())
    if errors:
        print("\n".join(errors))
        return 2
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
