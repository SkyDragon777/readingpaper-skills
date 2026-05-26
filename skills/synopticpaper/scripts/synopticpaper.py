from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def title_from_pdf_path(path: Path) -> str:
    text = path.stem.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text or path.stem


def find_pdf_files(project_dir: Path) -> list[Path]:
    roots = [project_dir / "input" / "papers", project_dir]
    seen: set[Path] = set()
    pdfs: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.pdf")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            pdfs.append(path)
    return pdfs


def bootstrap_seed_papers_from_pdfs(project_dir: Path) -> Path:
    out = project_dir / "outputs" / "finalpaper" / "seed_papers.json"
    if out.exists():
        return out
    pdfs = find_pdf_files(project_dir)
    if not pdfs:
        raise FileNotFoundError(
            "No seed file found and no PDFs found in the project root or input/papers/. "
            "Add PDFs or provide outputs/finalpaper/seed_papers.json."
        )
    seeds = []
    for index, pdf in enumerate(pdfs, start=1):
        rel = pdf.relative_to(project_dir).as_posix() if pdf.is_relative_to(project_dir) else pdf.as_posix()
        seeds.append({
            "seed_id": f"seed-{index:03d}",
            "source_file": rel,
            "title": title_from_pdf_path(pdf),
            "authors": [],
            "year": None,
            "doi": None,
            "arxiv_id": None,
            "abstract": None,
            "keywords": [],
            "key_claims": [],
            "methods": [],
            "datasets": [],
            "metadata_confidence": "low",
            "needs_review": True,
            "provenance": {
                "source": "synopticpaper.pdf_filename_bootstrap",
                "extracted_from": rel,
                "note": "Generated from PDF filename because finalpaper seed metadata was missing.",
            },
        })
    write_json(out, {
        "schema_version": "readingpaper.seed_papers.v1",
        "created_by": "synopticpaper",
        "created_at": utc_now(),
        "seed_papers": seeds,
    })
    return out


def validate_inputs(project_dir: Path) -> dict[str, Path]:
    paths = {
        "seed_papers": project_dir / "outputs" / "finalpaper" / "seed_papers.json",
        "literature_index": project_dir / "outputs" / "relevantpaper" / "literature_index.json",
        "references": project_dir / "outputs" / "relevantpaper" / "references.bib",
        "download_manifest": project_dir / "outputs" / "relevantpaper" / "download_manifest.json",
    }
    required = ["seed_papers", "literature_index"]
    missing = [name for name in required if not paths[name].exists()]
    if missing:
        raise FileNotFoundError("Missing required synopticpaper inputs: " + ", ".join(str(paths[name]) for name in missing))
    return paths


def classify_relation(record: dict[str, Any]) -> str:
    labels = {r.get("relation") for r in record.get("relations_to_seed", [])}
    if "referenced_by_seed" in labels:
        return "foundational"
    if "cites_seed" in labels:
        return "later_work"
    if "semantic_match" in labels:
        return "semantic_neighbor"
    if "related_to_seed" in labels:
        return "competing_method"
    return "semantic_neighbor"


