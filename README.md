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

### Agent Workflow

Install `readingpaper-skills` with Codex or opencode, then use the skills as agent workflows:

a. Invoke `finalpaper` to parse all PDF papers in the folder with the MinerU Precision API and generate bilingual reading guides with author backgrounds, concept explanations, and embedded figure-by-figure analysis.

b. Invoke `relevantpaper` to treat the PDF papers in the folder as seed papers, use OpenAlex API and other public academic data sources to discover, rank, and legally download related open-access papers, and generate a literature index and BibTeX.

c. Invoke `synopticpaper` to run one-click related-literature research from the PDFs already in the folder and finally generate detailed, readable `outputs/synopticpaper/finalpaper.md` and `outputs/synopticpaper/finalpaper_cn.md`.

1. Run finalpaper to create seed-only outputs such as `outputs/finalpaper/finalpaper.md` and `outputs/finalpaper/seed_papers.json`.
2. Run relevantpaper to create `literature_index.json`, `paper_digests.json`, BibTeX, download manifest, and legal OA PDFs.
3. Run synopticpaper to synthesize seed and related-paper outputs into `outputs/synopticpaper/finalpaper.md` and `outputs/synopticpaper/synoptic_review.md`.

`outputs/finalpaper/finalpaper.md` is the seed-paper reading guide. The integrated related-literature document is `outputs/synopticpaper/finalpaper.md`.

Example:

```bash
python skills/relevantpaper/scripts/relevantpaper.py --project-dir . --seeds outputs/finalpaper/seed_papers.json
python skills/synopticpaper/scripts/synopticpaper.py --project-dir .
```

## Safety policy

Only legal open-access PDFs may be downloaded.

No Sci-Hub, Library Genesis, paywall bypassing, shared credentials, cookies, or unauthorized scraping.
