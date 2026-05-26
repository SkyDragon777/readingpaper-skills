from common.schema import load_json
from pipeline.resolve import resolve_seeds

from conftest import fixture_path


class FakeOpenAlex:
    def __init__(self, work, title_results=None):
        self.work = work
        self.title_results = title_results if title_results is not None else [work]

    def get_work_by_doi(self, doi):
        return self.work if doi == "10.1234/example" else None

    def search_works_by_title(self, title, per_page=5):
        return self.title_results


def test_doi_exact_match_wins():
    seed = load_json(fixture_path("seed_papers.json"))["seed_papers"][0]
    work = load_json(fixture_path("openalex_work.json"))
    resolved, unresolved = resolve_seeds([seed], FakeOpenAlex(work))
    assert not unresolved
    assert resolved[0]["openalex_id"] == "W123456789"
    assert resolved[0]["resolution"]["confidence"] == 1.0


def test_title_fallback_marks_medium_confidence_needs_review():
    seed = {"seed_id": "seed-002", "title": "Example Paper", "authors": ["Alice Smith"], "year": 2024}
    work = load_json(fixture_path("openalex_work.json"))
    resolved, unresolved = resolve_seeds([seed], FakeOpenAlex(work))
    assert not unresolved
    assert resolved[0]["needs_review"] is True
    assert 0.65 <= resolved[0]["resolution"]["confidence"] < 0.85


def test_unresolved_seed_is_returned():
    seed = {"seed_id": "seed-003", "title": "No Match", "authors": [], "year": 1999}
    resolved, unresolved = resolve_seeds([seed], FakeOpenAlex(None, []))
    assert not resolved
    assert unresolved[0]["needs_review"] is True
