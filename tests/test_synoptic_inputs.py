import json

import pytest

from synopticpaper import bootstrap_seed_papers_from_pdfs, build_synoptic, run_end_to_end
from conftest import fixture_path


def write_seed_file(project_dir):
    final_dir = project_dir / "outputs" / "finalpaper"
    final_dir.mkdir(parents=True, exist_ok=True)
    (final_dir / "seed_papers.json").write_text(fixture_path("seed_papers.json").read_text(encoding="utf-8"), encoding="utf-8")
    return final_dir


def write_literature_index(project_dir, papers):
    relevant_dir = project_dir / "outputs" / "relevantpaper"
    relevant_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "readingpaper.literature_index.v1",
        "created_by": "relevantpaper",
        "project_dir": ".",
        "created_at": "2026-05-26T00:00:00+00:00",
        "seeds": [],
        "papers": papers,
        "summary": {
            "seed_count": 1,
            "resolved_seed_count": 1,
            "candidate_count_raw": len(papers),
            "candidate_count_deduped": len(papers),
            "ranked_count": len(papers),
            "downloaded_count": 0,
            "manual_review_count": 0,
        },
        "backend_status": {},
    }
    (relevant_dir / "literature_index.json").write_text(json.dumps(data), encoding="utf-8")
    (relevant_dir / "references.bib").write_text("", encoding="utf-8")
    (relevant_dir / "download_manifest.json").write_text('{"downloads":[]}', encoding="utf-8")
    return relevant_dir


def paper(title, relation_key="relations_to_seed", relation_value=None):
    relation_value = relation_value or [{"seed_id": "seed-001", "relation": "cites_seed", "source": "openalex", "evidence": "test"}]
    return {
        "paper_id": "openalex:" + title.replace(" ", ""),
        "title": title,
        "year": 2024,
        "doi": "10.1234/" + title.replace(" ", "").lower(),
        "abstract": f"Abstract for {title}",
        "ranking_reason": f"{title} is relevant to the seed paper.",
        "scores": {"final": 0.8},
        relation_key: relation_value,
        "download": {"status": "not_attempted"},
    }


def test_synoptic_includes_relevant_titles_and_input_coverage(tmp_path):
    write_seed_file(tmp_path)
    relevant_dir = write_literature_index(tmp_path, [paper("Relevant Paper A"), paper("Relevant Paper B")])
    digests = {
        "schema_version": "readingpaper.paper_digests.v1",
        "created_by": "relevantpaper",
        "created_at": "2026-05-26T00:00:00+00:00",
        "digests": [
            {"paper_id": "openalex:A", "title": "Relevant Paper A", "year": 2024, "relation_to_seed": ["cites_seed"], "relevance_score": 0.9, "digest_status": "metadata_digest", "pdf_parse_status": "not_downloaded", "summary": "Summary A"},
            {"paper_id": "openalex:B", "title": "Relevant Paper B", "year": 2024, "relation_to_seed": ["semantic_match"], "relevance_score": 0.8, "digest_status": "metadata_digest", "pdf_parse_status": "not_downloaded", "summary": "Summary B"},
        ],
    }
    (relevant_dir / "paper_digests.json").write_text(json.dumps(digests), encoding="utf-8")
    build_synoptic(tmp_path)
    text = (tmp_path / "outputs" / "synopticpaper" / "finalpaper.md").read_text(encoding="utf-8")
    assert "Relevant Paper A" in text
    assert "Relevant Paper B" in text
    assert "## Input Coverage" in text
    assert "Relevant papers loaded: 2" in text


def test_synoptic_fallback_metadata_digests(tmp_path):
    write_seed_file(tmp_path)
    write_literature_index(tmp_path, [paper("Relevant Paper A"), paper("Relevant Paper B")])
    build_synoptic(tmp_path)
    text = (tmp_path / "outputs" / "synopticpaper" / "finalpaper.md").read_text(encoding="utf-8")
    report = (tmp_path / "outputs" / "synopticpaper" / "run_report.md").read_text(encoding="utf-8")
    assert "Relevant Paper A" in text
    assert "Relevant Paper B" in text
    assert "fallback metadata digests generated: True" in report


def test_synoptic_requires_relevantpaper_by_default(tmp_path):
    write_seed_file(tmp_path)
    with pytest.raises(FileNotFoundError, match="Run relevantpaper before synopticpaper"):
        build_synoptic(tmp_path, require_relevantpaper=True)


def test_synoptic_allow_missing_relevantpaper_writes_warning(tmp_path):
    write_seed_file(tmp_path)
    build_synoptic(tmp_path, require_relevantpaper=False)
    text = (tmp_path / "outputs" / "synopticpaper" / "finalpaper.md").read_text(encoding="utf-8")
    assert "## Warning" in text
    assert "No relevantpaper outputs were loaded" in text


def test_finalpaper_output_not_overwritten(tmp_path):
    final_dir = write_seed_file(tmp_path)
    sentinel = "SENTINEL SEED ONLY"
    (final_dir / "finalpaper.md").write_text(sentinel, encoding="utf-8")
    write_literature_index(tmp_path, [paper("Relevant Paper A")])
    build_synoptic(tmp_path)
    assert (final_dir / "finalpaper.md").read_text(encoding="utf-8") == sentinel
    assert (tmp_path / "outputs" / "synopticpaper" / "finalpaper.md").exists()


def test_schema_field_normalization_accepts_both_relation_shapes(tmp_path):
    write_seed_file(tmp_path)
    write_literature_index(tmp_path, [
        paper("Relations To Seed Paper"),
        paper("Relation To Seed Paper", relation_key="relation_to_seed", relation_value=["semantic_match"]),
    ])
    build_synoptic(tmp_path)
    text = (tmp_path / "outputs" / "synopticpaper" / "finalpaper.md").read_text(encoding="utf-8")
    assert "Relations To Seed Paper" in text
    assert "Relation To Seed Paper" in text


def test_metadata_digests_are_not_filtered_without_downloads(tmp_path):
    write_seed_file(tmp_path)
    write_literature_index(tmp_path, [paper("Undownloaded Relevant Paper")])
    build_synoptic(tmp_path)
    text = (tmp_path / "outputs" / "synopticpaper" / "finalpaper.md").read_text(encoding="utf-8")
    assert "Undownloaded Relevant Paper" in text
    assert "PDF full text unavailable" in text


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
        require_relevantpaper = "true"
        allow_missing_relevantpaper = False
        top_k_relevant = 20

    run_end_to_end(tmp_path, Args())
    assert (tmp_path / "outputs" / "finalpaper" / "seed_papers.json").exists()
    assert (tmp_path / "outputs" / "relevantpaper" / "literature_index.json").exists()
    assert (tmp_path / "outputs" / "relevantpaper" / "paper_digests.json").exists()
    assert (tmp_path / "outputs" / "synopticpaper" / "finalpaper.md").exists()
    assert (tmp_path / "outputs" / "synopticpaper" / "run_report.md").exists()
