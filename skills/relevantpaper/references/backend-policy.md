# Backend Policy

## Primary backend

Use OpenAlex as the default backend for:
- DOI/title resolution
- Works metadata
- referenced works
- citing works
- related works
- semantic search
- open-access status
- PDF URL signals
- topics and source metadata

## Optional backends

Semantic Scholar:
- Optional augmentation backend.
- SEMANTIC_SCHOLAR_API_KEY is optional.
- If key exists, use authenticated requests.
- If key does not exist, use unauthenticated endpoints where possible.
- If an endpoint requires authentication or rate-limits, skip that step and continue.

Crossref:
- Optional DOI metadata validation backend.
- CROSSREF_MAILTO is optional but recommended.
- Missing CROSSREF_MAILTO must not fail the pipeline.

arXiv:
- Optional arXiv metadata and PDF backend.
- Prefer arXiv PDF when arXiv ID exists.

## Disallowed backends

Do not call undocumented ResearchRabbit, Litmaps, Connected Papers, Google Scholar, publisher, or institutional private endpoints.

Do not scrape pages that require authentication, institutional access, or browser sessions.

Do not use piracy sources or paywall bypass services.
