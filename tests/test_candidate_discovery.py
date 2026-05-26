from common.schema import load_json
from pipeline.discover import discover_candidates

from conftest import fixture_path


class FakeClient:
    def get_referenced_works(self, work):
        return [{"id": "https://openalex.org/Wb", "title": "Backward"}]

    def get_citing_works(self, oid, per_page=80):
        return [{"id": "https://openalex.org/Wf", "title": "Forward"}]

    def get_related_works(self, oid, per_page=80):
        return [{"id": "https://openalex.org/Wr", "title": "Related"}]

    def semantic_search(self, query, filters=None, per_page=80):
        return [{"id": "https://openalex.org/Ws", "title": "Semantic"}]


def test_candidate_discovery_relation_labels():
    work = load_json(fixture_path("openalex_work.json"))
    seed = {"seed_id": "seed-001", "openalex_id": "W123456789", "_work": work, "title": "Example", "abstract": "retrieval"}
    config = {"discovery": {"include_backward": True, "include_forward": True, "include_related": True, "include_semantic": True, "max_candidates": 10, "max_per_seed": {}}}
    candidates, counts = discover_candidates([seed], FakeClient(), config)
    labels = {relation["relation"] for _, relation in candidates}
    assert labels == {"referenced_by_seed", "cites_seed", "related_to_seed", "semantic_match"}
    assert counts == {"backward": 1, "forward": 1, "related": 1, "semantic": 1}
