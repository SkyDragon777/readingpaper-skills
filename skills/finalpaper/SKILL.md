---
name: finalpaper
description: Analyze user-provided academic papers or manuscript PDFs to extract seed paper metadata, research claims, methods, datasets, keywords, and structured summaries for downstream literature discovery and synthesis.
---

# finalpaper — AI Agent Paper Reading Report

Parse all PDF papers in the user's working directory with the [MinerU Precision API](https://mineru.net) and generate bilingual reading guides. Compatible with any LLM-powered agent (Codex CLI, Claude Code, Cursor, opencode, etc.).

## Directory Contract

- PDF files stay in the user's working directory (the folder containing the papers to process).
- Output files are standardized under `outputs/finalpaper/` when this skill is used as part of the readingpaper-skills suite. Preserve the existing local outputs `finalpaper.md` and `finalpaper_cn.md` when running the original MinerU workflow directly.
- All MinerU parsing outputs, zip files, and manifests stay under `mineru/` within the working directory.
- Do not create parsing outputs beside the PDFs except for `finalpaper.md` and `finalpaper_cn.md`.

```
<working-directory>/
  *.pdf
  outputs/finalpaper/
    finalpaper.md           # final output (English)
    finalpaper_cn.md        # final output (Chinese)
    seed_papers.json        # optional downstream seed metadata
  mineru/
    manifest.json           # machine-readable processed/skip list
    <paper-slug>/
      full.md
      *_content_list.json
      *_content_list_v2.json
      images/
```

## Required API Token

This skill requires a [MinerU API token](https://mineru.net/apiManage/token). Obtain the token in this order:

1. Read the `MINERU_API_TOKEN` environment variable. If it exists, use it silently.
2. If the environment variable is not set, ask the user: "I need your MinerU API token. Get one at https://mineru.net/apiManage/token, then paste it here or set the `MINERU_API_TOKEN` environment variable."
3. Do NOT write the token into any file. Do NOT echo it in logs. Use it only in `Authorization: Bearer <token>` headers to `https://mineru.net`.

## Skip Already-Processed Papers

Always consult `mineru/manifest.json` before uploading. A PDF is already processed when:

1. It appears in `mineru/manifest.json` under `processed_papers` with `status: "done"`
2. The corresponding `full_md` path exists
3. At least one `*_content_list.json` or `*_content_list_v2.json` exists in the output directory

If all three conditions are met, skip the upload. `manifest.json` is the single source of truth.

## Slug Rule

Use stable lowercase slugs for output directories: remove `.pdf`, lowercase, replace spaces and punctuation with `-`, collapse repeated `-`.

- `Attention Is All You Need.pdf` → `attention-is-all-you-need`
- `Learning representations by back-propagating errors.pdf` → `backpropagation-1986`

## Processing Order

1. List `*.pdf` files in the working directory (ignore PDFs inside `mineru/`).
2. Read `mineru/manifest.json` if it exists. For each root PDF, skip it only when all three processed-paper conditions above are true; otherwise treat it as missing or incomplete.
3. Upload only missing PDFs to MinerU Precision API → see [references/mineru-api.md](references/mineru-api.md).
4. Store all outputs under `mineru/<paper-slug>/`.
5. Update `mineru/manifest.json` after each successful parse.
6. After all PDFs are parsed, read all `mineru/*/full.md` and generate both `outputs/finalpaper/finalpaper.md` and `outputs/finalpaper/finalpaper_cn.md` → see [references/output-rules.md](references/output-rules.md) and [references/translation-rules.md](references/translation-rules.md).
7. When downstream discovery is requested, write or adapt extracted metadata to `outputs/finalpaper/seed_papers.json` using the shared `SeedPaperRecord` schema.

## Related Files

| File | Open when |
|---|---|
| [references/mineru-api.md](references/mineru-api.md) | You need the exact MinerU Precision API workflow (upload, poll, download) |
| [references/output-rules.md](references/output-rules.md) | You are generating `finalpaper.md` and need figure/table/formula rules |
| [references/translation-rules.md](references/translation-rules.md) | You are generating `finalpaper_cn.md` and need Chinese translation rules |
| [references/examples/](references/examples/) | You want to see sample outputs from running this skill on two papers |
