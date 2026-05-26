# Troubleshooting

- Missing `OPENALEX_API_KEY`: full discovery should stop unless fixture/dry-run mode is being used.
- Missing `SEMANTIC_SCHOLAR_API_KEY`: continue with public endpoints or skip augmentation.
- Missing `CROSSREF_MAILTO`: continue using the public pool.
- Download failures must be retained in `download_manifest.json`.
