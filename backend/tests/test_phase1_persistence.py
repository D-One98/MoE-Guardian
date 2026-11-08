import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import get_session_factory
from app.repositories.governance_repo import GovernanceRepository, DuplicateResourceError
from app.schemas.contracts import BrandRule, RuleCategory, Severity

client = TestClient(app)


def test_sqlite_foreign_keys_enabled():
    session_factory = get_session_factory()
    with session_factory() as db:
        fk_status = db.execute(text("PRAGMA foreign_keys")).scalar()
        assert fk_status == 1


def test_idempotent_seed_and_custom_preservation():
    session_factory = get_session_factory()
    with session_factory() as db:
        repo = GovernanceRepository(db)
        repo.ensure_demo_seed_data()
        initial_rules_count = len(repo.list_rules())
        initial_facts_count = len(repo.list_facts())

        # Re-running seed must not duplicate records
        repo.ensure_demo_seed_data()
        assert len(repo.list_rules()) == initial_rules_count
        assert len(repo.list_facts()) == initial_facts_count

        # Custom rule must not be overwritten by subsequent seeding
        custom_rule = BrandRule(
            rule_id="RULE-CUSTOM-101",
            category=RuleCategory.BANNED_TERM,
            title="Custom Banned Term",
            description="Do not use 'unbreakable'.",
            mandatory_flag=True,
            severity=Severity.MEDIUM,
            pattern_or_target="unbreakable",
        )
        repo.create_rule(custom_rule)
        repo.ensure_demo_seed_data()
        rule_ids = {r.rule_id for r in repo.list_rules()}
        assert "RULE-CUSTOM-101" in rule_ids


def test_audit_and_snapshot_persistence_across_service_recreation():
    payload = {
        "campaign_id": "CAMP-PHASE1-01",
        "submitted_by_role": "CREATOR",
        "blocks": [
            {
                "document_block_id": "blk-p1",
                "text": "AURORAGEAR delivers 12 hours of guaranteed battery life.",
            }
        ],
    }
    create_resp = client.post("/api/audits", json=payload)
    assert create_resp.status_code == 201
    audit_id = create_resp.json()["audit_id"]

    # Review and sign snapshot
    rev_resp = client.post(
        f"/api/audits/{audit_id}/review",
        json={
            "actor_role": "AUTHORISED_REVIEWER",
            "decision": "APPROVE",
            "override_justification": "Approved with lab note.",
        },
    )
    assert rev_resp.status_code == 200
    snap1_sig = rev_resp.json()["latest_snapshot"]["snapshot_hmac_signature"]

    # Simulate application restart with fresh TestClient
    fresh_client = TestClient(app)
    get_resp = fresh_client.get(f"/api/audits/{audit_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["audit_id"] == audit_id
    assert data["overall_status"] == "APPROVED"
    assert data["latest_snapshot"]["snapshot_hmac_signature"] == snap1_sig

    # Create second audit and verify HMAC chain continuity from persisted storage
    audit2_id = fresh_client.post(
        "/api/audits",
        json={"blocks": [{"document_block_id": "b2", "text": "AURORAGEAR workstation."}]},
    ).json()["audit_id"]
    rev2_resp = fresh_client.post(
        f"/api/audits/{audit2_id}/review",
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE"},
    )
    assert rev2_resp.status_code == 200
    assert rev2_resp.json()["latest_snapshot"]["previous_snapshot_hmac"] == snap1_sig


def test_database_transaction_rollback_on_duplicate_error():
    session_factory = get_session_factory()
    with session_factory() as db:
        repo = GovernanceRepository(db)
        repo.ensure_demo_seed_data()
        before = len(repo.list_rules())

        dup = BrandRule(
            rule_id="RULE-TERM-001",
            category=RuleCategory.BANNED_TERM,
            title="Dup",
            description="Duplicate ID test",
            mandatory_flag=True,
            severity=Severity.HIGH,
            pattern_or_target="dup",
        )
        with pytest.raises(DuplicateResourceError):
            repo.create_rule(dup)

        assert len(repo.list_rules()) == before