def build_synoptic(project_dir: Path) -> dict[str, Any]:
    paths = validate_inputs(project_dir)
    seeds = load_json(paths["seed_papers"]).get("seed_papers", [])
    index = load_json(paths["literature_index"])
    papers = index.get("papers", [])
    out_dir = project_dir / "outputs" / "synopticpaper"
    out_dir.mkdir(parents=True, exist_ok=True)
    top = papers[:20]
    themes = []
    buckets: dict[str, list[dict[str, Any]]] = {}
    for paper in top:
        buckets.setdefault(classify_relation(paper), []).append(paper)
    for i, (name, group) in enumerate(buckets.items(), start=1):
        themes.append({
            "theme_id": f"theme-{i:03d}",
            "name": name.replace("_", " ").title(),
            "summary": f"{len(group)} papers grouped by relation '{name}'.",
            "supporting_papers": [p.get("paper_id") for p in group],
            "relation_to_seed": name,
        })
    gaps = [{
        "gap_id": "gap-001",
        "description": "Manual synthesis required to convert ranked related papers into domain-specific research gaps.",
        "evidence": [p.get("paper_id") for p in top[:5]],
        "confidence": "medium",
    }]
    evidence = {
        "schema_version": "readingpaper.evidence_map.v1",
        "created_by": "synopticpaper",
        "created_at": index.get("created_at"),
        "themes": themes,
        "gaps": gaps,
    }
    bibliography = paths["references"].read_text(encoding="utf-8") if paths["references"].exists() else ""
    review = build_review_markdown(seeds, papers, themes, gaps, bibliography)
    reading_plan = [
        "# Reading Plan",
        "",
        "1. Seed papers",
        *[f"- {s.get('title')}" for s in seeds[:20]],
        "",
        "2. Foundational works",
        *[f"- {p.get('title')}" for p in top if classify_relation(p) == "foundational"],
        "",
        "3. Closest related works",
        *[f"- {p.get('title')}" for p in top if classify_relation(p) in {"competing_method", "semantic_neighbor"}],
        "",
        "4. Recent follow-ups",
        *[f"- {p.get('title')}" for p in top if classify_relation(p) == "later_work"],
        "",
        "5. Evaluation/dataset papers",
        "",
        "6. Optional broader context",
        "",
    ]
    gaps_md = ["# Research Gaps", "", *[f"- {g['description']} Evidence: {', '.join(g['evidence'])}." for g in gaps], ""]
    (out_dir / "synoptic_review.md").write_text("\n".join(review), encoding="utf-8")
    write_json(out_dir / "evidence_map.json", evidence)
    (out_dir / "research_gaps.md").write_text("\n".join(gaps_md), encoding="utf-8")
    (out_dir / "reading_plan.md").write_text("\n".join(reading_plan), encoding="utf-8")
    write_finalpaper_reports(project_dir, seeds, papers, review, reading_plan, gaps)
    return evidence


def build_review_markdown(seeds: list[dict[str, Any]], papers: list[dict[str, Any]], themes: list[dict[str, Any]], gaps: list[dict[str, Any]], bibliography: str) -> list[str]:
    top = papers[:20]
    return [
        "# Synoptic Literature Review",
        "",
        "## Scope",
        f"This synthesis covers {len(seeds)} seed papers and {len(papers)} related papers from `literature_index.json`.",
        "",
        "## Seed Paper Summary",
        *[f"- {s.get('title')} ({s.get('year') or 'n.d.'})" for s in seeds],
        "",
        "## Related Literature Map",
        *[f"- {t['name']}: {t['summary']}" for t in themes],
        "",
        "## Theme 1",
        "Papers directly cited by seeds provide foundational context.",
        "",
        "## Theme 2",
        "Papers citing the seeds indicate later uptake and follow-up work.",
        "",
        "## Theme 3",
        "Semantic and related-work matches indicate adjacent methods or applications.",
        "",
        "## Methodological Comparison",
        "Use upstream summaries and downloaded PDFs to expand this section.",
        "",
        "## Dataset / Benchmark Comparison",
        "Use `paper_claims.json` and paper records to compare datasets and benchmarks.",
        "",
        "## Chronological Development",
        *[f"- {p.get('year') or 'n.d.'}: {p.get('title')}" for p in sorted(top, key=lambda p: p.get('year') or 0)[:20]],
        "",
        "## Citation and Influence Structure",
        "Relation labels distinguish foundational, later, related, and semantic-neighbor papers.",
        "",
        "## Research Gaps",
        *[f"- {g['description']} (confidence: {g['confidence']})" for g in gaps],
        "",
        "## Recommended Reading Order",
        "See `reading_plan.md`.",
        "",
        "## Bibliography",
        bibliography.strip(),
        "",
        "## Uncertainties and Manual Review Items",
        *[f"- {p.get('paper_id')}: {p.get('title')}" for p in papers if p.get("needs_review")],
        "",
    ]


