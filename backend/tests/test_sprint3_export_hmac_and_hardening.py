import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_session_factory
from app.core.tenant_context import create_hs256_jwt
from app.repositories.governance_repo import GovernanceRepository
from app.schemas.contracts import AuditSnapshotRecord, DemoRole
from app.services.orchestrator import VerityMoEOrchestrator

client = TestClient(app)

TEST_JWT_SECRET = "sprint3-test-supabase-jwt-hmac-secret-key-2026"
TEST_ISSUER = "https://example-project.supabase.co/auth/v1"
TEST_AUDIENCE = "authenticated"


def _issue_jwt(sub: str, extra: dict = None) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": TEST_ISSUER,
        "aud": TEST_AUDIENCE,
        "iat": now,
        "exp": now + 3600,
    }
    if extra:
        payload.update(extra)
    return create_hs256_jwt(payload, TEST_JWT_SECRET)


def test_1_to_5_compliance_export_cms_gating_and_secret_minimization():
    # 1. Create an audit with a violation (unapproved)
    create_resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-EXPORT-01",
            "blocks": [
                {
                    "document_block_id": "blk-exp-1",
                    "text": "AURORAGEAR delivers 12 hours of guaranteed battery life.",
                }
            ],
        },
    )
    assert create_resp.status_code == 201
    audit_id = create_resp.json()["audit_id"]

    # 2. Export BEFORE approval: CMS payload MUST exclude unapproved content blocks
    exp_unapproved = client.get(f"/api/audits/{audit_id}/export")
    assert exp_unapproved.status_code == 200
    exp_data = exp_unapproved.json()
    assert exp_data["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"
    assert exp_data["human_review_decision"] is None
    assert exp_data["snapshot_integrity"]["status_code"] == "NO_SNAPSHOT_FOUND"
    assert exp_data["simulated_cms_payload"]["export_ready_for_cms"] is False
    assert exp_data["simulated_cms_payload"]["external_cms_published"] is False
    assert exp_data["simulated_cms_payload"]["approved_blocks"] == []

    # 3. Approve audit via Authorised Reviewer with override justification
    rev_resp = client.post(
        f"/api/audits/{audit_id}/review",
        json={
            "actor_role": "AUTHORISED_REVIEWER",
            "decision": "APPROVE",
            "override_justification": "Approved for internal compliance export test.",
        },
    )
    assert rev_resp.status_code == 200

    # 4. Export AFTER approval: CMS payload now includes approved canonical blocks and verified snapshot
    exp_approved = client.get(f"/api/audits/{audit_id}/export")
    assert exp_approved.status_code == 200
    app_data = exp_approved.json()
    assert app_data["overall_status"] == "APPROVED"
    assert app_data["human_review_decision"]["approver_role"] == "AUTHORISED_REVIEWER"
    assert app_data["snapshot_integrity"]["is_valid"] is True
    assert app_data["snapshot_integrity"]["status_code"] == "VALID"
    assert app_data["simulated_cms_payload"]["export_ready_for_cms"] is True
    assert len(app_data["simulated_cms_payload"]["approved_blocks"]) == 1
    assert app_data["simulated_cms_payload"]["approved_blocks"][0]["document_block_id"] == "blk-exp-1"

    # 5. Verify no secret material leaks in export response
    serialized_export = str(app_data)
    assert "dev-only-replace-in-production-hmac-secret-key-2026" not in serialized_export
    assert TEST_JWT_SECRET not in serialized_export


def test_2_and_3_export_tenant_isolation_and_auth_enforcement(monkeypatch):
    monkeypatch.setenv("REQUIRE_VERIFIED_TENANT_AUTH", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", TEST_AUDIENCE)

    sf = get_session_factory()
    with sf() as db:
        repo = GovernanceRepository(db)
        repo.upsert_membership("user-alpha", "ORG-EXP-ALPHA", DemoRole.CREATOR)
        repo.upsert_membership("user-beta", "ORG-EXP-BETA", DemoRole.WORKSPACE_ADMIN)

    token_alpha = _issue_jwt("user-alpha")
    token_beta = _issue_jwt("user-beta")

    audit_alpha = client.post(
        "/api/audits",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={"blocks": [{"document_block_id": "b1", "text": "Alpha confidential draft."}]},
    ).json()

    # Unauthenticated export attempt fails with 401
    unauth_exp = client.get(f"/api/audits/{audit_alpha['audit_id']}/export")
    assert unauth_exp.status_code == 401

    # Cross-tenant export attempt by ORG-EXP-BETA fails with 404
    cross_exp = client.get(
        f"/api/audits/{audit_alpha['audit_id']}/export",
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    assert cross_exp.status_code == 404

    # Same-tenant export succeeds
    ok_exp = client.get(
        f"/api/audits/{audit_alpha['audit_id']}/export",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert ok_exp.status_code == 200
    assert ok_exp.json()["org_id"] == "ORG-EXP-ALPHA"


def test_6_to_14_hmac_key_versioning_rotation_tampering_and_chain_verification(monkeypatch):
    # Step A: Sign first audit snapshot using initial key 'key-v1-2025'
    monkeypatch.setenv("HMAC_KEY_ID", "key-v1-2025")
    monkeypatch.setenv("HMAC_SIGNING_SECRET", "secret-material-for-key-v1-2025-only")
    monkeypatch.setenv("HMAC_RETIRED_KEYS", "")

    a1_id = client.post(
        "/api/audits",
        json={"blocks": [{"document_block_id": "b1", "text": "AURORAGEAR workstation."}]},
    ).json()["audit_id"]
    r1 = client.post(
        f"/api/audits/{a1_id}/review",
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE"},
    ).json()
    snap1 = AuditSnapshotRecord(**r1["latest_snapshot"])
    assert snap1.hmac_key_id == "key-v1-2025"

    # Verify with original key active
    v1_check = client.get(f"/api/audits/{a1_id}/verify-snapshot").json()
    assert v1_check["is_valid"] is True
    assert v1_check["status_code"] == "VALID"
    assert v1_check["hmac_key_id"] == "key-v1-2025"

    # Step B: Rotate to new active key 'key-v2-2026' while keeping 'key-v1-2025' in HMAC_RETIRED_KEYS
    monkeypatch.setenv("HMAC_KEY_ID", "key-v2-2026")
    monkeypatch.setenv("HMAC_SIGNING_SECRET", "brand-new-rotated-secret-key-v2-2026")
    monkeypatch.setenv("HMAC_RETIRED_KEYS", "key-v1-2025:secret-material-for-key-v1-2025-only")

    # New snapshot uses 'key-v2-2026' and chains to snap1
    a2_id = client.post(
        "/api/audits",
        json={"blocks": [{"document_block_id": "b2", "text": "AURORAGEAR notebook."}]},
    ).json()["audit_id"]
    r2 = client.post(
        f"/api/audits/{a2_id}/review",
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE"},
    ).json()
    snap2 = AuditSnapshotRecord(**r2["latest_snapshot"])
    assert snap2.hmac_key_id == "key-v2-2026"
    assert snap2.previous_snapshot_hmac == snap1.snapshot_hmac_signature

    # Both historical snapshot (key-v1-2025) and new snapshot (key-v2-2026) verify as VALID!
    v1_after_rotation = client.get(f"/api/audits/{a1_id}/verify-snapshot").json()
    v2_after_rotation = client.get(f"/api/audits/{a2_id}/verify-snapshot").json()
    assert v1_after_rotation["is_valid"] is True
    assert v1_after_rotation["status_code"] == "VALID"
    assert v2_after_rotation["is_valid"] is True
    assert v2_after_rotation["status_code"] == "VALID"
    assert v2_after_rotation["chain_integrity_verified"] is True

    # Step C: Unknown key ID rejection
    unknown_key_snap = snap1.model_copy(update={"hmac_key_id": "key-v99-unknown"})
    is_ok, status_code, _ = VerityMoEOrchestrator.verify_snapshot_hmac_detailed(unknown_key_snap)
    assert is_ok is False
    assert status_code.value == "UNKNOWN_KEY_ID"

    # Step D: Tampered payload / invalid signature rejection
    tampered_payload_snap = snap2.model_copy(update={"review_notes": "Injected note"})
    is_ok_t, status_code_t, _ = VerityMoEOrchestrator.verify_snapshot_hmac_detailed(tampered_payload_snap)
    assert is_ok_t is False
    assert status_code_t.value == "INVALID_SIGNATURE"

    # Step E: Malformed signature rejection
    malformed_snap = snap2.model_copy(update={"snapshot_hmac_signature": "short-invalid-sig"})
    is_ok_m, status_code_m, _ = VerityMoEOrchestrator.verify_snapshot_hmac_detailed(malformed_snap)
    assert is_ok_m is False
    assert status_code_m.value == "MALFORMED_SNAPSHOT"


def test_12_missing_or_insecure_production_hmac_signing_config_fails_closed(monkeypatch):
    sf = get_session_factory()
    with sf() as db:
        repo = GovernanceRepository(db)
        repo.upsert_membership("user-mgr-prod", "ORG-SAMPLE-DEMO-01", DemoRole.BRAND_MANAGER)

    audit_id = client.post(
        "/api/audits",
        json={"blocks": [{"document_block_id": "b1", "text": "AURORAGEAR workstation."}]},
    ).json()["audit_id"]

    # 1. Production environment requires verified JWT AND refuses default dev HMAC_SIGNING_SECRET with 503
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", TEST_AUDIENCE)
    monkeypatch.setenv("HMAC_SIGNING_SECRET", "dev-only-replace-in-production-hmac-secret-key-2026")

    mgr_token = _issue_jwt("user-mgr-prod")
    rev = client.post(
        f"/api/audits/{audit_id}/review",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE"},
    )
    assert rev.status_code == 503
    assert rev.json()["detail"]["error"] == "HMAC_SIGNING_CONFIG_ERROR"

    # 2. Missing/empty HMAC_SIGNING_SECRET also fails closed with 503
    monkeypatch.setenv("HMAC_SIGNING_SECRET", "   ")
    rev_empty = client.post(
        f"/api/audits/{audit_id}/review",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE"},
    )
    assert rev_empty.status_code == 503
    assert rev_empty.json()["detail"]["error"] == "HMAC_SIGNING_CONFIG_ERROR"


def test_16_multi_tenant_membership_requires_explicit_org_selection(monkeypatch):
    monkeypatch.setenv("REQUIRE_VERIFIED_TENANT_AUTH", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", TEST_AUDIENCE)

    sf = get_session_factory()
    with sf() as db:
        repo = GovernanceRepository(db)
        # User belongs to TWO active organisations
        repo.upsert_membership("user-multi-org", "ORG-MULTI-1", DemoRole.BRAND_MANAGER)
        repo.upsert_membership("user-multi-org", "ORG-MULTI-2", DemoRole.WORKSPACE_ADMIN)

    token = _issue_jwt("user-multi-org")

    # 1. Request without explicit org selection must be rejected (never silently pick an arbitrary tenant)
    ambiguous_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ambiguous_resp.status_code == 400
    assert ambiguous_resp.json()["detail"]["error"] == "AMBIGUOUS_TENANT_MEMBERSHIP_SELECTION_REQUIRED"

    # 2. Request with explicit X-Demo-Org-Id selects the verified membership & role for that org
    explicit_1 = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Demo-Org-Id": "ORG-MULTI-1"},
    )
    assert explicit_1.status_code == 200
    assert explicit_1.json()["org_id"] == "ORG-MULTI-1"
    assert explicit_1.json()["role"] == "BRAND_MANAGER"

    explicit_2 = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Demo-Org-Id": "ORG-MULTI-2"},
    )
    assert explicit_2.status_code == 200
    assert explicit_2.json()["org_id"] == "ORG-MULTI-2"
    assert explicit_2.json()["role"] == "WORKSPACE_ADMIN"