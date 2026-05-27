from tools.validate_final_reports import validate


def test_synoptic_not_metadata_dump_quality_gate_fails_bad_output(tmp_path):
    out = tmp_path / "outputs" / "synopticpaper"
    out.mkdir(parents=True)
    bad_cn = "\n".join([
        "# finalpaper_cn",
        "## relevantpaper 发现的相关论文",
        "- 年份：2024",
        "- DOI：10.1/x",
        "- 相关性评分：0.9",
        "- 摘要状态：metadata_digest",
        "- PDF 状态：not_downloaded",
        "- 摘要：metadata only",
    ])
    bad_en = "# finalpaper\n\nRelevant papers list only."
    (out / "finalpaper_cn.md").write_text(bad_cn, encoding="utf-8")
    (out / "finalpaper.md").write_text(bad_en, encoding="utf-8")
    errors = validate(tmp_path)
    assert errors
    assert any("metadata dump" in error or "missing" in error.lower() for error in errors)
