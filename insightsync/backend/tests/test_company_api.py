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
    assert payload["recent_signals"][0]["signal_key"] == "signal-alpha-growth"
    assert payload["recent_timeline"][0]["headline"] == "Alpha Fintech expands into UAE"
    assert payload["recent_insights"][0]["title"] == "Engage Alpha Fintech"


def test_company_detail_returns_404_for_unknown_company() -> None:
    with _test_client() as client:
        response = client.get("/api/companies/missing-company")

    assert response.status_code == 404
    assert response.json()["detail"] == "Company not found"
