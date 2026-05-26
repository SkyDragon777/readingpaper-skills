import json

from common.schema import load_json
from pipeline.outputs import write_outputs

from conftest import fixture_path


def test_relevantpaper_writes_paper_digests(tmp_path):
    records = load_json(fixture_path("candidate_papers.json"))
    summary = {
        "seed_count": 1,
        "resolved_seed_count": 1,
        "candidate_count_raw": 2,
        "candidate_count_deduped": 2,
        "ranked_count": 2,
        "downloaded_count": 0,
        "manual_review_count": 0,
    }
    write_outputs(
        tmp_path / "outputs" / "relevantpaper",
        tmp_path,
        [],
        records,
        [],
        summary,
        {},
        {"backward": 0, "forward": 0, "related": 0, "semantic": 0},
        [],
        [],
    )
    path = tmp_path / "outputs" / "relevantpaper" / "paper_digests.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "readingpaper.paper_digests.v1"
    assert len(data["digests"]) == 2
    assert all(item["title"] for item in data["digests"])
    assert all(item["summary"] or item["abstract"] for item in data["digests"])
