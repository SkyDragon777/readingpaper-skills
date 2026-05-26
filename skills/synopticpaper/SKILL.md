---
name: synopticpaper
description: Run the end-to-end readingpaper workflow from a folder of PDFs or existing finalpaper/relevantpaper outputs, using file-based handoffs to produce integrated outputs/synopticpaper/finalpaper.md, finalpaper_cn.md, a structured literature review, evidence map, research gap analysis, and reading plan.
---

# Synoptic Paper

## Purpose

Synthesize outputs from finalpaper and relevantpaper into a coherent scholarly review. When used in a folder that only contains PDFs, act as the top-level file-based orchestrator:

1. Find PDFs in the current folder or `input/papers/`.
2. Create `outputs/finalpaper/seed_papers.json` if it is missing.
3. Run the relevantpaper script with that seed file to create `outputs/relevantpaper/`.
4. Synthesize those files into `outputs/synopticpaper/`.
5. Write integrated `outputs/synopticpaper/finalpaper.md` and `outputs/synopticpaper/finalpaper_cn.md`.

This is script/file orchestration, not direct Skill-to-Skill invocation.

## Inputs

Read, when available:

- `outputs/finalpaper/seed_papers.json`
- `outputs/finalpaper/paper_claims.json`
- `outputs/finalpaper/paper_summary.md`
- `outputs/relevantpaper/literature_index.json`
- `outputs/relevantpaper/paper_digests.json`
- `outputs/relevantpaper/references.bib`
- `outputs/relevantpaper/download_manifest.json`

## Outputs

Write:

- `outputs/synopticpaper/finalpaper.md`
- `outputs/synopticpaper/finalpaper_cn.md`
- `outputs/synopticpaper/synoptic_review.md`
- `outputs/synopticpaper/evidence_map.json`
- `outputs/synopticpaper/research_gaps.md`
- `outputs/synopticpaper/reading_plan.md`
- `outputs/synopticpaper/run_report.md`

## Rules

- For one-folder PDF workflows, call `skills/relevantpaper/scripts/relevantpaper.py` to perform external search/download through file-based schemas.
- For synthesis-only workflows, do not perform external search or download PDFs.
- Use `literature_index.json` as the authoritative related-paper input.
- Use `paper_digests.json` when present; otherwise build fallback metadata digests from `literature_index.json`.
- Do not overwrite `outputs/finalpaper/finalpaper.md`.
- Preserve uncertainty and manual_review flags.
- Distinguish seed papers, foundational works, later works, related works, and semantic matches.
- Cite papers using DOI, title, year, and BibTeX key where possible.
- Include unresolved or ambiguous metadata in an Uncertainties section.

## CLI

Default end-to-end folder workflow:

```bash
python skills/synopticpaper/scripts/synopticpaper.py --project-dir .
```

Synthesis only, requiring existing `outputs/finalpaper/seed_papers.json` and `outputs/relevantpaper/literature_index.json`:

```bash
python skills/synopticpaper/scripts/synopticpaper.py --project-dir . --synthesis-only
```

By default `synopticpaper` requires `outputs/relevantpaper/literature_index.json`. Pass `--allow-missing-relevantpaper` only when you intentionally want seed-only output with a warning.

`synoptic_review.md` structure:

# Synoptic Literature Review

## Scope
## Seed Paper Summary
## Related Literature Map
## Theme 1
## Theme 2
## Theme 3
## Methodological Comparison
## Dataset / Benchmark Comparison
## Chronological Development
## Citation and Influence Structure
## Research Gaps
## Recommended Reading Order
## Bibliography
## Uncertainties and Manual Review Items