def write_finalpaper_reports(project_dir: Path, seeds: list[dict[str, Any]], papers: list[dict[str, Any]], review: list[str], reading_plan: list[str], gaps: list[dict[str, Any]]) -> None:
    english = [
        "# finalpaper",
        "",
        "## Seed Papers",
        *[f"- {s.get('title')} ({s.get('year') or 'n.d.'})" for s in seeds],
        "",
        "## Related Papers",
        *[f"- {p.get('title')} ({p.get('year') or 'n.d.'}) - score {(p.get('scores') or {}).get('final', 'n/a')}" for p in papers[:30]],
        "",
        "## Integrated Review",
        *review[2:],
        "",
        "## Reading Plan",
        *reading_plan[2:],
    ]
    chinese = [
        "# finalpaper_cn",
        "",
        "## 种子论文",
        *[f"- {s.get('title')}（{s.get('year') or '年份未知'}）" for s in seeds],
        "",
        "## 相关论文",
        *[f"- {p.get('title')}（{p.get('year') or '年份未知'}）- 评分 {(p.get('scores') or {}).get('final', 'n/a')}" for p in papers[:30]],
        "",
        "## 综合综述",
        f"本报告基于 {len(seeds)} 篇种子论文和 {len(papers)} 篇相关论文生成。相关论文来自 `outputs/relevantpaper/literature_index.json`，并保留上游的不确定性和人工复核标记。",
        "",
        "## 主题结构",
        "- 被种子论文引用的文献可作为基础背景。",
        "- 引用种子论文的文献反映后续影响和延伸工作。",
        "- 语义匹配与 related works 反映邻近方法、任务或应用场景。",
        "",
        "## 研究空白",
        *[f"- {g['description']}（置信度：{g['confidence']}）" for g in gaps],
        "",
        "## 推荐阅读顺序",
        *reading_plan[2:],
        "",
        "## 不确定性与人工复核",
        *[f"- {p.get('paper_id')}: {p.get('title')}" for p in papers if p.get("needs_review")],
    ]
    out_dir = project_dir / "outputs" / "synopticpaper"
    for name, lines in [("finalpaper.md", english), ("finalpaper_cn.md", chinese)]:
        text = "\n".join(lines).strip() + "\n"
        (project_dir / name).write_text(text, encoding="utf-8")
        (out_dir / name).write_text(text, encoding="utf-8")


def run_relevantpaper(project_dir: Path, seed_path: Path, args: argparse.Namespace) -> None:
    index = project_dir / "outputs" / "relevantpaper" / "literature_index.json"
    if index.exists() and not args.force_relevantpaper:
        return
    repo_root = Path(__file__).resolve().parents[3]
    relevant_script = repo_root / "skills" / "relevantpaper" / "scripts" / "relevantpaper.py"
    cmd = [
        sys.executable,
        str(relevant_script),
        "--project-dir",
        str(project_dir),
        "--seeds",
        str(seed_path),
        "--max-candidates",
        str(args.max_candidates),
        "--max-downloads",
        str(args.max_downloads),
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"relevantpaper failed during synopticpaper orchestration: {detail}")


def run_end_to_end(project_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    seed_path = bootstrap_seed_papers_from_pdfs(project_dir)
    run_relevantpaper(project_dir, seed_path, args)
    return build_synoptic(project_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or synthesize the readingpaper workflow.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--synthesis-only", action="store_true", help="Only synthesize existing finalpaper/relevantpaper outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Create structured outputs without live relevantpaper discovery.")
    parser.add_argument("--force-relevantpaper", action="store_true", help="Re-run relevantpaper even if literature_index.json exists.")
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--max-downloads", type=int, default=40)
    args = parser.parse_args(argv)
    try:
        project_dir = Path(args.project_dir).resolve()
        if args.synthesis_only:
            build_synoptic(project_dir)
        else:
            run_end_to_end(project_dir, args)
    except Exception as exc:
        print(f"synopticpaper failed: {exc}")
        return 2
    print(f"Wrote finalpaper.md, finalpaper_cn.md, and synoptic outputs for {Path(args.project_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
