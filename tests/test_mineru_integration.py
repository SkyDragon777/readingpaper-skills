import json
import zipfile
from pathlib import Path

from common.mineru import build_reading_guide_source, unpack_mineru_zip
from pipeline.mineru_parse import parse_selected_relevant_papers_with_mineru


def make_mineru_zip(path: Path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("full.md", "# Example Paper\n\nIntroduction text.\n\n$$y=Wx$$")
        zf.writestr(
            "content_list.json",
            json.dumps([
                {"type": "text", "text": "Introduction text."},
                {"type": "image", "img_path": "images/fig1.png", "image_caption": ["Architecture overview"], "page_idx": 1},
                {"type": "table", "table_body": "<table><tr><td>A</td></tr></table>", "table_caption": ["Results"], "page_idx": 2},
                {"type": "equation", "latex": "$$y=Wx$$", "page_idx": 3},
            ]),
        )
        zf.writestr("middle.json", "{}")
        zf.writestr("model.json", "{}")
        zf.writestr("images/fig1.png", b"fake-png")


def test_mineru_full_zip_is_unpacked(tmp_path):
    zip_path = tmp_path / "mineru.zip"
    make_mineru_zip(zip_path)
    manifest = unpack_mineru_zip(zip_path, tmp_path, "seed", "example-paper", "input.pdf", "seed-001")
    mineru_dir = tmp_path / manifest["mineru_dir"]
    assert (mineru_dir / "full.md").exists()
    assert (mineru_dir / "content_list.json").exists()
    assert (mineru_dir / "middle.json").exists()
    assert (mineru_dir / "images").exists()
    assert (mineru_dir / "parse_manifest.json").exists()
    assert manifest["figure_count"] == 1
    assert manifest["table_count"] == 1
    assert manifest["equation_count"] == 1


def test_seed_reading_guide_source_created(tmp_path):
    zip_path = tmp_path / "mineru.zip"
    make_mineru_zip(zip_path)
    unpack_mineru_zip(zip_path, tmp_path, "seed", "example-paper", "input.pdf", "seed-001")
    source = build_reading_guide_source(tmp_path, tmp_path / "mineru" / "seed" / "example-paper", "finalpaper", "example-paper", "seed-001")
    assert source["sections"]
    assert source["figures"]
    assert source["tables"]
    assert source["equations"]
    assert (tmp_path / "mineru" / "seed" / "example-paper" / "reading_guide_source.json").exists()


def test_relevantpaper_parses_selected_downloads_with_mineru(monkeypatch, tmp_path):
    pdf = tmp_path / "outputs" / "relevantpaper" / "papers" / "paper.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4")
    zip_path = tmp_path / "mineru.zip"
    make_mineru_zip(zip_path)

    class FakeClient:
        def __init__(self, token):
            self.token = token

        def parse_pdf_to_mineru_dir(self, pdf_path, project_dir, category, paper_slug, paper_id=None):
            return unpack_mineru_zip(zip_path, project_dir, category, paper_slug, str(pdf_path), paper_id)

    monkeypatch.setattr("pipeline.mineru_parse.MinerUFullClient", FakeClient)
    records = [{"paper_id": "openalex:W1", "title": "Relevant Paper", "year": 2024, "authors": [], "doi": "10.1/x"}]
    downloads = [{"paper_id": "openalex:W1", "title": "Relevant Paper", "download_status": "downloaded", "file": str(pdf.relative_to(tmp_path))}]
    parsed = parse_selected_relevant_papers_with_mineru(records, downloads, tmp_path, {"MINERU_API_TOKEN": "token", "RELEVANTPAPER_MAX_MINERU_PARSE": "1"})
    assert parsed[0]["parse_status"] == "parsed"
    assert (tmp_path / "mineru" / "relevant").exists()
    assert downloads[0]["parse_status"] == "parsed"
