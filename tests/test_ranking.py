from copy import deepcopy

from common.schema import load_json
from pipeline.score import rank_records, score_record

from conftest import fixture_path


def test_cites_seed_outranks_keyword_only():
    ranked = rank_records(load_json(fixture_path("candidate_papers.json")))
    assert ranked[0]["relations_to_seed"][0]["relation"] == "cites_seed"
    assert ranked[0]["scores"]["final"] > ranked[1]["scores"]["final"]


def test_retracted_paper_penalty_and_oa_bonus_written():
    record = load_json(fixture_path("candidate_papers.json"))[0]
    normal = score_record(deepcopy(record))
    retracted = deepcopy(record)
    retracted["is_retracted"] = True
    penalized = score_record(retracted)
    assert penalized["scores"]["final"] < normal["scores"]["final"]
    assert normal["scores"]["open_access"] == 1.0
    assert normal["ranking_reason"]
