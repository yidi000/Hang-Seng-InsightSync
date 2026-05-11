from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from insightsync.backend.db.session import get_db
from insightsync.backend.main import app


def _seed_test_db(db: Session) -> None:
    db.execute(
        text(
            """
            INSERT INTO companies (
              id, source, company_id, canonical_name, display_name, country, region, city,
              segments_json, industries_json, website_url, linkedin_url, facebook_url, x_url,
              instagram_url, wikipedia_url, profile_summary, description, extra_json, updated_at
            )
            VALUES
              (
                1, 'company_directory', 'hkg-alpha-fintech', 'Alpha Fintech', 'Alpha Fintech',
                'China', 'Hong Kong', 'Hong Kong',
                :alpha_segments, :alpha_industries, 'https://alpha.example.com', NULL, NULL, NULL,
                NULL, NULL, 'Older summary', 'Older description', :alpha_extra_old, '2026-04-10T09:00:00Z'
              ),
              (
                2, 'company_directory', 'hkg-alpha-fintech', 'Alpha Fintech', 'Alpha Fintech Holdings',
                'China', 'Hong Kong', 'Hong Kong',
                :alpha_segments, :alpha_industries, 'https://alpha.example.com', 'https://linkedin.com/company/alpha',
                NULL, NULL, NULL, NULL, 'Latest summary', 'Latest description', :alpha_extra_new,
                '2026-04-20T09:00:00Z'
              ),
              (
                3, 'company_mapper', '0005', 'HSBC Holdings', 'HSBC Holdings',
                'China', 'Hong Kong', 'Hong Kong',
                :hsbc_segments, :hsbc_industries, NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, 'Listed issuer', :hsbc_extra, '2026-04-21T08:00:00Z'
              )
            """
        ),
        {
            "alpha_segments": json.dumps(["fintech", "sme"], ensure_ascii=False),
            "alpha_industries": json.dumps(["Payments"], ensure_ascii=False),
            "alpha_extra_old": json.dumps({"seed_source": "manual_seed_v1"}, ensure_ascii=False),
            "alpha_extra_new": json.dumps({"seed_source": "manual_seed_v2"}, ensure_ascii=False),
            "hsbc_segments": json.dumps(["listed_company", "hkex"], ensure_ascii=False),
            "hsbc_industries": json.dumps(["Banking"], ensure_ascii=False),
            "hsbc_extra": json.dumps({"discovered_from": "hkex_disclosure"}, ensure_ascii=False),
        },
    )
    db.execute(
        text(
            """
            INSERT INTO trigger_signals (
              id, source, dataset, signal_key, signal_type, company_id, entity, event_time,
              indicator, value_num, value_text, unit, signal_text, signal_score, signal_level,
              evidence_refs_json, extra_json
            )
            VALUES
              (
                11, 'investhk_news', 'news_signals', 'signal-alpha-growth', 'growth',
                'hkg-alpha-fintech', 'HKG', '2026-04-22T10:00:00Z',
                'headline', NULL, NULL, NULL, 'Alpha Fintech expands into UAE', NULL, NULL,
                :alpha_signal_refs, :alpha_signal_extra
              ),
              (
                12, 'hk_gov_news', 'finance_news_signals', 'signal-alpha-cross-border', 'cross_border',
                'hkg-alpha-fintech', 'HKG', '2026-04-18T08:00:00Z',
                'headline', NULL, NULL, NULL, 'Policy support for Alpha Fintech', NULL, NULL,
                :gov_signal_refs, :gov_signal_extra
              ),
              (
                13, 'hkex_disclosure', 'annual_report_publication', 'signal-hsbc-market', 'market',
                '0005', 'HKG', '2026-04-21T08:30:00Z',
                'annual_report_published', NULL, '2026-04-21', NULL, 'HSBC annual report published', NULL, NULL,
                :hsbc_signal_refs, :hsbc_signal_extra
              )
            """
        ),
        {
            "alpha_signal_refs": json.dumps(["https://alpha.example.com/news"], ensure_ascii=False),
            "alpha_signal_extra": json.dumps({"language": "en"}, ensure_ascii=False),
            "gov_signal_refs": json.dumps(["https://www.info.gov.hk/gia/general"], ensure_ascii=False),
            "gov_signal_extra": json.dumps({"language": "en"}, ensure_ascii=False),
            "hsbc_signal_refs": json.dumps(["https://www1.hkexnews.hk/0005.pdf"], ensure_ascii=False),
            "hsbc_signal_extra": json.dumps({"stock_code": "0005"}, ensure_ascii=False),
        },
    )
    db.execute(
        text(
            """
            INSERT INTO client_one_view_timeline (
              id, source, company_id, entity, event_time, event_type, headline, detail, evidence_url, payload_json
            )
            VALUES
              (
                21, 'investhk_news', 'hkg-alpha-fintech', 'HKG', '2026-04-22T10:00:00Z',
                'event', 'Alpha Fintech expands into UAE', 'Expansion event',
                'https://alpha.example.com/news', :alpha_timeline_payload
              ),
              (
                22, 'hkex_disclosure', '0005', 'HKG', '2026-04-21T08:30:00Z',
                'document', 'HSBC annual report filed', 'Annual report publication',
                'https://www1.hkexnews.hk/0005.pdf', :hsbc_timeline_payload
              )
            """
        ),
        {
            "alpha_timeline_payload": json.dumps({"source": "investhk_news", "record_key": "news-1"}, ensure_ascii=False),
            "hsbc_timeline_payload": json.dumps({"source": "hkex_disclosure", "record_key": "hkex-1"}, ensure_ascii=False),
        },
    )
    db.execute(
        text(
            """
            INSERT INTO generated_insights (
              id, source, company_id, entity, insight_type, title, summary, confidence,
              model_name, prompt_version, generated_at
            )
            VALUES
              (
                31, 'rag', 'hkg-alpha-fintech', 'HKG', 'action',
                'Engage Alpha Fintech', 'Recent expansion and policy support justify follow-up.',
                0.81, 'gpt-4o-mini', 'rag-trusted-v1', '2026-04-22T11:00:00Z'
              )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO parsed_documents (
              id, source_table, source_id, source_content_hash, source_record_key, source, dataset,
              company_id, entity, title, summary, media_type, lang, file_path, evidence_url,
              parser_name, backend_name, parse_version, parse_status, ocr_status, xbrl_status,
              content_text, search_text, warnings_json, metadata_json, management_discussion_summary,
              management_discussion_highlights_json, management_discussion_source_sections_json,
              section_count, table_count, metric_count, risk_factor_count, business_event_count,
              parsed_at, run_id
            )
            VALUES
              (
                41, 'intelligence_records', 101, 'hash-doc-1', 'hkex-annual-1', 'hkex_disclosure',
                'annual_report_publication', 'hkg-alpha-fintech', 'HKG', 'Alpha Fintech Annual Report 2025',
                'Annual report parsed', 'application/pdf', 'en', 'D:/tmp/alpha-annual-report.pdf',
                'https://alpha.example.com/reports/annual-2025.pdf', 'document_parser', 'pymupdf',
                'v1', 'success', 'used', 'completed', 'full text', 'search text', :doc_warnings,
                :doc_metadata, 'Management highlights strong SME payment growth and GCC expansion.',
                :doc_highlights, :doc_sections, 12, 3, 2, 1, 1, '2026-04-22T09:30:00Z', 'parse-run-1'
              )
            """
        ),
        {
            "doc_warnings": json.dumps([], ensure_ascii=False),
            "doc_metadata": json.dumps(
                {
                    "pages": 48,
                    "genai_extraction": {
                        "status": "ok",
                        "prompt_version": "genai-section-extraction-v0.1",
                        "candidate_count": 1,
                        "accepted_count": 3,
                        "rejected_count": 1,
                        "accepted_facts": [
                            {
                                "fact_type": "risk_factor",
                                "category": "regulatory",
                                "description": "Cross-border licensing requirements are tightening.",
                                "severity": "medium",
                                "extraction_confidence": 0.91,
                                "evidence_span": {
                                    "document_id": "hkex-annual-1",
                                    "section_id": 2,
                                    "paragraph_id": 4,
                                    "chunk_id": "s2:p4",
                                    "page": 11,
                                    "quoted_text": "cross-border licensing requirements are tightening",
                                    "language": "en",
                                },
                                "scoring_eligibility": {
                                    "eligible": True,
                                    "reasons": ["valid_evidence_span", "allowed_candidate_section"],
                                },
                            },
                            {
                                "fact_type": "business_event",
                                "event_type": "expansion",
                                "summary": "Alpha Fintech launched UAE operations.",
                                "extraction_confidence": 0.89,
                                "evidence_span": {
                                    "document_id": "hkex-annual-1",
                                    "section_id": 2,
                                    "paragraph_id": 3,
                                    "chunk_id": "s2:p3",
                                    "page": 10,
                                    "quoted_text": "launched UAE operations",
                                    "language": "en",
                                },
                                "scoring_eligibility": {
                                    "eligible": True,
                                    "reasons": ["valid_evidence_span", "allowed_candidate_section"],
                                },
                            },
                            {
                                "fact_type": "management_statement",
                                "statement_type": "cross_border",
                                "summary": "Management sees GCC expansion momentum.",
                                "extraction_confidence": 0.86,
                                "evidence_span": {
                                    "document_id": "hkex-annual-1",
                                    "section_id": 2,
                                    "paragraph_id": 5,
                                    "chunk_id": "s2:p5",
                                    "page": 12,
                                    "quoted_text": "GCC expansion momentum",
                                    "language": "en",
                                },
                                "scoring_eligibility": {
                                    "eligible": False,
                                    "reasons": ["context_only_not_scoring_input"],
                                },
                            },
                        ],
                        "rejected_facts": [
                            {
                                "fact_type": "metric",
                                "reasons": ["duplicate_existing_fact"],
                                "normalized": {
                                    "fact_type": "metric",
                                    "name": "revenue_growth",
                                    "value": "18.5",
                                    "scoring_eligibility": {
                                        "eligible": False,
                                        "reasons": ["duplicate_existing_fact"],
                                    },
                                },
                            }
                        ],
                    },
                },
                ensure_ascii=False,
            ),
            "doc_highlights": json.dumps(["SME growth", "GCC expansion"], ensure_ascii=False),
            "doc_sections": json.dumps(["Management Discussion and Analysis"], ensure_ascii=False),
        },
    )
    db.execute(
        text(
            """
            INSERT INTO parsed_metrics (
              id, document_id, metric_index, name, value, unit, period, context, confidence
            )
            VALUES
              (51, 41, 0, 'revenue_growth', '18.5', '%', 'FY2025', 'management discussion', 0.91),
              (52, 41, 1, 'customer_deposits', '398046.34', 'HKD million', 'FY2025', 'financial highlights', 0.88)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO parsed_risk_factors (
              id, document_id, risk_index, category, description, severity, confidence
            )
            VALUES
              (61, 41, 0, 'regulatory', 'Expansion depends on cross-border licensing progress.', 'medium', 0.84)
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO parsed_business_events (
              id, document_id, event_index, event_type, summary, event_date, parties_json, confidence
            )
            VALUES
              (71, 41, 0, 'expansion', 'Alpha Fintech launched UAE operations.', '2026-03-15',
               :business_event_parties, 0.89)
            """
        ),
        {"business_event_parties": json.dumps(["Alpha Fintech", "UAE partners"], ensure_ascii=False)},
    )
    db.commit()


