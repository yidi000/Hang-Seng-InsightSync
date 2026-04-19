from insightsync.backend.workflows.sync_from_sqlite import _map_intelligence_record, _map_trigger_signal


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
