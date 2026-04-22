from pathlib import Path

from insightsync.backend.services.rag_document_builder import RagDocumentBuilder
from insightsync.parsing import ParseRequest, parse_content


def test_json_parser_extracts_metrics_risks_events_and_management_discussion() -> None:
    payload = {
        "management_discussion": (
            "Management discussion and analysis. Revenue grew to HK$12.5 billion in FY2025. "
            "Management discussed expansion into Shenzhen and highlighted regulatory risk from new capital rules."
        ),
        "financial_highlights": [
            {"revenue": "HK$12.5 billion", "net profit": "HK$2.1 billion"},
        ],
        "event_note": "On 2026-04-01 the group signed a strategic partnership agreement with a payments company.",
    }

    parsed = parse_content(
        ParseRequest(
            source_name="hkex",
            dataset="annual_report",
            title="Alpha Holdings Annual Report",
            content=payload,
        )
    )

    assert parsed.parser_name == "json"
    assert parsed.management_discussion is not None
    assert any(metric.name.lower() == "revenue" for metric in parsed.metrics)
    assert any(risk.category == "regulatory" for risk in parsed.risk_factors)
    assert any(event.event_type == "partnership" for event in parsed.business_events)


def test_html_parser_extracts_sections_tables_and_structured_items() -> None:
    html = """
    <html>
      <head><title>Market Signal</title></head>
      <body>
        <main>
          <h1>Market Signal</h1>
          <h2>Management Discussion</h2>
          <p>Revenue reached HK$5 billion in FY2025.</p>
          <p>On 2026-04-01 the company signed a partnership agreement in Shenzhen.</p>
          <h2>Risk Factors</h2>
          <p>Regulatory risk increased significantly because of new capital requirements.</p>
          <table>
            <caption>Financial highlights</caption>
            <tr><th>revenue</th><th>net profit</th></tr>
            <tr><td>HK$5 billion</td><td>HK$1 billion</td></tr>
          </table>
        </main>
      </body>
    </html>
    """

    parsed = parse_content(
        ParseRequest(
            source_name="crawler",
            dataset="news_article",
            title="Market Signal",
            content=html,
        )
    )

    assert parsed.parser_name == "html"
    assert len(parsed.sections) >= 2
    assert len(parsed.tables) == 1
    assert any(metric.name.lower() == "revenue" for metric in parsed.metrics)
    assert any(risk.category == "regulatory" for risk in parsed.risk_factors)
    assert any(event.event_type == "partnership" for event in parsed.business_events)


def test_document_parser_handles_text_file() -> None:
    report_path = Path("insightsync/backend/tests/fixtures/sample_report.txt").resolve()

    parsed = parse_content(
        ParseRequest(
            source_name="local",
            dataset="report_text",
            title="Annual Report Draft",
            file_path=str(report_path),
            media_type="text/plain",
        )
    )

    assert parsed.parser_name == "document"
    assert parsed.source_kind == "document"
    assert parsed.management_discussion is not None
    assert any(metric.name.lower() == "revenue" for metric in parsed.metrics)
    assert any(risk.category == "regulatory" for risk in parsed.risk_factors)


def test_metric_extraction_prefers_actual_value_over_punctuation_or_growth_rate() -> None:
    parsed = parse_content(
        ParseRequest(
            source_name="news",
            dataset="market_update",
            title="Retail sales update",
            content=(
                "Retail sales in February, provisionally estimated at $35 billion, "
                "were up 19.3% compared with the same month a year earlier."
            ),
        )
    )

    revenue_metrics = [metric for metric in parsed.metrics if metric.name == "revenue"]
    assert revenue_metrics
    assert revenue_metrics[0].value == "$35 billion"
    assert all(metric.value not in {",", "19.3%"} for metric in revenue_metrics)


def test_risk_extraction_skips_neutral_interest_rate_snapshot() -> None:
    parsed = parse_content(
        ParseRequest(
            source_name="hkma",
            dataset="composite_interest_rate_monthly",
            title="Composite interest rate",
            content="end of month\n2026-02\n\ninterest rate\n1.31",
        )
    )

    assert parsed.risk_factors == []


def test_business_event_extraction_skips_legal_partnership_boilerplate() -> None:
    parsed = parse_content(
        ParseRequest(
            source_name="kpmg",
            dataset="banking_outlook",
            title="Banking outlook",
            content=(
                "Hong Kong Banking Outlook 2026. "
                "© 2026 KPMG, a Hong Kong (SAR) partnership and a member firm of the KPMG global organisation."
            ),
        )
    )

    assert parsed.business_events == []


def test_document_parser_csv_uses_real_header_row_and_row_label_metrics() -> None:
    tmp_dir = Path(".tmp_parsing_quality").resolve()
    tmp_dir.mkdir(parents=True, exist_ok=True)
    csv_path = tmp_dir / "guangdong_table.csv"
    csv_path.write_text(
        "0,1,2\n"
        "指标,1-2月,增长%\n"
        "中外资银行业机构本外币存款余额（亿元）,398046.34,7.8\n",
        encoding="utf-8",
    )

    parsed = parse_content(
        ParseRequest(
            source_name="guangdong_stats",
            dataset="tables_csv",
            title="广东统计表",
            file_path=str(csv_path),
            media_type="text/csv",
        )
    )

    assert parsed.tables
    assert parsed.tables[0].headers == ["指标", "1-2月", "增长%"]
    assert any(metric.name == "customer deposits" and metric.value == "398046.34" for metric in parsed.metrics)


def test_rag_document_builder_uses_parsed_output() -> None:
    builder = RagDocumentBuilder(db=None)  # type: ignore[arg-type]
    row = {
        "source_table": "intelligence_records",
        "source_id": 1,
        "source": "hkex",
        "dataset": "annual_report",
        "record_key": "alpha-2025",
        "signal_key": None,
        "entity": "Alpha Holdings",
        "company_id": "alpha",
        "event_time": "2026-04-01",
        "record_type": "document",
        "signal_type": None,
        "region": "Hong Kong",
        "industry": "Financials",
        "lang": "en",
        "evidence_url": "https://example.com/report",
        "title": "Alpha Holdings Annual Report",
        "summary": "Annual report summary",
        "payload_json": {
            "management_discussion": (
                "Management discussion and analysis. Revenue grew to HK$12.5 billion in FY2025. "
                "The company signed a partnership agreement in Shenzhen on 2026-04-01."
            ),
            "risk_note": "Regulatory risk increased because of capital rules.",
        },
        "signal_text": None,
    }

    document = builder._row_to_document(row)

    assert "Parsed text:" in document["content"]
    assert "Management discussion summary:" in document["content"]
    assert "Business events:" in document["content"]
    assert document["metadata_json"]["parse"]["parser_name"] == "json"
