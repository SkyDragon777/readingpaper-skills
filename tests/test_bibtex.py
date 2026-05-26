from common.schema import load_json
from pipeline.bibtex import to_bibtex

from conftest import fixture_path


def test_bibtex_contains_all_candidate_papers():
    records = load_json(fixture_path("candidate_papers.json"))
    text = to_bibtex(records)
    assert text.count("@article") == len(records)
    assert "title = {Citing Seed Paper}" in text
    assert "doi = {10.1/keyword}" in text
