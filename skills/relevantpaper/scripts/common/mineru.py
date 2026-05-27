from __future__ import annotations

import json
import re
import shutil
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_slug(value: str, max_len: int = 80) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return (text[:max_len].strip("-") or "paper")


def relpath(path: Path, project_dir: Path) -> str:
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def unpack_mineru_zip(zip_path: Path, project_dir: Path, category: str, paper_slug: str, source_pdf: str | None = None, paper_id: str | None = None, full_zip_url: str | None = None) -> dict[str, Any]:
    mineru_dir = project_dir / "mineru" / category / paper_slug
    if mineru_dir.exists():
        shutil.rmtree(mineru_dir)
    mineru_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(mineru_dir)
    return build_parse_manifest(project_dir, mineru_dir, category, paper_slug, source_pdf, paper_id, full_zip_url, parse_status="parsed")


def locate_first(root: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        found = sorted(root.rglob(pattern))
        if found:
            return found[0]
    return None


def build_parse_manifest(project_dir: Path, mineru_dir: Path, category: str, paper_slug: str, source_pdf: str | None = None, paper_id: str | None = None, full_zip_url: str | None = None, parse_status: str = "parsed", parse_error: str | None = None, mineru_task_id: str | None = None) -> dict[str, Any]:
    full_md = locate_first(mineru_dir, ["full.md", "*.md"])
    content_list = locate_first(mineru_dir, ["*_content_list.json", "content_list.json"])
    content_list_v2 = locate_first(mineru_dir, ["*_content_list_v2.json", "content_list_v2.json"])
    middle_json = locate_first(mineru_dir, ["*_middle.json", "middle.json"])
    model_json = locate_first(mineru_dir, ["*_model.json", "model.json"])
    images_dir = locate_first(mineru_dir, ["images"])
    content_items = load_content_items(content_list_v2 or content_list)
    manifest = {
        "schema_version": "readingpaper.mineru_parse_manifest.v1",
        "paper_id": paper_id,
        "paper_slug": paper_slug,
        "source_pdf": source_pdf,
        "category": category,
        "parse_status": parse_status,
        "mineru_task_id": mineru_task_id,
        "full_zip_url": full_zip_url,
        "mineru_dir": relpath(mineru_dir, project_dir),
        "full_md": relpath(full_md, project_dir) if full_md else None,
        "content_list_json": relpath(content_list, project_dir) if content_list else None,
        "content_list_v2_json": relpath(content_list_v2, project_dir) if content_list_v2 else None,
        "middle_json": relpath(middle_json, project_dir) if middle_json else None,
        "model_json": relpath(model_json, project_dir) if model_json else None,
        "images_dir": relpath(images_dir, project_dir) if images_dir else None,
        "figure_count": count_items(content_items, {"image", "figure", "chart"}),
        "table_count": count_items(content_items, {"table"}),
        "equation_count": count_items(content_items, {"equation", "formula", "interline_equation", "inline_equation"}),
        "parse_error": parse_error,
        "created_at": utc_now(),
    }
    write_json(mineru_dir / "parse_manifest.json", manifest)
    return manifest


def load_content_items(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    data = read_json(path)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ["content", "items", "pages"]:
            if isinstance(data.get(key), list):
                if key == "pages":
                    items: list[dict[str, Any]] = []
                    for page in data[key]:
                        if isinstance(page, dict):
                            blocks = page.get("blocks") or page.get("items") or []
                            items.extend(block for block in blocks if isinstance(block, dict))
                    return items
                return [item for item in data[key] if isinstance(item, dict)]
    return []


def item_type(item: dict[str, Any]) -> str:
    return str(item.get("type") or item.get("category_type") or item.get("block_type") or item.get("text_type") or "").lower()


def count_items(items: list[dict[str, Any]], types: set[str]) -> int:
    return sum(1 for item in items if item_type(item) in types)


def item_text(item: dict[str, Any]) -> str:
    for key in ["text", "content", "md", "latex", "math_content", "table_body", "html"]:
        if item.get(key):
            return str(item[key])
    return ""


def item_caption(item: dict[str, Any]) -> str:
    caption = item.get("caption") or item.get("image_caption") or item.get("table_caption") or item.get("chart_caption")
    if isinstance(caption, list):
        return " ".join(str(v) for v in caption)
    return str(caption or "")


def normalize_image_path(value: str | None, mineru_dir: Path, project_dir: Path) -> str | None:
    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = mineru_dir / candidate
    return relpath(candidate, project_dir)


def build_reading_guide_source(project_dir: Path, mineru_dir: Path, created_by: str, paper_slug: str | None = None, paper_id: str | None = None, title: str | None = None, authors: list[Any] | None = None, year: int | None = None, doi: str | None = None, arxiv_id: str | None = None) -> dict[str, Any]:
    paper_slug = paper_slug or mineru_dir.name
    manifest_path = mineru_dir / "parse_manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else build_parse_manifest(project_dir, mineru_dir, "seed", paper_slug)
    full_md_path = project_dir / manifest["full_md"] if manifest.get("full_md") else None
    full_md = full_md_path.read_text(encoding="utf-8", errors="replace") if full_md_path and full_md_path.exists() else ""
    content_path = project_dir / (manifest.get("content_list_v2_json") or manifest.get("content_list_json") or "") if (manifest.get("content_list_v2_json") or manifest.get("content_list_json")) else None
    items = load_content_items(content_path)
    sections = extract_sections(full_md)
    figures = extract_figures(items, mineru_dir, project_dir)
    tables = extract_tables(items, mineru_dir, project_dir)
    equations = extract_equations(items, full_md)
    source = {
        "schema_version": "readingpaper.reading_guide_source.v1",
        "created_by": created_by,
        "paper_id": paper_id,
        "paper_slug": paper_slug,
        "title": title or infer_title(full_md) or paper_slug.replace("-", " ").title(),
        "authors": authors or [],
        "year": year,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "mineru": {
            "mineru_dir": manifest.get("mineru_dir"),
            "full_md": manifest.get("full_md"),
            "content_list_json": manifest.get("content_list_v2_json") or manifest.get("content_list_json"),
            "middle_json": manifest.get("middle_json"),
            "images_dir": manifest.get("images_dir"),
            "parse_manifest": relpath(manifest_path, project_dir) if manifest_path.exists() else None,
        },
        "sections": sections,
        "figures": figures,
        "tables": tables,
        "equations": equations,
        "keywords": infer_keywords(full_md),
        "claims": [],
        "limitations": [],
        "references": extract_references(full_md),
    }
    write_json(mineru_dir / "reading_guide_source.json", source)
    return source


class MinerUFullClient:
    base_url = "https://mineru.net/api/v4"

    def __init__(self, token: str, timeout: int = 60, poll_interval: int = 5, max_polls: int = 120):
        self.token = token
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Accept": "*/*"}

    def parse_pdf_to_mineru_dir(self, pdf_path: Path, project_dir: Path, category: str, paper_slug: str, paper_id: str | None = None) -> dict[str, Any]:
        payload = {
            "files": [{"name": pdf_path.name, "data_id": paper_slug, "is_ocr": False}],
            "model_version": "vlm",
            "language": "en",
            "enable_formula": True,
            "enable_table": True,
        }
        response = requests.post(f"{self.base_url}/file-urls/batch", headers={**self.headers, "Content-Type": "application/json"}, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json().get("data", response.json())
        batch_id = data.get("batch_id")
        file_urls = data.get("file_urls") or data.get("file_urls_batch") or []
        if not batch_id or not file_urls:
            raise RuntimeError("MinerU did not return batch_id and file upload URL.")
        upload_url = file_urls[0] if isinstance(file_urls[0], str) else file_urls[0].get("url")
        with pdf_path.open("rb") as fh:
            upload = requests.put(upload_url, data=fh, timeout=self.timeout)
        upload.raise_for_status()
        result = self.poll_result(batch_id)
        zip_url = result.get("full_zip_url")
        if not zip_url:
            raise RuntimeError("MinerU full parse finished without full_zip_url.")
        zip_response = requests.get(zip_url, timeout=self.timeout)
        zip_response.raise_for_status()
        tmp_zip = project_dir / ".readingpaper" / "cache" / "mineru" / f"{paper_slug}.zip"
        tmp_zip.parent.mkdir(parents=True, exist_ok=True)
        tmp_zip.write_bytes(zip_response.content)
        manifest = unpack_mineru_zip(tmp_zip, project_dir, category, paper_slug, relpath(pdf_path, project_dir), paper_id, zip_url)
        manifest["mineru_task_id"] = batch_id
        write_json(project_dir / manifest["mineru_dir"] / "parse_manifest.json", manifest)
        return manifest

    def poll_result(self, batch_id: str) -> dict[str, Any]:
        for _ in range(self.max_polls):
            response = requests.get(f"{self.base_url}/extract-results/batch/{batch_id}", headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            body = response.json()
            data = body.get("data", body)
            results = data.get("extract_result") or data.get("results") or data.get("files") or []
            if isinstance(results, dict):
                results = [results]
            result = results[0] if results else data
            state = str(result.get("state") or result.get("status") or "").lower()
            if state == "done":
                return result
            if state == "failed":
                raise RuntimeError(result.get("err_msg") or result.get("error") or "MinerU parse failed.")
            time.sleep(self.poll_interval)
        raise TimeoutError(f"Timed out waiting for MinerU batch {batch_id}.")


def infer_title(full_md: str) -> str | None:
    for line in full_md.splitlines():
        text = line.strip().strip("#").strip()
        if len(text) > 8:
            return text
    return None


def infer_keywords(full_md: str) -> list[str]:
    lowered = full_md.lower()
    candidates = ["attention", "transformer", "neural network", "dataset", "benchmark", "optimization", "representation"]
    return [term for term in candidates if term in lowered][:8]


def extract_sections(full_md: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in full_md.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if match:
            if current:
                current["text"] = current["text"].strip()
                sections.append(current)
            current = {"heading": match.group(2).strip(), "level": len(match.group(1)), "text": "", "page_start": None, "page_end": None}
        elif current is not None:
            current["text"] += line + "\n"
    if current:
        current["text"] = current["text"].strip()
        sections.append(current)
    if not sections and full_md.strip():
        sections.append({"heading": "Full Text", "level": 1, "text": full_md[:8000], "page_start": None, "page_end": None})
    return sections[:30]


def extract_figures(items: list[dict[str, Any]], mineru_dir: Path, project_dir: Path) -> list[dict[str, Any]]:
    figures = []
    for index, item in enumerate(items, start=1):
        if item_type(item) not in {"image", "figure", "chart"}:
            continue
        path = item.get("img_path") or item.get("image_path") or item.get("path")
        figures.append({
            "figure_id": f"fig{len(figures) + 1}",
            "caption": item_caption(item),
            "image_path": normalize_image_path(path, mineru_dir, project_dir),
            "page_idx": item.get("page_idx") or item.get("page"),
            "explanation": None,
        })
    return figures


def extract_tables(items: list[dict[str, Any]], mineru_dir: Path, project_dir: Path) -> list[dict[str, Any]]:
    tables = []
    for item in items:
        if item_type(item) != "table":
            continue
        path = item.get("img_path") or item.get("image_path") or item.get("path")
        tables.append({
            "table_id": f"table{len(tables) + 1}",
            "caption": item_caption(item),
            "html": item.get("table_body") or item.get("html") or item.get("text"),
            "image_path": normalize_image_path(path, mineru_dir, project_dir),
            "page_idx": item.get("page_idx") or item.get("page"),
            "explanation": None,
        })
    return tables


def extract_equations(items: list[dict[str, Any]], full_md: str) -> list[dict[str, Any]]:
    equations = []
    for item in items:
        if item_type(item) not in {"equation", "formula", "interline_equation", "inline_equation"}:
            continue
        latex = item.get("latex") or item.get("math_content") or item.get("text")
        if latex:
            equations.append({"equation_id": f"eq{len(equations) + 1}", "latex": str(latex), "page_idx": item.get("page_idx") or item.get("page"), "context": ""})
    if not equations:
        for match in re.finditer(r"\$\$(.+?)\$\$", full_md, flags=re.S):
            equations.append({"equation_id": f"eq{len(equations) + 1}", "latex": "$$" + match.group(1).strip() + "$$", "page_idx": None, "context": ""})
    return equations[:30]


def extract_references(full_md: str) -> list[str]:
    marker = re.search(r"(?im)^#+\s*(references|bibliography)\s*$", full_md)
    if not marker:
        return []
    tail = full_md[marker.end():]
    refs = [line.strip() for line in tail.splitlines() if len(line.strip()) > 20]
    return refs[:80]
