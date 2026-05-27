---
name: relevantpaper
description: Discover, rank, and legally download related academic papers from seed paper metadata, finalpaper outputs, DOI/title lists, arXiv IDs, or a working folder of PDFs. Use when the user asks to find relevant literature, citation-linked papers, semantically similar papers, open-access PDFs, BibTeX, or a structured literature index for downstream synthesis.
---

# Relevant Paper

## Purpose

Find related academic literature from seed papers, rank candidates, download legally available open-access PDFs, and produce structured outputs for synopticpaper.

## Inputs

Prefer inputs in this order:

1. `outputs/finalpaper/seed_papers.json`
2. A user-specified seed file
3. DOI / arXiv ID / title lists
4. Academic PDFs in `input/papers/`

Normalize all inputs to the shared `SeedPaperRecord` schema described in `references/io-contract.md`.

## Default workflow

1. Load and normalize seed papers.
2. Resolve seed papers to canonical IDs using DOI-first matching.
3. Query OpenAlex for references, citing works, related works, semantic matches, OA status, and PDF signals.
4. Optionally use Crossref for DOI metadata validation.
5. Optionally use Semantic Scholar for recommendation/citation augmentation.
6. Optionally use arXiv for arXiv metadata and PDF retrieval.
7. Deduplicate candidates.
8. Score and rank candidates using `references/ranking-rubric.md`.
9. Download only legally available open-access PDFs according to `references/download-policy.md`.
10. Parse selected downloaded relevant PDFs with MinerU full parsing when `MINERU_API_TOKEN` is available.
11. Write all outputs under `outputs/relevantpaper/` and MinerU parse stores under `mineru/relevant/`.

## Required outputs

- `outputs/relevantpaper/literature_index.json`
- `outputs/relevantpaper/literature_index.csv`
- `outputs/relevantpaper/candidate_papers.json`
- `outputs/relevantpaper/paper_digests.json`
- `outputs/relevantpaper/references.bib`
- `outputs/relevantpaper/download_manifest.json`
- `outputs/relevantpaper/parsed_papers.json`
- `outputs/relevantpaper/run_report.md`
- `outputs/relevantpaper/papers/`

## Backend policy

OpenAlex is the primary backend.

Semantic Scholar is optional. Missing `SEMANTIC_SCHOLAR_API_KEY` must not fail the pipeline.

Crossref is optional. Missing `CROSSREF_MAILTO` must not fail the pipeline.

arXiv is optional and should fail softly.

## Safety and access policy

Never use piracy sources, paywall bypassing, shared credentials, browser cookies, or unauthorized scraping. If a paper has no verified open-access PDF URL, keep its metadata and set `download_status: unavailable`.

## Quality rules

- Do not invent missing metadata.
- Preserve provenance for every identifier, citation relation, score, and PDF URL.
- Mark ambiguous matches as `needs_review`.
- Do not let a low-confidence title match override DOI-based metadata.
- Write a run report summarizing seed resolution, candidates, downloads, failures, and manual review items.
- Write metadata-based `paper_digests.json` for synopticpaper even when PDFs were not downloaded or parsed.
- When relevant PDFs are selected and parsed by MinerU, write `pdf_digest` entries with `mineru` references. Metadata digests are fallback/debug context only.
