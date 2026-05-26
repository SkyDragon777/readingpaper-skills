from common.schema import load_json
from adapters.finalpaper_adapter import normalize_finalpaper_output

from conftest import fixture_path


def test_finalpaper_fixture_normalizes_to_seed_record():
    envelope = normalize_finalpaper_output(fixture_path("seed_papers.json"))
    assert envelope["schema_version"] == "readingpaper.seed_papers.v1"
    seed = envelope["seed_papers"][0]
    assert seed["doi"] == "10.1234/example"
    assert seed["arxiv_id"] == "2401.12345"
    assert seed["needs_review"] is False
