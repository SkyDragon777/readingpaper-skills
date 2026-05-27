from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from adapters.finalpaper_adapter import normalize_finalpaper_output
from adapters.manual_seed_adapter import load_manual_seed_file
from clients.openalex_client import OpenAlexClient
from common.config import load_config, parse_bool
from common.schema import seed_envelope, write_json
from pipeline.dedupe import dedupe_records
from pipeline.discover import discover_candidates
from pipeline.download import download_pdfs
from pipeline.mineru_parse import parse_selected_relevant_papers_with_mineru
from pipeline.normalize import normalize_records
from pipeline.outputs import write_outputs
from pipeline.resolve import resolve_seeds
from pipeline.score import rank_records


def default_seed_path(project_dir: Path) -> Path:
    return project_dir / "outputs" / "finalpaper" / "seed_papers.json"


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


def bootstrap_seeds_from_pdfs(project_dir: Path) -> dict[str, Any]:
    pdfs = find_pdf_files(project_dir)
    if not pdfs:
        raise FileNotFoundError(f"Seed file not found: {default_seed_path(project_dir)}")
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
                "source": "relevantpaper.pdf_filename_bootstrap",
                "extracted_from": rel,
                "note": "Generated from PDF filename because no seed_papers.json was found.",
            },
        })
    return seed_envelope(seeds, "relevantpaper")


def load_seeds(project_dir: Path, seeds_path: str | None) -> dict[str, Any]:
    path = Path(seeds_path) if seeds_path else default_seed_path(project_dir)
    if not path.is_absolute():
        path = project_dir / path
    if not path.exists():
        if seeds_path is None:
            return bootstrap_seeds_from_pdfs(project_dir)
        raise FileNotFoundError(f"Seed file not found: {path}")
    if "finalpaper" in path.as_posix().lower():
        return normalize_finalpaper_output(path)
    return load_manual_seed_file(path)


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config(args.project_dir, vars(args))
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    seeds_envelope = load_seeds(config.project_dir, args.seeds)
    if seeds_envelope.get("created_by") == "relevantpaper":
        write_json(output_dir / "logs" / "pdf_seed_papers.json", seeds_envelope)
    seeds = seeds_envelope["seed_papers"]
    if not config.env.get("OPENALEX_API_KEY") and not args.dry_run:
        raise RuntimeError("OPENALEX_API_KEY is missing. Full live discovery requires OpenAlex access; use --dry-run for schema/output smoke tests.")
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    discovery_counts = {"backward": 0, "forward": 0, "related": 0, "semantic": 0}
    records: list[dict[str, Any]] = []
    downloads: list[dict[str, Any]] = []
    parsed_papers: list[dict[str, Any]] = []
    raw_count = 0
    if not args.dry_run:
        client = OpenAlexClient(config.cache_dir, api_key=config.env.get("OPENALEX_API_KEY"), timeout=int(config.data["download"].get("timeout_seconds", 30)))
        resolved, unresolved = resolve_seeds(seeds, client)
        write_json(output_dir / "logs" / "unresolved_seeds.json", unresolved)
        raw_candidates, discovery_counts = discover_candidates(resolved, client, config.data)
        raw_count = len(raw_candidates)
        records = normalize_records(raw_candidates)
        records = dedupe_records(records)
        records = rank_records(records)
        downloads = download_pdfs(
            records,
            output_dir,
            max_downloads=int(config.data["download"]["max_downloads"]),
            timeout=int(config.data["download"]["timeout_seconds"]),
            verify_pdf_header=bool(config.data["download"]["verify_pdf_header"]),
        )
        parsed_papers = parse_selected_relevant_papers_with_mineru(records, downloads, config.project_dir, config.env)
    else:
        write_json(output_dir / "logs" / "unresolved_seeds.json", [])
    downloaded_count = sum(1 for d in downloads if d.get("download_status") == "downloaded")
    summary = {
        "seed_count": len(seeds),
        "resolved_seed_count": len(resolved),
        "candidate_count_raw": raw_count,
        "candidate_count_deduped": len(records),
        "ranked_count": len(records),
        "downloaded_count": downloaded_count,
        "manual_review_count": sum(1 for r in records if r.get("needs_review")),
    }
    return write_outputs(
        output_dir,
        config.project_dir,
        resolved or seeds,
        records,
        downloads,
        summary,
        config.backend_status(),
        discovery_counts,
        unresolved,
        config.warnings,
        parsed_papers,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover, rank, and legally download related academic papers.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--seeds")
    parser.add_argument("--max-candidates", type=int)
    parser.add_argument("--max-downloads", type=int)
    parser.add_argument("--oa-only")
    parser.add_argument("--include-backward")
    parser.add_argument("--include-forward")
    parser.add_argument("--include-related")
    parser.add_argument("--include-semantic")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and write empty structured outputs without network discovery.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    for attr in ["oa_only", "include_backward", "include_forward", "include_related", "include_semantic"]:
        value = getattr(args, attr)
        if value is not None:
            setattr(args, attr, parse_bool(value))
    try:
        index = run_pipeline(args)
    except Exception as exc:
        print(f"relevantpaper failed: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {len(index.get('papers', []))} ranked papers to {Path(args.project_dir) / 'outputs' / 'relevantpaper'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
