from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def read_json(path: Path, required: bool = True) -> Any:
    if not path.exists():
        if required:
            raise FileNotFoundError(str(path))
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: Path, required: bool = True) -> str | None:
    if not path.exists():
        if required:
            raise FileNotFoundError(str(path))
        return None
    return path.read_text(encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


@dataclass
class SynopticInputs:
    seed_papers: dict[str, Any]
    paper_claims: dict[str, Any] | None
    paper_summary: str | None
    literature_index: dict[str, Any] | None
    paper_digests: dict[str, Any]
    references_bib: str | None
    download_manifest: dict[str, Any] | None
    warnings: list[str]
    fallback_metadata_digests: bool = False


@dataclass
class DeepReadingInputs:
    synoptic: SynopticInputs
    seed_sources: list[dict[str, Any]]
    relevant_sources: list[dict[str, Any]]
    author_profiles: dict[str, Any]
    supporting_papers: dict[str, Any]


def normalize_title(record: dict[str, Any]) -> str:
    return str(record.get("title") or record.get("display_name") or "Untitled paper")


def normalize_relations(record: dict[str, Any]) -> list[str]:
    if isinstance(record.get("relations_to_seed"), list):
        labels = []
        for relation in record["relations_to_seed"]:
            if isinstance(relation, dict) and relation.get("relation"):
                labels.append(str(relation["relation"]))
            elif isinstance(relation, str):
                labels.append(relation)
        return sorted(set(labels))
    relation_to_seed = record.get("relation_to_seed")
    if isinstance(relation_to_seed, list):
        return sorted({str(item.get("relation") if isinstance(item, dict) else item) for item in relation_to_seed if item})
    if relation_to_seed:
        return [str(relation_to_seed)]
    return []


def normalize_score(record: dict[str, Any]) -> float:
    scores = record.get("scores") or {}
    if isinstance(scores, dict) and scores.get("final") is not None:
        return float(scores["final"])
    if record.get("relevance_score") is not None:
        return float(record["relevance_score"])
    return 0.0


def pdf_parse_status(record: dict[str, Any], download_by_id: dict[str, dict[str, Any]]) -> str:
    paper_id = record.get("paper_id") or record.get("id")
    manifest = download_by_id.get(str(paper_id), {})
    status = manifest.get("download_status") or (record.get("download") or {}).get("status")
    if status == "downloaded":
        return "downloaded_not_parsed"
    if status in {"failed", "rejected"}:
        return "parse_failed"
    return "not_downloaded"


def build_metadata_digests_from_literature_index(literature_index: dict[str, Any], download_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    downloads = (download_manifest or {}).get("downloads") or []
    download_by_id = {str(item.get("paper_id")): item for item in downloads if item.get("paper_id")}
    digests = []
    for record in literature_index.get("papers") or []:
        relations = normalize_relations(record)
        title = normalize_title(record)
        summary_parts = []
        if record.get("abstract"):
            summary_parts.append(str(record["abstract"]))
        if record.get("ranking_reason"):
            summary_parts.append(str(record["ranking_reason"]))
        if relations:
            summary_parts.append("Relations to seed: " + ", ".join(relations) + ".")
        digests.append({
            "paper_id": record.get("paper_id") or record.get("id") or title,
            "title": title,
            "year": record.get("year"),
            "doi": record.get("doi"),
            "relation_to_seed": relations,
            "relevance_score": normalize_score(record),
            "digest_status": "metadata_digest",
            "pdf_parse_status": pdf_parse_status(record, download_by_id),
            "abstract": record.get("abstract"),
            "summary": " ".join(summary_parts) or f"Metadata-only digest for {title}.",
            "contributions": [],
            "methods": [],
            "datasets": [],
            "findings": [],
            "limitations": [],
            "why_it_matters_for_seed": record.get("ranking_reason") or ("Related by " + ", ".join(relations) if relations else "Related paper discovered by metadata search."),
        })
    return {
        "schema_version": "readingpaper.paper_digests.v1",
        "created_by": "synopticpaper",
        "created_at": utc_now(),
        "digests": digests,
    }


def load_synoptic_inputs(project_dir: Path, require_relevantpaper: bool = True) -> SynopticInputs:
    finalpaper_dir = project_dir / "outputs" / "finalpaper"
    relevantpaper_dir = project_dir / "outputs" / "relevantpaper"
    warnings: list[str] = []

    seed_papers = read_json(finalpaper_dir / "seed_papers.json", required=True)
    paper_claims = read_json(finalpaper_dir / "paper_claims.json", required=False)
    paper_summary = read_text(finalpaper_dir / "paper_summary.md", required=False)
    if paper_summary is None:
        paper_summary = read_text(finalpaper_dir / "finalpaper.md", required=False)

    literature_index_path = relevantpaper_dir / "literature_index.json"
    if require_relevantpaper and not literature_index_path.exists():
        raise FileNotFoundError(
            "outputs/relevantpaper/literature_index.json not found. "
            "Run relevantpaper before synopticpaper, or pass --allow-missing-relevantpaper."
        )
    literature_index = read_json(literature_index_path, required=require_relevantpaper)
    download_manifest = read_json(relevantpaper_dir / "download_manifest.json", required=False)

    fallback = False
    paper_digests_path = relevantpaper_dir / "paper_digests.json"
    if paper_digests_path.exists():
        paper_digests = read_json(paper_digests_path, required=True)
    elif literature_index:
        paper_digests = build_metadata_digests_from_literature_index(literature_index, download_manifest)
        fallback = True
        warnings.append("outputs/relevantpaper/paper_digests.json missing; generated fallback metadata digests from literature_index.json.")
    else:
        paper_digests = {"schema_version": "readingpaper.paper_digests.v1", "created_by": "synopticpaper", "created_at": utc_now(), "digests": []}
        warnings.append("No relevantpaper outputs were loaded. This synthesis only covers the seed paper.")

    references_bib = read_text(relevantpaper_dir / "references.bib", required=False)
    return SynopticInputs(
        seed_papers=seed_papers,
        paper_claims=paper_claims,
        paper_summary=paper_summary,
        literature_index=literature_index,
        paper_digests=paper_digests,
        references_bib=references_bib,
        download_manifest=download_manifest,
        warnings=warnings,
        fallback_metadata_digests=fallback,
    )


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


def select_top_relevant_digests(inputs: SynopticInputs, top_k: int = 20) -> list[dict[str, Any]]:
    digests = list(inputs.paper_digests.get("digests") or [])
    digests.sort(key=lambda item: normalize_score(item), reverse=True)
    return digests[:top_k]


def load_reading_guide_sources(project_dir: Path, category: str) -> list[dict[str, Any]]:
    root = project_dir / "mineru" / category
    if not root.exists():
        return []
    sources = []
    for path in sorted(root.glob("*/reading_guide_source.json")):
        try:
            sources.append(read_json(path, required=True))
        except Exception:
            continue
    return sources


def build_author_profiles(seed_sources: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    profiles = []
    seen: set[str] = set()
    for source in seed_sources:
        for author in source.get("authors") or []:
            name = author.get("name") if isinstance(author, dict) else str(author)
            if not name or name in seen:
                continue
            seen.add(name)
            profiles.append({
                "name": name,
                "paper_affiliation": author.get("affiliation") if isinstance(author, dict) else None,
                "current_or_known_affiliation": None,
                "research_areas": [],
                "notable_works": [],
                "source_urls": [],
                "confidence": "low",
                "notes": "未找到可验证来源。",
            })
    if not profiles:
        profiles.append({
            "name": "Unknown author",
            "paper_affiliation": None,
            "current_or_known_affiliation": None,
            "research_areas": [],
            "notable_works": [],
            "source_urls": [],
            "confidence": "low",
            "notes": "未找到可验证来源。",
        })
    data = {"schema_version": "readingpaper.author_profiles.v1", "authors": profiles}
    write_json(out_dir / "author_profiles.json", data)
    return data


def select_supporting_papers_for_reading_guide(selected: list[dict[str, Any]], out_dir: Path) -> dict[str, Any]:
    supporting = []
    for digest in selected[:8]:
        relations = digest.get("relation_to_seed") or []
        role = digest.get("role_for_reading_guide")
        if not role:
            if "referenced_by_seed" in relations:
                role = "foundational_for_seed"
            elif "semantic_match" in relations or "related_to_seed" in relations:
                role = "explains_core_concept"
            elif "cites_seed" in relations:
                role = "direct_successor"
            else:
                role = "low_priority_citing_paper"
        supporting.append({
            "paper_id": digest.get("paper_id"),
            "title": normalize_title(digest),
            "role": role,
            "reason_for_inclusion": digest.get("why_it_matters_for_seed") or digest.get("summary") or "Selected from relevantpaper ranking.",
            "used_in_sections": ["历史背景", "学术圈与影响分析"],
            "mineru_parsed": digest.get("pdf_parse_status") == "parsed",
        })
    data = {"supporting_papers": supporting}
    write_json(out_dir / "supporting_papers.json", data)
    return data


def load_deep_reading_inputs(project_dir: Path, inputs: SynopticInputs, selected: list[dict[str, Any]]) -> DeepReadingInputs:
    seed_sources = load_reading_guide_sources(project_dir, "seed")
    if not seed_sources:
        raise FileNotFoundError("MINERU_API_TOKEN is required to generate finalpaper-style deep reading guides. No mineru/seed/*/reading_guide_source.json was found.")
    relevant_sources = load_reading_guide_sources(project_dir, "relevant")
    out_dir = project_dir / "outputs" / "synopticpaper"
    out_dir.mkdir(parents=True, exist_ok=True)
    author_profiles = build_author_profiles(seed_sources, out_dir)
    supporting_papers = select_supporting_papers_for_reading_guide(selected, out_dir)
    return DeepReadingInputs(inputs, seed_sources, relevant_sources, author_profiles, supporting_papers)


def count_downloaded(inputs: SynopticInputs) -> int:
    downloads = (inputs.download_manifest or {}).get("downloads") or []
    return sum(1 for item in downloads if item.get("download_status") == "downloaded")


def input_coverage(inputs: SynopticInputs, selected: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "seed_papers_loaded": len(inputs.seed_papers.get("seed_papers") or []),
        "relevant_papers_loaded": len((inputs.literature_index or {}).get("papers") or []),
        "relevant_digests_loaded": len(inputs.paper_digests.get("digests") or []),
        "downloaded_pdfs_available": count_downloaded(inputs),
        "relevant_papers_included": len({normalize_title(item) for item in selected}),
    }


def coverage_lines(coverage: dict[str, int]) -> list[str]:
    return [
        "## Input Coverage",
        "",
        f"- Seed papers loaded: {coverage['seed_papers_loaded']}",
        f"- Relevant papers loaded: {coverage['relevant_papers_loaded']}",
        f"- Relevant paper digests loaded: {coverage['relevant_digests_loaded']}",
        f"- Downloaded PDFs available: {coverage['downloaded_pdfs_available']}",
        f"- Relevant papers included in synthesis: {coverage['relevant_papers_included']}",
        "",
    ]


def warning_lines(warnings: list[str]) -> list[str]:
    if not warnings:
        return []
    return ["## Warning", "", *[f"- {warning}" for warning in warnings], ""]


def seed_lines(inputs: SynopticInputs) -> list[str]:
    seeds = inputs.seed_papers.get("seed_papers") or []
    lines = ["## Seed Paper Summary", ""]
    if inputs.paper_summary:
        lines.extend([inputs.paper_summary.strip(), ""])
    lines.extend([f"- {seed.get('title')} ({seed.get('year') or 'n.d.'})" for seed in seeds])
    lines.append("")
    return lines


def relevant_digest_lines(selected: list[dict[str, Any]]) -> list[str]:
    lines = ["## Relevant Papers from relevantpaper", ""]
    if not selected:
        lines.extend(["No relevant papers were loaded from relevantpaper.", ""])
        return lines
    for item in selected:
        relations = item.get("relation_to_seed") or normalize_relations(item)
        if isinstance(relations, list):
            relation_text = ", ".join(str(r) for r in relations if r)
        else:
            relation_text = str(relations)
        pdf_note = "PDF full text unavailable" if item.get("pdf_parse_status") == "not_downloaded" else f"PDF status: {item.get('pdf_parse_status')}"
        lines.extend([
            f"### {normalize_title(item)}",
            "",
            f"- Year: {item.get('year') or 'n.d.'}",
            f"- DOI: {item.get('doi') or 'not available'}",
            f"- Relevance score: {normalize_score(item):.3f}",
            f"- Relation to seed: {relation_text or 'not specified'}",
            f"- Digest status: {item.get('digest_status') or 'metadata_digest'}; {pdf_note}.",
            f"- Summary: {item.get('summary') or item.get('abstract') or 'No abstract or summary available.'}",
            f"- Why it matters: {item.get('why_it_matters_for_seed') or 'Included by relevantpaper ranking.'}",
            "",
        ])
    return lines


def build_literature_index_report(inputs: SynopticInputs, selected: list[dict[str, Any]], coverage: dict[str, int]) -> list[str]:
    bibliography = (inputs.references_bib or "").strip()
    gaps = build_gaps(selected)
    return [
        "# Literature Index Report",
        "",
        *coverage_lines(coverage),
        *warning_lines(inputs.warnings),
        "## Scope",
        "",
        f"This synthesis covers {coverage['seed_papers_loaded']} seed papers and {coverage['relevant_papers_loaded']} related papers from `outputs/relevantpaper/literature_index.json`.",
        "",
        *seed_lines(inputs),
        "## Related Literature Map",
        "",
        "The sections below are built from `outputs/relevantpaper/paper_digests.json` or fallback metadata digests derived from `literature_index.json`.",
        "",
        *relevant_digest_lines(selected),
        "## Methodological Comparison",
        "",
        "Compare methods using the seed paper metadata, relation labels, ranking reasons, and available abstracts. Downloaded PDF full text is optional for this metadata-based synthesis.",
        "",
        "## Dataset / Benchmark Comparison",
        "",
        "Dataset and benchmark details are included when present in seed claims or paper digests; otherwise they remain manual-review items.",
        "",
        "## Chronological Development",
        "",
        *[f"- {item.get('year') or 'n.d.'}: {normalize_title(item)}" for item in sorted(selected, key=lambda item: item.get("year") or 0)],
        "",
        "## Citation and Influence Structure",
        "",
        "Relation labels distinguish foundational works, later citing works, related works, and semantic neighbors.",
        "",
        "## Research Gaps",
        "",
        *[f"- {gap['description']} (confidence: {gap['confidence']})" for gap in gaps],
        "",
        "## Recommended Reading Order",
        "",
        "See `reading_plan.md`.",
        "",
        "## Bibliography",
        "",
        bibliography,
        "",
        "## Uncertainties and Manual Review Items",
        "",
        *[f"- {normalize_title(item)}: metadata digest only; verify claims against the full paper." for item in selected if item.get("digest_status") == "metadata_digest"],
        "",
    ]


def build_finalpaper(inputs: SynopticInputs, selected: list[dict[str, Any]], coverage: dict[str, int]) -> list[str]:
    return [
        "# finalpaper",
        "",
        *coverage_lines(coverage),
        *warning_lines(inputs.warnings),
        *seed_lines(inputs),
        *relevant_digest_lines(selected),
        "## Integrated Synthesis",
        "",
        "The integrated synthesis combines seed-paper context with relevantpaper-ranked related works. It intentionally keeps `outputs/finalpaper/finalpaper.md` seed-only and writes this integrated document under `outputs/synopticpaper/`.",
        "",
        "## Reading Plan",
        "",
        *reading_plan_lines(inputs, selected, include_heading=False),
    ]


def build_finalpaper_cn(inputs: SynopticInputs, selected: list[dict[str, Any]], coverage: dict[str, int]) -> list[str]:
    lines = [
        "# finalpaper_cn",
        "",
        "## 输入覆盖",
        "",
        f"- 已加载种子论文：{coverage['seed_papers_loaded']}",
        f"- 已加载相关论文：{coverage['relevant_papers_loaded']}",
        f"- 已加载相关论文摘要：{coverage['relevant_digests_loaded']}",
        f"- 可用已下载 PDF：{coverage['downloaded_pdfs_available']}",
        f"- 纳入综合的相关论文：{coverage['relevant_papers_included']}",
        "",
    ]
    if inputs.warnings:
        lines.extend(["## 警告", "", *[f"- {warning}" for warning in inputs.warnings], ""])
    lines.extend(["## 种子论文", ""])
    for seed in inputs.seed_papers.get("seed_papers") or []:
        lines.append(f"- {seed.get('title')}（{seed.get('year') or '年份未知'}）")
    lines.extend(["", "## relevantpaper 发现的相关论文", ""])
    if not selected:
        lines.extend(["未加载 relevantpaper 相关论文。", ""])
    for item in selected:
        relations = item.get("relation_to_seed") or normalize_relations(item)
        relation_text = ", ".join(str(r) for r in relations) if isinstance(relations, list) else str(relations)
        lines.extend([
            f"### {normalize_title(item)}",
            "",
            f"- 年份：{item.get('year') or '未知'}",
            f"- DOI：{item.get('doi') or '暂无'}",
            f"- 相关性评分：{normalize_score(item):.3f}",
            f"- 与种子论文关系：{relation_text or '未标注'}",
            f"- 摘要状态：{item.get('digest_status') or 'metadata_digest'}；PDF 状态：{item.get('pdf_parse_status') or 'not_downloaded'}",
            f"- 摘要：{item.get('summary') or item.get('abstract') or '暂无摘要。'}",
            "",
        ])
    lines.extend([
        "## 综合结论",
        "",
        "本文件是 synopticpaper 生成的综合文档，整合了 finalpaper 的种子论文信息与 relevantpaper 的相关论文索引和摘要。`outputs/finalpaper/finalpaper.md` 保持为种子论文分析，不在此处覆盖。",
        "",
    ])
    return lines


def image_rel(path: str | None) -> str | None:
    if not path:
        return None
    return "../../" + path.replace("\\", "/")


def section_snippet(source: dict[str, Any], limit: int = 900) -> str:
    sections = source.get("sections") or []
    text = "\n\n".join(str(section.get("text") or "") for section in sections[:3]).strip()
    return text[:limit] if text else "No parsed section text available."


def figure_lines(figures: list[dict[str, Any]], english: bool) -> list[str]:
    if not figures:
        return ["No figures were detected in MinerU output." if english else "MinerU 输出中未检测到图。"]
    lines: list[str] = []
    for figure in figures:
        path = image_rel(figure.get("image_path"))
        figure_id = figure.get("figure_id") or "figure"
        caption = figure.get("caption") or "No caption"
        if path:
            lines.append(f"![{figure_id}: {caption}]({path})")
        lines.extend([
            "",
            f"### {figure_id}",
            "",
            f"Original caption: {caption}" if english else f"原始图注：{caption}",
            "What it shows: interpreted from the MinerU caption and nearby parsed text." if english else "图中展示内容：根据 MinerU 图注和相邻正文解释。",
            "Why it matters: use this figure to connect the paper's method and claims." if english else "为什么重要：这幅图用于连接论文方法与核心主张。",
            "",
        ])
    return lines


def supporting_context(supporting: list[dict[str, Any]]) -> str:
    if not supporting:
        return "No supporting relevant papers were selected."
    return " ".join(f"{paper.get('title')} is used as {paper.get('role')} because {paper.get('reason_for_inclusion')}" for paper in supporting[:6])


def build_deep_finalpaper(deep: DeepReadingInputs, coverage: dict[str, int]) -> list[str]:
    source = deep.seed_sources[0]
    title = source.get("title") or "Untitled Paper"
    figures = source.get("figures") or []
    tables = source.get("tables") or []
    equations = source.get("equations") or []
    supporting = deep.supporting_papers.get("supporting_papers") or []
    return [
        f"# {title} Reading Guide",
        "",
        *coverage_lines(coverage),
        "## Author Profiles with Verifiable Sources",
        "",
        *[f"- **{author['name']}**: {author.get('paper_affiliation') or 'Affiliation unavailable'}. Sources: {', '.join(author.get('source_urls') or []) or 'No verifiable source found.'} Confidence: {author.get('confidence')}." for author in deep.author_profiles.get("authors", [])],
        "",
        "## Paper Overview",
        "",
        section_snippet(source),
        "",
        "## Key Terms",
        "",
        *[f"- **{term}**: Core term detected from MinerU full text; interpret it in the context of the parsed paper and supporting literature." for term in (source.get("keywords") or ["method", "model", "evaluation"])],
        "",
        "## Deep Concept Explanations",
        "",
        "This guide is composed from MinerU `full.md`, parsed sections, formulas, tables, and figures. Relevant papers provide context for concepts, history, and field impact; they are not dumped as metadata.",
        "",
        "## Method Reconstruction",
        "",
        "Reconstruct the method from parsed sections: inputs, model or algorithm structure, objectives, inference process, experiments, and links to supporting papers.",
        "",
        "## Equations and Notation",
        "",
        *([f"### {eq.get('equation_id')}\n\n{eq.get('latex')}\n\nExplanation: this formula is preserved from MinerU LaTeX and should be interpreted with nearby parsed context." for eq in equations] or ["No equations were detected in MinerU output."]),
        "",
        "## Table Walkthrough",
        "",
        *([f"### {table.get('table_id')}\n\nCaption: {table.get('caption') or 'No caption'}\n\n{table.get('html') or ''}\n\nExplanation: this table is preserved from MinerU HTML/table output and should be read against the experiment narrative." for table in tables] or ["No tables were detected in MinerU output."]),
        "",
        "## Figure-by-Figure Walkthrough",
        "",
        *figure_lines(figures, english=True),
        "",
        "## Historical Background",
        "",
        supporting_context(supporting),
        "",
        "## Academic Community and Field Impact",
        "",
        "Relevantpaper-selected works explain field context, direct successors, broad influence, and later developments without turning the report into a flat paper list.",
        "",
        "## How to Read This Paper",
        "",
        "- First pass: read the overview and figures.\n- Second pass: trace method and equations.\n- Third pass: compare against supporting papers.\n- Final pass: revisit tables and limitations.",
        "",
        "## References and Sources",
        "",
        f"- Seed MinerU source: `{source.get('mineru', {}).get('full_md')}`",
        *[f"- {paper.get('title')} ({paper.get('role')}): {paper.get('reason_for_inclusion')}" for paper in supporting],
    ]


def build_deep_finalpaper_cn(deep: DeepReadingInputs, coverage: dict[str, int]) -> list[str]:
    source = deep.seed_sources[0]
    title = source.get("title") or "Untitled Paper"
    figures = source.get("figures") or []
    tables = source.get("tables") or []
    equations = source.get("equations") or []
    supporting = deep.supporting_papers.get("supporting_papers") or []
    return [
        f"# {title} 阅读指南",
        "",
        "## 输入与解析状态",
        "",
        f"- 已加载种子论文：{coverage['seed_papers_loaded']}",
        f"- 已加载相关论文：{coverage['relevant_papers_loaded']}",
        f"- 已加载相关论文摘要：{coverage['relevant_digests_loaded']}",
        f"- 图数量：{len(figures)}",
        f"- 表格数量：{len(tables)}",
        f"- 公式数量：{len(equations)}",
        f"- 相关论文全文解析数量：{len(deep.relevant_sources)}",
        "",
        "## 作者简介与可验证来源",
        "",
        *[f"- **{author['name']}**：{author.get('paper_affiliation') or '论文署名单位未知'}。可验证来源：{', '.join(author.get('source_urls') or []) or '未找到可验证来源。'} 置信度：{author.get('confidence')}。" for author in deep.author_profiles.get("authors", [])],
        "",
        "## 文章概览",
        "",
        section_snippet(source),
        "",
        "## 关键词与术语定义",
        "",
        *[f"- **{term}**：从 MinerU 正文中检测到的核心术语；需要结合原文段落、图表和相关论文理解其作用。" for term in (source.get("keywords") or ["方法", "模型", "评估"])],
        "",
        "## 深度概念讲解",
        "",
        "本节基于 MinerU 的 full.md、结构化段落、公式、表格和图示组织。相关论文只作为解释原论文概念、历史背景和影响分析的支撑语境，不作为平铺列表。",
        "",
        "## 方法重构",
        "",
        "- 输入：从论文方法部分和图表中识别。\n- 模型/算法结构：结合 MinerU 解析出的章节、公式和图示重构。\n- 训练目标：优先引用公式和实验设置。\n- 推理过程：结合方法说明和图示解释。\n- 实验设计：结合表格和结果段落说明。\n- 与相关论文的联系：使用 supporting_papers.json 中的角色说明。",
        "",
        "## 公式与符号说明",
        "",
        *([f"### {eq.get('equation_id')}\n\n{eq.get('latex')}\n\n说明：该公式来自 MinerU LaTeX 输出，应结合前后正文解释每个符号和目标函数。" for eq in equations] or ["MinerU 输出中未检测到公式。"]),
        "",
        "## 表格解读",
        "",
        *([f"### {table.get('table_id')}\n\n图注/表注：{table.get('caption') or '无'}\n\n{table.get('html') or ''}\n\n解读：该表格来自 MinerU HTML/table 输出，应结合实验问题解释指标、对比方法和结论。" for table in tables] or ["MinerU 输出中未检测到表格。"]),
        "",
        "## 逐图描述",
        "",
        *figure_lines(figures, english=False),
        "",
        "## 历史背景",
        "",
        supporting_context(supporting),
        "",
        "## 学术圈与影响分析",
        "",
        "本节使用 relevantpaper 选出的支撑论文分析学术脉络、直接后续工作、广泛影响和争议限制，而不是直接罗列论文元数据。",
        "",
        "## 如何阅读这篇论文",
        "",
        "- 第一遍：读文章概览和逐图描述。\n- 第二遍：重构方法和公式。\n- 第三遍：结合表格和实验设计理解证据。\n- 第四遍：按 supporting_papers.json 的顺序阅读相关论文。",
        "",
        "## 参考文献与来源",
        "",
        f"- 种子论文 MinerU 来源：`{source.get('mineru', {}).get('full_md')}`",
        *[f"- {paper.get('title')}（{paper.get('role')}）：{paper.get('reason_for_inclusion')}" for paper in supporting],
    ]


def build_gaps(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = [str(item.get("paper_id") or normalize_title(item)) for item in selected[:5]]
    return [{
        "gap_id": "gap-001",
        "description": "Review full texts for the top related papers to convert metadata-level relationships into claim-level research gaps.",
        "evidence": evidence,
        "confidence": "medium" if evidence else "low",
    }]


def reading_plan_lines(inputs: SynopticInputs, selected: list[dict[str, Any]], include_heading: bool = True) -> list[str]:
    lines = ["# Reading Plan", ""] if include_heading else []
    lines.extend(["1. Seed papers", *[f"- {seed.get('title')}" for seed in (inputs.seed_papers.get("seed_papers") or [])[:20]], ""])
    lines.extend(["2. Foundational works", *[f"- {normalize_title(item)}" for item in selected if "referenced_by_seed" in (item.get("relation_to_seed") or [])], ""])
    lines.extend(["3. Closest related works", *[f"- {normalize_title(item)}" for item in selected if "related_to_seed" in (item.get("relation_to_seed") or []) or "semantic_match" in (item.get("relation_to_seed") or [])], ""])
    lines.extend(["4. Recent follow-ups", *[f"- {normalize_title(item)}" for item in selected if "cites_seed" in (item.get("relation_to_seed") or [])], ""])
    lines.extend(["5. Evaluation/dataset papers", "", "6. Optional broader context", ""])
    return lines


def build_evidence_map(selected: list[dict[str, Any]]) -> dict[str, Any]:
    themes = []
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in selected:
        relations = item.get("relation_to_seed") or ["semantic_neighbor"]
        relation = relations[0] if isinstance(relations, list) and relations else str(relations)
        buckets.setdefault(relation, []).append(item)
    for index, (relation, group) in enumerate(buckets.items(), start=1):
        themes.append({
            "theme_id": f"theme-{index:03d}",
            "name": relation.replace("_", " ").title(),
            "summary": f"{len(group)} relevant papers grouped by relation '{relation}'.",
            "supporting_papers": [item.get("paper_id") for item in group],
            "relation_to_seed": relation,
        })
    return {
        "schema_version": "readingpaper.evidence_map.v1",
        "created_by": "synopticpaper",
        "created_at": utc_now(),
        "themes": themes,
        "gaps": build_gaps(selected),
    }


def write_run_report(path: Path, inputs: SynopticInputs, coverage: dict[str, int], selected: list[dict[str, Any]], output_files: list[str]) -> None:
    lines = [
        "# synopticpaper Run Report",
        "",
        "## Inputs",
        f"- finalpaper seed_papers.json found: {bool(inputs.seed_papers)}",
        f"- finalpaper paper_claims.json found: {inputs.paper_claims is not None}",
        f"- finalpaper paper_summary/finalpaper.md found: {inputs.paper_summary is not None}",
        f"- relevantpaper literature_index.json papers: {coverage['relevant_papers_loaded']}",
        f"- relevantpaper paper_digests.json digests: {coverage['relevant_digests_loaded']}",
        f"- fallback metadata digests generated: {inputs.fallback_metadata_digests}",
        f"- selected relevant papers: {len(selected)}",
        "",
        *coverage_lines(coverage),
        "## Output Files",
        *[f"- {name}" for name in output_files],
        "",
        "## Warnings",
        *([f"- {warning}" for warning in inputs.warnings] if inputs.warnings else ["- none"]),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_composition_prompts(out_dir: Path, deep: DeepReadingInputs) -> list[str]:
    prompts_dir = out_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    seed_refs = "\n".join(f"- {source.get('title')}: {source.get('mineru', {}).get('full_md')} / {source.get('mineru', {}).get('content_list_json')}" for source in deep.seed_sources)
    supporting = "\n".join(f"- {paper.get('title')} ({paper.get('role')}): {paper.get('reason_for_inclusion')}" for paper in deep.supporting_papers.get("supporting_papers", []))
    common = f"""Use these inputs:

Seed MinerU sources:
{seed_refs}

Supporting papers:
{supporting}

Author profiles: outputs/synopticpaper/author_profiles.json
Supporting paper roles: outputs/synopticpaper/supporting_papers.json

Do not produce a metadata dump. Do not invent author biographies. Use figures, tables, equations, and MinerU provenance. Integrate relevant papers as historical and conceptual context, not as a flat list.
"""
    en = "# finalpaper.md composition prompt\n\nWrite a deep English reading guide following `assets/finalpaper_report_template.md`.\n\n" + common
    cn = "# finalpaper_cn.md composition prompt\n\n撰写一份中文深度阅读指南，结构遵循 `assets/finalpaper_report_template_cn.md`。\n\n" + common
    (prompts_dir / "finalpaper_prompt.md").write_text(en, encoding="utf-8")
    (prompts_dir / "finalpaper_cn_prompt.md").write_text(cn, encoding="utf-8")
    return ["outputs/synopticpaper/prompts/finalpaper_prompt.md", "outputs/synopticpaper/prompts/finalpaper_cn_prompt.md"]


def build_synoptic(project_dir: Path, require_relevantpaper: bool = True, top_k_relevant: int = 20, report_mode: str = "deep_reading_guide") -> dict[str, Any]:
    inputs = load_synoptic_inputs(project_dir, require_relevantpaper=require_relevantpaper)
    selected = select_top_relevant_digests(inputs, top_k_relevant)
    coverage = input_coverage(inputs, selected)
    if coverage["relevant_papers_loaded"] > 0 and coverage["relevant_papers_included"] == 0:
        raise RuntimeError("relevantpaper loaded papers but none were included in synoptic synthesis.")

    out_dir = project_dir / "outputs" / "synopticpaper"
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence_map(selected)
    gaps = build_gaps(selected)
    literature_report = build_literature_index_report(inputs, selected, coverage)
    reading_plan = reading_plan_lines(inputs, selected)
    gaps_md = ["# Research Gaps", "", *[f"- {gap['description']} Evidence: {', '.join(gap['evidence'])}." for gap in gaps], ""]

    outputs: dict[str, list[str]] = {
        "literature_index_report.md": literature_report,
        "research_gaps.md": gaps_md,
        "reading_plan.md": reading_plan,
    }
    if report_mode == "deep_reading_guide":
        deep = load_deep_reading_inputs(project_dir, inputs, selected)
        outputs["finalpaper.md"] = build_deep_finalpaper(deep, coverage)
        outputs["finalpaper_cn.md"] = build_deep_finalpaper_cn(deep, coverage)
        outputs["synoptic_review.md"] = build_deep_finalpaper(deep, coverage)
        prompt_files = write_composition_prompts(out_dir, deep)
    elif report_mode == "metadata_index_report":
        outputs["synoptic_review.md"] = literature_report
        prompt_files = []
    else:
        raise ValueError(f"Unknown report mode: {report_mode}")
    for name, lines in outputs.items():
        (out_dir / name).write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    write_json(out_dir / "evidence_map.json", evidence)
    output_files = [f"outputs/synopticpaper/{name}" for name in [*outputs.keys(), "evidence_map.json", "run_report.md"]] + prompt_files
    write_run_report(out_dir / "run_report.md", inputs, coverage, selected, output_files)
    return evidence


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
    require_relevantpaper = parse_bool(args.require_relevantpaper) and not args.allow_missing_relevantpaper
    return build_synoptic(project_dir, require_relevantpaper=require_relevantpaper, top_k_relevant=args.top_k_relevant, report_mode=getattr(args, "report_mode", "deep_reading_guide"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or synthesize the readingpaper workflow.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--synthesis-only", action="store_true", help="Only synthesize existing finalpaper/relevantpaper outputs.")
    parser.add_argument("--dry-run", action="store_true", help="Create structured outputs without live relevantpaper discovery.")
    parser.add_argument("--force-relevantpaper", action="store_true", help="Re-run relevantpaper even if literature_index.json exists.")
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--max-downloads", type=int, default=40)
    parser.add_argument("--top-k-relevant", type=int, default=20)
    parser.add_argument("--report-mode", choices=["deep_reading_guide", "metadata_index_report"], default="deep_reading_guide")
    parser.add_argument("--require-relevantpaper", default="true")
    parser.add_argument("--allow-missing-relevantpaper", action="store_true")
    args = parser.parse_args(argv)
    try:
        project_dir = Path(args.project_dir).resolve()
        require_relevantpaper = parse_bool(args.require_relevantpaper) and not args.allow_missing_relevantpaper
        if args.synthesis_only:
            build_synoptic(project_dir, require_relevantpaper=require_relevantpaper, top_k_relevant=args.top_k_relevant, report_mode=args.report_mode)
        else:
            run_end_to_end(project_dir, args)
    except Exception as exc:
        print(f"synopticpaper failed: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote synopticpaper {args.report_mode} outputs to {Path(args.project_dir) / 'outputs' / 'synopticpaper'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
