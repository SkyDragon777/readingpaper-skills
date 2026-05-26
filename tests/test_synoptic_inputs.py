import json
from pathlib import Path

import pytest

from synopticpaper import bootstrap_seed_papers_from_pdfs, build_synoptic, run_end_to_end, validate_inputs
from conftest import fixture_path


def test_synoptic_reads_inputs_and_writes_outputs(tmp_path):
    final_dir = tmp_path / "outputs" / "finalpaper"
    relevant_dir = tmp_path / "outputs" / "relevantpaper"
    final_dir.mkdir(parents=True)
    relevant_dir.mkdir(parents=True)
    (final_dir / "seed_papers.json").write_text(fixture_path("seed_papers.json").read_text(encoding="utf-8"), encoding="utf-8")
    (relevant_dir / "literature_index.json").write_text(fixture_path("literature_index.json").read_text(encoding="utf-8"), encoding="utf-8")
    (relevant_dir / "references.bib").write_text("", encoding="utf-8")
    (relevant_dir / "download_manifest.json").write_text('{"downloads":[]}', encoding="utf-8")
    build_synoptic(tmp_path)
    assert (tmp_path / "outputs" / "synopticpaper" / "synoptic_review.md").exists()
    assert (tmp_path / "finalpaper.md").exists()
    assert (tmp_path / "finalpaper_cn.md").exists()
    evidence = json.loads((tmp_path / "outputs" / "synopticpaper" / "evidence_map.json").read_text(encoding="utf-8"))
    assert evidence["schema_version"] == "readingpaper.evidence_map.v1"


def test_synoptic_fails_clearly_when_required_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_inputs(tmp_path)


def test_bootstrap_seed_papers_from_root_pdfs(tmp_path):
    pdf = tmp_path / "Attention Is All You Need.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    seed_path = bootstrap_seed_papers_from_pdfs(tmp_path)
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "readingpaper.seed_papers.v1"
    assert data["seed_papers"][0]["title"] == "Attention Is All You Need"
    assert data["seed_papers"][0]["needs_review"] is True


def test_end_to_end_dry_run_from_pdf_folder(tmp_path):
    pdf = tmp_path / "Example Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    class Args:
        dry_run = True
        force_relevantpaper = False
        max_candidates = 10
        max_downloads = 0

    run_end_to_end(tmp_path, Args())
    assert (tmp_path / "outputs" / "finalpaper" / "seed_papers.json").exists()
    assert (tmp_path / "outputs" / "relevantpaper" / "literature_index.json").exists()
    assert (tmp_path / "finalpaper.md").exists()
    assert (tmp_path / "finalpaper_cn.md").exists()
