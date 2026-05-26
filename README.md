# readingpaper-skills

[中文](README_cn.md) | English

A suite of Agent Skills for reading academic papers, discovering related literature, downloading legal open-access PDFs, and synthesizing literature reviews.

## Skills

- finalpaper: analyze seed/final papers and extract structured claims and metadata.
- relevantpaper: discover, rank, and legally download related papers.
- synopticpaper: synthesize finalpaper and relevantpaper outputs into a literature review.

## Installation / development

Use Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Environment variables

| Variable | Required? | Used by | Behavior if missing |
|---|---:|---|---|
| OPENALEX_API_KEY | Recommended / expected | OpenAlex | Warn; limited/dry-run only for full discovery |
| SEMANTIC_SCHOLAR_API_KEY | No | Semantic Scholar | Use unauthenticated endpoints where possible; skip auth-only/rate-limited steps |
| CROSSREF_MAILTO | No, recommended | Crossref | Use public pool; recommend polite pool |
| CROSSREF_PLUS_API_TOKEN | No | Crossref Metadata Plus | Skip plus pool |
| RELEVANTPAPER_MAX_CANDIDATES | No | relevantpaper | Default 200 |
| RELEVANTPAPER_MAX_DOWNLOADS | No | relevantpaper | Default 40 |

## Typical workflow

1. Run finalpaper to create `outputs/finalpaper/seed_papers.json`.
2. Run relevantpaper to create the literature index, BibTeX, download manifest, and legal OA PDFs.
3. Run synopticpaper to synthesize the seed and related-paper outputs.

Example:

```bash
python skills/relevantpaper/scripts/relevantpaper.py --project-dir . --seeds outputs/finalpaper/seed_papers.json
python skills/synopticpaper/scripts/synopticpaper.py --project-dir .
```

## Safety policy

Only legal open-access PDFs may be downloaded.

No Sci-Hub, Library Genesis, paywall bypassing, shared credentials, cookies, or unauthorized scraping.
