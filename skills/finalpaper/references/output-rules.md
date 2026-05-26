# finalpaper.md Generation Rules

After all PDFs have MinerU outputs, generate exactly one `finalpaper.md` in the root folder.

## Required Sections Per Paper

1. **Authors & backgrounds** — names, affiliations, and major-author background/circle. Use external web search when needed; cite sources with URLs. Mark unverified claims as `[UNVERIFIED]`.

2. **Article overview** — executive summary, keywords with definitions, and key concepts that are necessary to understand the paper.

3. **Figure-by-figure explanations**:
   - The agent does not need to read image pixels.
   - Use `full.md`, figure captions, nearby paragraphs, and cross-references ("Figure 1", "see Fig. 2").
   - Tag every claim with one exact bracket token: `[FROM CAPTION]` = verbatim from figure caption, `[FROM TEXT]` = from body text, `[FROM TABLE]` = from table content, `[INFERRED]` = deduced from context without direct support.
   - Put section references outside the provenance tag, e.g. `[FROM TEXT]` (§3.2.1). Do not combine multiple sources inside one tag.
   - If the Markdown does not support a claim, say so instead of inventing.

## Image Embedding

**CRITICAL** — embed the actual figure images for each figure. Use relative paths from the root folder:

```markdown
![Figure 1: Description](mineru/attention-is-all-you-need/images/d018247de...jpg)
```

The images are already extracted by MinerU under `mineru/<paper-slug>/images/`. The reader needs to see them alongside the textual explanations.

## Formula Formatting

Use proper LaTeX math delimiters exactly as MinerU outputs them in `full.md`:

- Display (block) formulas: `$$ ... $$`
- Inline formulas: `$ ... $`

Do NOT convert formulas to plain Unicode/ASCII text. Keep original LaTeX for MathJax/KaTeX rendering.

## Appendix Content Filtering

Only include figures and tables from the main body (before References/Acknowledgements). Do NOT include appendix-only figures/tables unless essential. When excluded, add a brief note listing what was omitted and where the images are (e.g., `mineru/<paper-slug>/images/`).

Example: the Transformer paper has 5 figures but Figures 3–5 are appendix attention visualizations — only Figures 1–2 (architecture and attention mechanism) belong in the main body.

## Table Preservation

Preserve tables from the main body. Note their source with `[FROM TABLE]` followed by the section reference, e.g. `[FROM TABLE]` (§6.2). Explain what the table shows and why it matters.

## Provenance Tags

All substantive claims must carry a provenance tag. Use consistently:

| Tag | Meaning |
|-----|---------|
| `[FROM CAPTION]` | Exact text from the figure caption |
| `[FROM TEXT]` | From body paragraphs discussing the figure |
| `[FROM TABLE]` | From main-body table content |
| `[INFERRED]` | Deduced from context, no direct quote |
| `[UNVERIFIED]` | From external source, not yet confirmed |

Use these exact bracket tokens only. Section names, section numbers, and short source notes belong immediately after the tag in parentheses, not inside the brackets.

## Quirks

Front noise in some MinerU Markdown (e.g., text from adjacent journal articles on the same scanned page) is acceptable. Do not discard an otherwise good parse only because noise appears before the title. Title detection can be handled during summary generation.
