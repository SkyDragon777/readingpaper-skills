from copy import deepcopy

from common.schema import load_json
from pipeline.download import download_pdfs
from pipeline.pdf_discovery import discover_pdf_url

from conftest import fixture_path


def test_arxiv_pdf_preferred_when_arxiv_id_exists():
    record = load_json(fixture_path("candidate_papers.json"))[0]
    record["arxiv_id"] = "2401.12345"
    url, source = discover_pdf_url(record)
    assert url == "https://arxiv.org/pdf/2401.12345.pdf"
    assert source == "arxiv"


def test_openalex_oa_pdf_accepted_and_non_oa_rejected():
    records = load_json(fixture_path("candidate_papers.json"))
    assert discover_pdf_url(records[0])[0] == "https://example.org/citing.pdf"
    assert discover_pdf_url(records[1]) == (None, None)


def test_failed_or_unavailable_download_recorded(tmp_path):
    record = deepcopy(load_json(fixture_path("candidate_papers.json"))[1])
    downloads = download_pdfs([record], tmp_path, max_downloads=1)
    assert downloads[0]["download_status"] == "unavailable"
    assert record["download"]["status"] == "unavailable"
