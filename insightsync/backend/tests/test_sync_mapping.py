from insightsync.backend.workflows.sync_from_sqlite import (
    _map_company,
    _map_company_mapping_audit,
    _map_intelligence_record,
    _map_parsed_document,
    _map_parsed_metric,
    _map_trigger_signal,
)


def test_map_intelligence_record_parses_json_fields() -> None:
    row = {
        "source": "hkma",
        "dataset": "rates",
        "record_key": "record-1",
        "record_type": "metric",
        "company_id": None,
        "entity": "HKG",
        "event_time": "2026-01-01",
        "title": "Rates",
        "summary": "Rate update",
        "region": "Hong Kong",
        "industry": None,
        "lang": "en",
        "evidence_url": None,
        "tags_json": '["hkma"]',
        "payload_json": '{"rate": 1.2}',
        "raw_json": None,
        "content_hash": "hash",
        "fetched_at": "2026-01-01T00:00:00Z",
        "run_id": "run-1",
    }

    mapped = _map_intelligence_record(row)

    assert mapped["tags_json"] == ["hkma"]
    assert mapped["payload_json"] == {"rate": 1.2}


def test_map_trigger_signal_parses_evidence_refs() -> None:
    row = {
        "source": "hkma",
        "dataset": "rates",
        "signal_key": "signal-1",
        "signal_type": "market",
        "company_id": None,
        "entity": "HKG",
        "event_time": "2026-01-01",
        "indicator": "usd",
        "value_num": 7.8,
        "value_text": "7.8",
        "unit": "currency",
        "signal_text": "usd: 7.8",
        "signal_score": None,
        "signal_level": None,
        "evidence_refs_json": '["hkma", "rates"]',
        "extra_json": '{"lang": "en"}',
        "row_hash": "hash",
        "fetched_at": "2026-01-01T00:00:00Z",
        "run_id": "run-1",
    }

    mapped = _map_trigger_signal(row)

    assert mapped["evidence_refs_json"] == ["hkma", "rates"]
    assert mapped["extra_json"] == {"lang": "en"}


def test_map_company_parses_profile_json_fields() -> None:
    row = {
        "source": "company_directory",
        "company_id": "hkg-alpha-fintech",
        "canonical_name": "Alpha Fintech",
        "display_name": "Alpha",
        "country": "China",
        "region": "Hong Kong",
        "city": "Hong Kong",
        "segments_json": '["fintech", "cross_border"]',
        "industries_json": '["Payments"]',
        "website_url": "https://alpha.example.com",
        "linkedin_url": "https://www.linkedin.com/company/alpha",
        "facebook_url": None,
        "x_url": None,
        "instagram_url": None,
        "wikipedia_url": None,
        "profile_summary": "Company profile",
        "description": "Seeded company",
        "extra_json": '{"seed_source": "manual"}',
        "row_hash": "hash-company",
        "updated_at": "2026-04-20T00:00:00Z",
        "run_id": "run-1",
    }

    mapped = _map_company(row)

    assert mapped["segments_json"] == ["fintech", "cross_border"]
    assert mapped["industries_json"] == ["Payments"]
    assert mapped["extra_json"] == {"seed_source": "manual"}
    assert mapped["updated_at"] is not None


def test_map_company_mapping_audit_parses_timestamp() -> None:
    row = {
        "run_id": "company-map-20260420T000000Z",
        "target_table": "intelligence_records",
        "target_row_id": 101,
        "old_company_id": None,
        "new_company_id": "hkg-alpha-fintech",
        "mapping_method": "alias_match",
        "confidence": 0.92,
        "matched_alias": "alpha fintech",
        "matched_context": "Alpha Fintech expands into UAE",
        "mapped_at": "2026-04-20T00:10:00Z",
    }

    mapped = _map_company_mapping_audit(row)

    assert mapped["target_row_id"] == 101
    assert mapped["confidence"] == 0.92
    assert mapped["mapped_at"] is not None


def test_map_parsed_document_parses_json_fields() -> None:
    row = {
        "id": 7,
        "source_table": "intelligence_records",
        "source_id": 1,
        "source_content_hash": "hash-1",
        "source_record_key": "alpha-2025",
        "source": "hkex",
        "dataset": "annual_report",
        "company_id": "alpha",
        "entity": "Alpha Holdings",
        "title": "Alpha Annual Report",
        "summary": "Annual report",
        "media_type": "application/json",
        "lang": "en",
        "file_path": None,
        "evidence_url": "https://example.com/report",
        "parser_name": "json",
        "backend_name": "native",
        "parse_version": "multisource-v2",
        "parse_status": "success",
        "ocr_status": None,
        "xbrl_status": None,
        "content_text": "Parsed text",
        "search_text": "Search text",
        "warnings_json": '["resolved path"]',
        "metadata_json": '{"ocr_status": "not_needed"}',
        "management_discussion_summary": "Summary",
        "management_discussion_highlights_json": '["highlight"]',
        "management_discussion_source_sections_json": '["Management Discussion"]',
        "section_count": 2,
        "table_count": 0,
        "metric_count": 1,
        "risk_factor_count": 1,
        "business_event_count": 1,
        "parsed_at": "2026-04-22T00:00:00Z",
        "run_id": "parse-1",
    }

    mapped = _map_parsed_document(row)

    assert mapped["warnings_json"] == ["resolved path"]
    assert mapped["metadata_json"] == {"ocr_status": "not_needed"}
    assert mapped["management_discussion_highlights_json"] == ["highlight"]
    assert mapped["parsed_at"] is not None


def test_map_parsed_metric_keeps_context() -> None:
    row = {
        "document_id": 3,
        "metric_index": 0,
        "name": "revenue",
        "value": "HK$12.5 billion",
        "unit": None,
        "period": "FY2025",
        "context": "Revenue grew to HK$12.5 billion in FY2025.",
        "confidence": 0.6,
    }

    mapped = _map_parsed_metric(row)

    assert mapped["document_id"] == 3
    assert mapped["name"] == "revenue"
    assert mapped["context"].startswith("Revenue grew")
