# MinerU Precision API Workflow

Use the official cloud API (`https://mineru.net/api/v4`), not local `magic-pdf` CLI and not the lightweight Agent API.

## 1. Request Signed Upload URLs

```text
POST https://mineru.net/api/v4/file-urls/batch
```

Headers:

```text
Authorization: Bearer <MINERU_API_TOKEN>
Content-Type: application/json
Accept: */*
```

Request body for English academic PDFs:

```json
{
  "files": [
    {
      "name": "example.pdf",
      "data_id": "example-slug",
      "is_ocr": false
    }
  ],
  "model_version": "vlm",
  "language": "en",
  "enable_formula": true,
  "enable_table": true
}
```

- `model_version: "vlm"` — recommended for academic papers with formulas and complex layouts.
- `language: "en"` — for English papers.
- `is_ocr: true` — for scanned or old PDFs.
- Single request supports up to 50 files. Batches of 10–20 are safer.

## 2. Upload Each Local File

The response contains `data.batch_id` and `data.file_urls`.

```text
PUT <file_urls[i]>
```

Body: raw PDF bytes. Do not set a custom `Content-Type` header. After upload, MinerU automatically starts parsing — no separate submit endpoint.

## 3. Poll Batch Results

```text
GET https://mineru.net/api/v4/extract-results/batch/{batch_id}
```

States: `waiting-file` → `pending` → `running` → `converting` → `done` | `failed`.

When `state == "done"`, read `full_zip_url`. When `state == "failed"`, record `err_msg` and do not retry silently.

## 4. Download and Unpack

Download `full_zip_url` and extract into `mineru/<paper-slug>/`. Keep at least:

- `full.md`
- `*_content_list.json`
- `*_content_list_v2.json`
- `*_model.json`
- `layout.json`
- `images/`

Then update `mineru/manifest.json` so future runs skip the processed PDF.

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `A0202` | Invalid token | Check `Bearer` prefix or refresh token |
| `A0211` | Token expired | Get new token at mineru.net |
| `-60005` | File >200MB | Compress or split PDF |
| `-60006` | Page limit exceeded (>200) | Split file or use `page_ranges` |
| `-60007` | Model unavailable | Retry with exponential backoff |
| `-60010` | Parse failed | Re-submit; check PDF not corrupt |
| `-60018` | Daily task limit | Wait until next day |
