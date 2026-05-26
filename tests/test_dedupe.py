from copy import deepcopy

from common.schema import load_json
from pipeline.dedupe import dedupe_records

from conftest import fixture_path


def test_doi_duplicates_merge_relations():
    records = load_json(fixture_path("candidate_papers.json"))
    dup = deepcopy(records[0])
    dup["paper_id"] = "openalex:W9"
    dup["openalex_id"] = "W9"
    dup["relations_to_seed"] = [{"seed_id": "seed-001", "relation": "semantic_match", "source": "openalex", "evidence": "search"}]
    merged = dedupe_records([records[0], dup])
    assert len(merged) == 1
    assert {r["relation"] for r in merged[0]["relations_to_seed"]} == {"cites_seed", "semantic_match"}


def test_openalex_id_duplicates_merge():
    records = load_json(fixture_path("candidate_papers.json"))
    dup = deepcopy(records[0])
    dup["doi"] = "10.1/other"
    merged = dedupe_records([records[0], dup])
    assert len(merged) == 1


def test_title_year_author_fuzzy_duplicate_marks_review():
    records = load_json(fixture_path("candidate_papers.json"))
    a = deepcopy(records[0])
    b = deepcopy(records[0])
    a["doi"] = b["doi"] = None
    a["openalex_id"] = b["openalex_id"] = None
    b["title"] = "Citing Seed Paper!"
    merged = dedupe_records([a, b])
    assert len(merged) == 1
    assert merged[0]["needs_review"] is True
