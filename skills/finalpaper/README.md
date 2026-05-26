# finalpaper — AI Agent Paper Reading Report

[中文版](README_cn.md)

An opinionated skill for AI agents: parse all PDF papers in a folder via [MinerU Precision API](https://mineru.net), then generate bilingual reading guides with author backgrounds, concept explanations, and embedded figure analysis. Each PDF must be ≤200 pages and ≤200 MB (MinerU API limits).

## Installation

```bash
# Install the skill (trigger name: finalpaper)
codex skill install --path . --name finalpaper
```

The skill root is `skills/finalpaper` in the readingpaper-skills repository. The trigger name is `finalpaper`.

## What This Project Does

1. **Parse PDFs** → MinerU cloud API extracts text, formulas (LaTeX), tables (HTML), figures, and structured metadata into `mineru/<paper-slug>/`.
2. **Generate reading guides** → The AI agent produces `finalpaper.md` (English) and `finalpaper_cn.md` (Chinese), each containing:
   - Author biographies with verified sources
   - Article overview and keyword definitions
   - In-depth concept explanations
   - Figure-by-figure descriptions with embedded images
   - Historical context and academic circle analysis
3. **Self-documenting** → `SKILL.md` serves as the onboard instruction for any compatible AI agent to continue processing additional papers without manual guidance.

## Directory Structure

```
.
├── SKILL.md                            # Agent skill instructions
├── README.md                           # This file (EN)
├── README_cn.md                        # This file (CN)
├── references/
│   ├── mineru-api.md                   # MinerU API workflow reference
│   ├── output-rules.md                 # finalpaper.md generation rules
│   ├── translation-rules.md            # Bilingual translation rules
│   └── examples/
│       ├── finalpaper.md               # Sample output (English)
│       ├── finalpaper_cn.md            # Sample output (Chinese)
│       └── image/                      # Images used only by the examples
└── .gitignore
```

Runtime MinerU outputs are generated in the user's paper directory and ignored by this repository:

```
mineru/
├── manifest.json
└── <paper-slug>/
    ├── full.md
    ├── *_content_list.json
    ├── *_content_list_v2.json
    └── images/
```

## Quick Start

### Prerequisites

- A [MinerU API token](https://mineru.net/apiManage/token). Set the `MINERU_API_TOKEN` environment variable, or let the agent ask you for it. The token is never written to files — it is only used in-memory for API calls.
- Python 3.10+ with `requests` library (or `pip install mineru-open-sdk`)
- Git (for version control)

### Processing New Papers

1. Drop PDF files into this directory.
2. Run the agent workflow described in `SKILL.md`:
   - Check `mineru/manifest.json` and skip a paper only when `status: "done"`, `full_md`, and a content-list JSON are all present
   - Upload unprocessed PDFs to MinerU Precision API:
     ```
     POST https://mineru.net/api/v4/file-urls/batch
     ```
   - PUT each PDF to the returned signed upload URL
   - Poll `GET /api/v4/extract-results/batch/{batch_id}` until done
   - Extract the result zip into `mineru/<paper-slug>/`
3. After all PDFs are parsed, generate `finalpaper.md` and `finalpaper_cn.md`.

See `SKILL.md` for complete step-by-step instructions and API token setup.

### Using the MinerU Python SDK

```python
from mineru import MinerU

client = MinerU("your-api-token")
result = client.extract("./paper.pdf", model="vlm", language="en")
result.save_all("./mineru/paper-slug/")
```

## Design Decisions

- **Bilingual output**: English for precision, Chinese for accessibility. Both files share identical structure and image references.
- **Body-only figures**: Only figures from the main paper body are included. Appendix visualizations are noted but not embedded, keeping the guide focused on core content.
- **Provenance tags**: Every claim is tagged `[FROM CAPTION]`, `[FROM TEXT]`, `[FROM TABLE]`, or `[INFERRED]` so readers can trace information back to its source.
- **Self-contained images**: Generated reports reference figures from `mineru/<slug>/images/`; bundled examples keep their display images under `references/examples/image/` so the skill repository does not need committed MinerU runtime output.


