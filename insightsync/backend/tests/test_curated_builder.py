import json

from insightsync.backend.services.curated_builder import CuratedProspectBuilder, infer_signal_subtype, products_for_subtypes, tier_for_score


class _RowsResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "_RowsResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class _InsertResult:
    def __init__(self, rowcount: int = 1) -> None:
        self.rowcount = rowcount


class _FakeDb:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self.statements: list[str] = []
        self.params: list[dict[str, object]] = []

    def execute(self, statement: object, params: dict[str, object] | None = None) -> object:
        self.statements.append(str(statement))
        if params is None:
            return _RowsResult(self._rows)
        self.params.append(params)
        return _InsertResult()


def test_infer_signal_subtype_for_funding_and_expansion() -> None:
    assert infer_signal_subtype("announcement", "Company announces financing plan") == "funding"
    assert infer_signal_subtype("news", "New project investment and expansion") == "expansion"


def test_score_tiers_are_stable() -> None:
    assert tier_for_score(80) == "A"
    assert tier_for_score(60) == "B"
    assert tier_for_score(40) == "C"
    assert tier_for_score(39.9) == "D"


def test_products_for_subtypes_are_deduplicated() -> None:
    products = products_for_subtypes({"cross_border", "trade"})

    assert "trade_finance" in products
    assert len(products) == len(set(products))


def test_build_scores_does_not_use_generic_evidence_for_subtype_reasons() -> None:
    db = _FakeDb(
        [
            {
                "prospect_id": "p1",
                "company_id": "c1",
                "signal_counts": {"cross_border": 1},
                "evidence_count": 1,
                "days_since_last_activity": 5,
                "evidence_refs": [{"evidence_id": "ev_unrelated", "subtype": "evidence", "title": "Generic filing"}],
            }
        ]
    )

    CuratedProspectBuilder(db).build_scores()

    reasons = json.loads(str(db.params[0]["reasons"]))
    assert reasons == []


def test_build_scores_query_links_signal_subtypes_to_evidence_ids() -> None:
    db = _FakeDb([])

    CuratedProspectBuilder(db).build_scores()

    select_sql = db.statements[0]
    assert "evidence_ids_json" in select_sql
    assert "? pei.evidence_id" in select_sql
    assert "'subtype', 'evidence'" not in select_sql


def test_backfill_company_ids_from_evidence_returns_rule_counts() -> None:
    db = _FakeDb([])

    summary = CuratedProspectBuilder(db).backfill_company_ids_from_evidence()

    assert summary == {
        "name_match_updated": 1,
        "payload_id_updated": 1,
        "eastmoney_code_updated": 1,
        "total_updated": 3,
    }
    combined_sql = "\n".join(db.statements)
    assert "payload_json->>'stock_code'" in combined_sql
    assert "canonical_name" in combined_sql
    assert "display_name" in combined_sql
    assert "regexp_match" in combined_sql
    assert "eastmoney" in combined_sql


def test_backfill_company_ids_excludes_macro_sources_for_every_rule() -> None:
    db = _FakeDb([])

    CuratedProspectBuilder(db).backfill_company_ids_from_evidence()

    backfill_statements = db.statements[:3]
    backfill_params = db.params[:3]
    assert len(backfill_statements) == 3
    for statement, params in zip(backfill_statements, backfill_params):
        assert "excluded_macro_sources" in statement
        assert "LOWER(CONCAT_WS(' ', ir.source, ir.dataset))" in statement
        assert {"censtatd", "guangdong", "hkma", "adb", "kpmg"}.issubset(set(params.values()))


def test_build_all_runs_mapping_backfill_before_prospects() -> None:
    calls: list[str] = []

    class Builder(CuratedProspectBuilder):
        def backfill_company_ids_from_evidence(self) -> dict[str, int]:
            calls.append("mapping_backfill")
            return {"total_updated": 2}

        def build_prospects(self) -> dict[str, int]:
            calls.append("prospects")
            return {"upserted": 1}

        def build_evidence_items(self) -> dict[str, int]:
            calls.append("evidence")
            return {}

        def build_signals(self) -> dict[str, int]:
            calls.append("signals")
            return {}

        def build_scores(self) -> dict[str, int]:
            calls.append("scores")
            return {}

        def build_market_snapshots(self) -> dict[str, int]:
            calls.append("market")
            return {}

        def build_quality_report(self) -> dict[str, object]:
            calls.append("quality")
            return {}

    summary = Builder(_FakeDb([])).build_all()

    assert calls[:2] == ["mapping_backfill", "prospects"]
    assert summary["mapping_backfill"] == {"total_updated": 2}
