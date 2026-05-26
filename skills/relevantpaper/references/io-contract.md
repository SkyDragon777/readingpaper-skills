# IO Contract

`relevantpaper` reads seed metadata from `outputs/finalpaper/seed_papers.json` by default and writes every output under `outputs/relevantpaper/`.

Inputs must normalize to `readingpaper.seed_papers.v1`. Outputs use:
- `readingpaper.literature_index.v1`
- `readingpaper.download_manifest.v1`

Skills communicate only through these files. Do not invoke another skill directly.
