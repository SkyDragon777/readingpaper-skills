# Bilingual Translation Rules

Alongside the English `finalpaper.md`, generate a Chinese version `finalpaper_cn.md` in the same directory.

## What to Translate

Translate all of the following to natural Chinese (简体中文):

- Explanatory text and analysis paragraphs
- Concept explanations and article overviews
- Author background descriptions
- The Processing Metadata section at the bottom

## What NOT to Translate

Keep UNCHANGED:

- Paper titles
- Author names
- Institution names
- Figure captions (original English)
- ALL mathematical formulas (`$$...$$` and `$...$`)
- Image markdown syntax (`![...](...)`)
- Table markdown
- Citation markers like `(§3.2.1)`
- Provenance tags: `[FROM CAPTION]`, `[FROM TEXT]`, `[FROM TABLE]`, `[INFERRED]`, `[UNVERIFIED]`
- URLs and links
- Code blocks and technical identifiers

## Table Headers

Translate `### Author Information` table headers:
- `Author` → `作者`
- `Affiliation (at publication)` → `所属机构（发表时）`
- `Background & Academic Circle` → `背景与学术圈`

## Technical Terms

On first occurrence, use the form "自注意力（Self-Attention）" — Chinese term first, English in parentheses.

## Structure

Maintain EXACT same section structure (`##`, `###`, `####` headers), same image paths, and same formula blocks. Only the narrative text between these elements changes language.
