from insightsync.backend.services.company_mapping_quality import (
    canonical_company_token,
    extract_company_id_from_payload,
    is_company_mappable_source,
    mapping_coverage,
)


def test_extract_company_id_from_payload_prefers_stock_code() -> None:
    payload = {"stock_code": " 002129 ", "name": "TCL Zhonghuan"}

    assert extract_company_id_from_payload(payload) == "002129"


def test_canonical_company_token_normalizes_names() -> None:
    assert canonical_company_token(" TCL中环股份有限公司 ") == "tcl中环股份有限公司"


def test_mapping_coverage_handles_empty_total() -> None:
    assert mapping_coverage(mapped=0, total=0) == 0.0
    assert mapping_coverage(mapped=60, total=100) == 0.6


def test_is_company_mappable_source_excludes_macro_sources() -> None:
    assert not is_company_mappable_source("censtatd", "retail_sales")
    assert not is_company_mappable_source("guangdong_stats", "table_rows")
    assert not is_company_mappable_source("hkma", "press_releases_en")
    assert not is_company_mappable_source("adb_kidb", "unemployment_rate")
    assert not is_company_mappable_source("kpmg", "hong_kong_banking_outlook_pdf")


def test_is_company_mappable_source_keeps_company_sources() -> None:
    assert is_company_mappable_source("dongfang_eastmoney", "holdings_rank_rows")
    assert is_company_mappable_source("investhk_news", "news_items")
    assert is_company_mappable_source("szse_cninfo", "announcements")