@contextmanager
def _test_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE companies (
              id INTEGER PRIMARY KEY,
              source TEXT NOT NULL,
              company_id TEXT NOT NULL,
              canonical_name TEXT NOT NULL,
              display_name TEXT,
              country TEXT,
              region TEXT,
              city TEXT,
              segments_json TEXT,
              industries_json TEXT,
              website_url TEXT,
              linkedin_url TEXT,
              facebook_url TEXT,
              x_url TEXT,
              instagram_url TEXT,
              wikipedia_url TEXT,
              profile_summary TEXT,
              description TEXT,
              extra_json TEXT,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE trigger_signals (
              id INTEGER PRIMARY KEY,
              source TEXT NOT NULL,
              dataset TEXT NOT NULL,
              signal_key TEXT NOT NULL,
              signal_type TEXT NOT NULL,
              company_id TEXT,
              entity TEXT,
              event_time TEXT NOT NULL,
              indicator TEXT,
              value_num REAL,
              value_text TEXT,
              unit TEXT,
              signal_text TEXT,
              signal_score REAL,
              signal_level TEXT,
              evidence_refs_json TEXT,
              extra_json TEXT
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE client_one_view_timeline (
              id INTEGER PRIMARY KEY,
              source TEXT NOT NULL,
              company_id TEXT,
              entity TEXT,
              event_time TEXT,
              event_type TEXT NOT NULL,
              headline TEXT NOT NULL,
              detail TEXT,
              evidence_url TEXT,
              payload_json TEXT
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE generated_insights (
              id INTEGER PRIMARY KEY,
              source TEXT NOT NULL,
              company_id TEXT,
              entity TEXT,
              insight_type TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT NOT NULL,
              confidence REAL,
              model_name TEXT,
              prompt_version TEXT,
              generated_at TEXT NOT NULL
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE prospect_workflow_states (
              prospect_id TEXT PRIMARY KEY,
              company_id TEXT NOT NULL,
              owner TEXT,
              stage TEXT NOT NULL,
              status TEXT NOT NULL,
              last_action TEXT,
              next_action TEXT,
              review_status TEXT NOT NULL,
              notes TEXT,
              updated_at TEXT NOT NULL
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE parsed_documents (
              id INTEGER PRIMARY KEY,
              source_table TEXT NOT NULL,
              source_id INTEGER NOT NULL,
              source_content_hash TEXT NOT NULL,
              source_record_key TEXT,
              source TEXT NOT NULL,
              dataset TEXT,
              company_id TEXT,
              entity TEXT,
              title TEXT,
              summary TEXT,
              media_type TEXT,
              lang TEXT,
              file_path TEXT,
              evidence_url TEXT,
              parser_name TEXT NOT NULL,
              backend_name TEXT,
              parse_version TEXT NOT NULL,
              parse_status TEXT NOT NULL,
              ocr_status TEXT,
              xbrl_status TEXT,
              content_text TEXT,
              search_text TEXT,
              warnings_json TEXT,
              metadata_json TEXT,
              management_discussion_summary TEXT,
              management_discussion_highlights_json TEXT,
              management_discussion_source_sections_json TEXT,
              section_count INTEGER NOT NULL,
              table_count INTEGER NOT NULL,
              metric_count INTEGER NOT NULL,
              risk_factor_count INTEGER NOT NULL,
              business_event_count INTEGER NOT NULL,
              parsed_at TEXT NOT NULL,
              run_id TEXT NOT NULL
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE parsed_metrics (
              id INTEGER PRIMARY KEY,
              document_id INTEGER NOT NULL,
              metric_index INTEGER NOT NULL,
              name TEXT NOT NULL,
              value TEXT NOT NULL,
              unit TEXT,
              period TEXT,
              context TEXT,
              confidence REAL
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE parsed_risk_factors (
              id INTEGER PRIMARY KEY,
              document_id INTEGER NOT NULL,
              risk_index INTEGER NOT NULL,
              category TEXT NOT NULL,
              description TEXT NOT NULL,
              severity TEXT NOT NULL,
              confidence REAL
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE parsed_business_events (
              id INTEGER PRIMARY KEY,
              document_id INTEGER NOT NULL,
              event_index INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              summary TEXT NOT NULL,
              event_date TEXT,
              parties_json TEXT,
              confidence REAL
            )
            """
        )

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with SessionLocal() as db:
        _seed_test_db(db)

    def override_get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_list_companies_returns_latest_company_snapshots() -> None:
    with _test_client() as client:
        response = client.get("/api/companies?segment=fintech")

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 20
    assert len(payload["items"]) == 1

    company = payload["items"][0]
    assert company["company_id"] == "hkg-alpha-fintech"
    assert company["display_name"] == "Alpha Fintech Holdings"
    assert company["segments"] == ["fintech", "sme"]
    assert company["signal_count"] == 2
    assert company["timeline_event_count"] == 1
    assert company["generated_insight_count"] == 1


def test_company_detail_returns_company_centric_view() -> None:
    with _test_client() as client:
        response = client.get("/api/companies/hkg-alpha-fintech")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company"]["company_id"] == "hkg-alpha-fintech"
    assert payload["company"]["profile_summary"] == "Latest summary"
    assert payload["stats"]["signal_count"] == 2
    assert payload["stats"]["timeline_event_count"] == 1
    assert payload["stats"]["generated_insight_count"] == 1
    assert payload["stats"]["signal_type_distribution"][0]["name"] in {"growth", "cross_border"}
    assert payload["latest_state"]["status"] == "actionable"
    assert payload["latest_state"]["state_summary"].startswith(
        "Company has enough linked evidence for immediate RM follow-up"
    )
    assert "growth" in payload["latest_state"]["focus_tags"]
    assert "management_discussion" in payload["latest_state"]["focus_tags"]
    assert payload["latest_state"]["signal_highlights"][0].startswith("2 recent signals linked")
    assert payload["latest_state"]["opportunity_signals"][0]["signal_type"] in {"growth", "cross_border"}
    assert payload["latest_state"]["opportunity_signals"][0]["source_type"] == "trigger_signal"
    assert payload["latest_state"]["context_signals"][0]["signal_type"] in {"growth", "cross_border"}
    assert payload["latest_state"]["context_signals"][0]["linkage_type"] == "direct_company_link"
    assert payload["latest_state"]["context_signals"][0]["linkage_label"] == "Direct company link"
    assert payload["latest_state"]["context_signals"][0]["linkage_strength"] == "strong"
    assert payload["latest_state"]["context_signals"][0]["linkage_rationale"] is not None
    assert payload["latest_state"]["context_signals"][0]["supports_company_scoring"] is True
    assert payload["latest_state"]["context_signals"][0]["context_only"] is False
    assert payload["latest_state"]["risk_signals"][0]["signal_type"] == "regulatory"
    assert payload["latest_state"]["risk_signals"][0]["severity"] == "medium"
    assert payload["latest_state"]["coverage_flags"]["has_recent_signals"] is True
    assert payload["latest_state"]["coverage_flags"]["has_parsed_reports"] is True
    assert payload["latest_state"]["coverage_flags"]["has_management_discussion"] is True
    assert payload["latest_state"]["coverage_flags"]["has_structured_metrics"] is True
    assert payload["latest_state"]["coverage_flags"]["has_risk_factors"] is True
    assert payload["latest_state"]["coverage_flags"]["has_business_events"] is True
    assert payload["latest_state"]["coverage_flags"]["has_ocr_support"] is True
    assert payload["latest_state"]["coverage_flags"]["has_xbrl_support"] is True
    assert "opportunity:" in payload["latest_state"]["why_now"]
    assert "risk watch:" in payload["latest_state"]["why_now"]
    assert "direct company evidence points to" in payload["latest_state"]["fusion_summary"].lower()
    assert payload["latest_state"]["fusion"]["primary_lens_key"] in {"acquisition", "financing", "cross_border"}
    assert payload["latest_state"]["fusion"]["primary_opportunity"] is not None
    assert payload["latest_state"]["fusion"]["context_alignment"] is not None
    assert payload["latest_state"]["fusion"]["key_risk"] is not None
    assert len(payload["latest_state"]["fusion"]["reasoning_steps"]) >= 3
    assert payload["latest_state"]["fusion"]["reasoning_steps"][0]["step_key"] == "company_evidence"
    assert len(payload["latest_state"]["fusion"]["opportunity_lenses"]) == 3
    assert payload["latest_state"]["fusion"]["opportunity_lenses"][0]["lens_key"] in {
        "acquisition",
        "financing",
        "cross_border",
    }
    assert payload["latest_state"]["product_fit"][0]["product_name"] == "cross-border payments"
    assert payload["latest_state"]["product_fit"][0]["fit_score"] >= 80
    assert payload["latest_state"]["recommended_entry_angles"][0].startswith("Lead with the company event:")
    assert payload["latest_state"]["commercial_attractiveness_score"] > 0
    assert payload["latest_state"]["immediacy_score"] > 0
    assert payload["latest_state"]["product_fit_score"] > 0
    assert payload["latest_state"]["risk_penalty_score"] > 0
    assert payload["latest_state"]["evidence_confidence_score"] > 0
    assert len(payload["latest_state"]["decision_answers"]) >= 4
    assert payload["latest_state"]["decision_answers"][0]["question_key"] == "priority"
    assert payload["latest_state"]["decision_answers"][0]["question"] == "Is this company worth prioritizing now?"
    assert len(payload["latest_state"]["decision_features"]) >= 4
    assert payload["latest_state"]["decision_features"][0]["feature_key"] is not None
    assert payload["latest_state"]["decision_features"][0]["feature_label"] is not None
    assert payload["latest_state"]["decision_features"][0]["feature_description"] is not None
    assert payload["latest_state"]["decision_features"][0]["business_question"] is not None
    assert isinstance(payload["latest_state"]["decision_features"][0]["preferred_linkage_types"], list)
    assert payload["latest_state"]["decision_features"][0]["max_score_contribution"] > 0
    assert payload["latest_state"]["recommended_next_step"].startswith("review latest risk factors")
    assert payload["latest_state"]["evidence_summary"]["parsed_document_count"] == 1
    assert payload["latest_state"]["evidence_summary"]["ocr_hit_count"] == 1
    assert payload["latest_state"]["evidence_summary"]["xbrl_hit_count"] == 1
    assert payload["recent_documents"][0]["title"] == "Alpha Fintech Annual Report 2025"
    assert payload["recent_documents"][0]["management_discussion_summary"].startswith("Management highlights")
    assert payload["recent_documents"][0]["genai_extraction"]["status"] == "ok"
    assert payload["recent_documents"][0]["genai_extraction"]["accepted_count"] == 3
    assert payload["recent_documents"][0]["genai_extraction"]["scoring_eligible_counts"] == {
        "risk_factor": 1,
        "business_event": 1,
    }
    assert payload["recent_documents"][0]["genai_extraction"]["context_only_count"] == 1
    assert payload["recent_documents"][0]["genai_extraction"]["accepted_facts"][0]["evidence_span"]["chunk_id"] == "s2:p4"
    assert payload["key_metrics"][0]["name"] == "revenue_growth"
    assert payload["key_risk_factors"][0]["category"] == "regulatory"
    assert payload["key_business_events"][0]["event_type"] == "expansion"
    assert payload["key_business_events"][0]["parties"] == ["Alpha Fintech", "UAE partners"]
    assert payload["recent_signals"][0]["signal_key"] == "signal-alpha-growth"
    assert payload["recent_timeline"][0]["headline"] == "Alpha Fintech expands into UAE"
    assert payload["recent_insights"][0]["title"] == "Engage Alpha Fintech"


def test_company_detail_returns_active_state_when_only_market_evidence_exists() -> None:
    with _test_client() as client:
        response = client.get("/api/companies/0005")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company"]["company_id"] == "0005"
    assert payload["stats"]["signal_count"] == 1
    assert payload["stats"]["generated_insight_count"] == 0
    assert payload["latest_state"]["status"] == "active"
    assert payload["latest_state"]["coverage_flags"]["has_recent_signals"] is True
    assert payload["latest_state"]["coverage_flags"]["has_parsed_reports"] is False
    assert payload["latest_state"]["opportunity_signals"][0]["signal_type"] == "market"
    assert payload["latest_state"]["context_signals"][0]["signal_type"] == "market"
    assert payload["latest_state"]["context_signals"][0]["linkage_type"] == "direct_company_link"
    assert payload["latest_state"]["context_signals"][0]["supports_company_scoring"] is True
    assert payload["latest_state"]["context_signals"][0]["context_only"] is False
    assert payload["latest_state"]["risk_signals"] == []
    assert payload["latest_state"]["fusion"]["primary_lens_key"] == "acquisition"
    assert payload["latest_state"]["product_fit"][0]["product_name"] == "capital markets"
    assert payload["latest_state"]["recommended_next_step"].startswith(
        "prepare acquisition outreach anchored on capital markets"
    )


def test_company_detail_returns_404_for_unknown_company() -> None:
    with _test_client() as client:
        response = client.get("/api/companies/missing-company")

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"
