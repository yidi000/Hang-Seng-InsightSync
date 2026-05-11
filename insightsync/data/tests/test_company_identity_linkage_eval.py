from __future__ import annotations

import json
import tempfile
from pathlib import Path

from insightsync.data.pipeline.company_mapper import _build_alias_index, _match_company_id
from insightsync.data.pipeline.models import CollectionBatch, CompanyProfile, IntelligenceRecord
from insightsync.data.pipeline.storage import SQLiteRepository

EVAL_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "company_identity_linkage_cases.json"


def _seed_identity_repo(db_path: Path) -> None:
    with SQLiteRepository(db_path) as repo:
        repo.start_run("identity-seed", started_at="2026-05-11T00:00:00Z")
        batch = CollectionBatch(
            source="identity_eval_seed",
            companies=[
                CompanyProfile(
                    source="company_directory",
                    company_id="hkg-alpha-fintech",
                    canonical_name="Alpha Fintech",
                    display_name="Alpha Fintech Holdings",
                    country="China",
                    region="Hong Kong",
                    city="Hong Kong",
                    segments=["fintech", "cross_border"],
                    industries=["Payments"],
                    description="Identity evaluation seed.",
                    extra={"aliases": ["阿爾法金融科技", "阿尔法金融科技", "Alpha Fintech Holdings"]},
                ),
                CompanyProfile(
                    source="company_directory",
                    company_id="hkg-alpha-logistics",
                    canonical_name="Alpha Logistics",
                    display_name="Alpha Logistics Holdings",
                    country="China",
                    region="Hong Kong",
                    city="Hong Kong",
                    segments=["logistics"],
                    industries=["Logistics"],
                    description="Ambiguity guard seed.",
                    extra={"aliases": ["Alpha Group"]},
                ),
                CompanyProfile(
                    source="company_directory",
                    company_id="hkg-alpha-media",
                    canonical_name="Alpha Media",
                    display_name="Alpha Media Holdings",
                    country="China",
                    region="Hong Kong",
                    city="Hong Kong",
                    segments=["media"],
                    industries=["Media"],
                    description="Ambiguity guard seed.",
                    extra={"aliases": ["Alpha Group"]},
                ),
            ],
            intelligence_records=[
                IntelligenceRecord(
                    source="hkex_disclosure",
                    dataset="annual_report_publication",
                    record_key="hkex-0005",
                    record_type="document",
                    event_time="2026-04-20",
                    company_id="0005",
                    entity="HKG",
                    title="HSBC Holdings annual report",
                    summary="Annual report publication",
                    region="Hong Kong",
                    industry="Banking",
                    tags=["hkex_disclosure"],
                    payload={"stock_code": "0005", "company_name": "HSBC Holdings"},
                    evidence_url=None,
                    lang="en",
                    raw=None,
                )
            ],
        )
        repo.persist_batch("identity-seed", batch, fetched_at="2026-05-11T00:00:00Z")
        repo.finish_run("identity-seed", status="success", message="ok", summary={"ok": True})


def test_company_identity_linkage_evaluation_cases() -> None:
    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    assert cases

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "identity.db"
        _seed_identity_repo(db_path)

        with SQLiteRepository(db_path) as repo:
            alias_index = _build_alias_index(repo)

        for case in cases:
            company_id, alias, confidence = _match_company_id(case["text"], alias_index)

            if case["should_match"]:
                assert company_id == case["expected_company_id"], case["case_id"]
                assert alias == case["expected_alias"], case["case_id"]
                assert confidence is not None and confidence >= 0.85, case["case_id"]
            else:
                assert company_id is None, case["case_id"]
                assert alias is None, case["case_id"]
                assert confidence is None, case["case_id"]
