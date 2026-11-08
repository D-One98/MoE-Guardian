import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_session_factory
from app.core.tenant_context import create_hs256_jwt
from app.repositories.governance_repo import GovernanceRepository
from app.schemas.contracts import DemoRole

client = TestClient(app)

TEST_JWT_SECRET = "sprint1-test-supabase-jwt-hmac-secret-key-2026"
TEST_ISSUER = "https://example-project.supabase.co/auth/v1"
TEST_AUDIENCE = "authenticated"


def _seed_test_memberships():
    sf = get_session_factory()
    with sf() as db:
        repo = GovernanceRepository(db)
        repo.upsert_membership("user-creator-alpha", "ORG-ALPHA", DemoRole.CREATOR)
        repo.upsert_membership("user-reviewer-alpha", "ORG-ALPHA", DemoRole.AUTHORISED_REVIEWER)
        repo.upsert_membership("user-admin-alpha", "ORG-ALPHA", DemoRole.WORKSPACE_ADMIN)
        repo.upsert_membership("user-admin-beta", "ORG-BETA", DemoRole.WORKSPACE_ADMIN)


def _configure_auth_env(monkeypatch, require_auth: bool = True):
    monkeypatch.setenv("REQUIRE_VERIFIED_TENANT_AUTH", "true" if require_auth else "false")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", TEST_AUDIENCE)


def _issue_token(sub: str, exp_offset: int = 3600, iss: str = TEST_ISSUER, aud: str = TEST_AUDIENCE, secret: str = TEST_JWT_SECRET, extra: dict = None) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + exp_offset,
    }
    if extra:
        payload.update(extra)
    return create_hs256_jwt(payload, secret)


def test_1_require_verified_tenant_auth_rejects_missing_bearer_token(monkeypatch):
    _configure_auth_env(monkeypatch, require_auth=True)
    resp = client.get("/api/brand/rules")
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"] == "UNAUTHORIZED_TENANT_CONTEXT"


def test_2_production_env_automatically_enforces_verified_auth_without_demo_fallback(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("REQUIRE_VERIFIED_TENANT_AUTH", "false")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)

    # Even if X-Demo-Org-Id is passed, production mode refuses unauthenticated demo fallback
    resp = client.get("/api/brand/rules", headers={"X-Demo-Org-Id": "ORG-ALPHA"})
    assert resp.status_code == 401


def test_3_valid_jwt_resolves_org_and_role_from_server_side_membership(monkeypatch):
    _configure_auth_env(monkeypatch, require_auth=True)
    _seed_test_memberships()

    token = _issue_token(sub="user-admin-alpha")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "user-admin-alpha"
    assert data["org_id"] == "ORG-ALPHA"
    assert data["role"] == "WORKSPACE_ADMIN"
    assert data["is_demo_fallback"] is False
    assert data["auth_mode"] == "VERIFIED_JWT_SERVER_MEMBERSHIP"


def test_4_jwt_rejects_invalid_signature_expired_token_and_wrong_issuer_or_audience(monkeypatch):
    _configure_auth_env(monkeypatch, require_auth=True)
    _seed_test_memberships()

    # 1. Wrong signing secret
    bad_sig_token = _issue_token(sub="user-admin-alpha", secret="wrong-secret-key")
    r_sig = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_sig_token}"})
    assert r_sig.status_code == 401
    assert r_sig.json()["detail"]["error"] == "INVALID_JWT_SIGNATURE"

    # 2. Expired token
    expired_token = _issue_token(sub="user-admin-alpha", exp_offset=-60)
    r_exp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r_exp.status_code == 401
    assert r_exp.json()["detail"]["error"] == "EXPIRED_JWT"

    # 3. Wrong issuer
    bad_iss_token = _issue_token(sub="user-admin-alpha", iss="https://evil.example.com")
    r_iss = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_iss_token}"})
    assert r_iss.status_code == 401
    assert r_iss.json()["detail"]["error"] == "INVALID_JWT_ISSUER"

    # 4. Wrong audience
    bad_aud_token = _issue_token(sub="user-admin-alpha", aud="wrong-audience")
    r_aud = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_aud_token}"})
    assert r_aud.status_code == 401
    assert r_aud.json()["detail"]["error"] == "INVALID_JWT_AUDIENCE"


def test_5_authenticated_user_cannot_access_unauthorised_tenant_org(monkeypatch):
    _configure_auth_env(monkeypatch, require_auth=True)
    _seed_test_memberships()

    # user-admin-alpha belongs to ORG-ALPHA, attempts to access ORG-BETA via header or claim
    token_alpha = _issue_token(sub="user-admin-alpha")
    resp = client.get(
        "/api/brand/rules",
        headers={
            "Authorization": f"Bearer {token_alpha}",
            "X-Demo-Org-Id": "ORG-BETA",
        },
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["error"] == "TENANT_MEMBERSHIP_DENIED"


def test_6_creator_cannot_modify_brand_rules_or_spoof_reviewer_role(monkeypatch):
    _configure_auth_env(monkeypatch, require_auth=True)
    _seed_test_memberships()

    creator_token = _issue_token(sub="user-creator-alpha")
    reviewer_token = _issue_token(sub="user-reviewer-alpha")
    admin_token = _issue_token(sub="user-admin-alpha")

    # 1. Creator is blocked from creating brand rules (403 INSUFFICIENT_TENANT_ROLE)
    rule_payload = {
        "rule_id": "RULE-ALPHA-01",
        "category": "BANNED_TERM",
        "title": "Ban phrase 'untested'",
        "description": "Never use 'untested' in Alpha copy.",
        "mandatory_flag": True,
        "severity": "HIGH",
        "pattern_or_target": "untested",
    }
    r_creator_rule = client.post(
        "/api/brand/rules",
        headers={"Authorization": f"Bearer {creator_token}"},
        json=rule_payload,
    )
    assert r_creator_rule.status_code == 403
    assert r_creator_rule.json()["detail"]["error"] == "INSUFFICIENT_TENANT_ROLE"

    # 2. Admin creates the rule in ORG-ALPHA
    r_admin_rule = client.post(
        "/api/brand/rules",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=rule_payload,
    )
    assert r_admin_rule.status_code == 201

    # 3. Creator submits an audit (even if Creator passes submitted_by_role='WORKSPACE_ADMIN', backend forces 'CREATOR')
    audit_resp = client.post(
        "/api/audits",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={
            "campaign_id": "CAMP-ALPHA-AUTH",
            "submitted_by_role": "WORKSPACE_ADMIN",
            "blocks": [{"document_block_id": "b1", "text": "Alpha product with untested module."}],
        },
    )
    assert audit_resp.status_code == 201
    audit_data = audit_resp.json()
    assert audit_data["org_id"] == "ORG-ALPHA"
    assert audit_data["submitted_by_role"] == "CREATOR"

    # 4. Creator attempts to spoof AUTHORISED_REVIEWER in review payload -> blocked with 403 ROLE_SPOOFING_FORBIDDEN
    spoof_rev = client.post(
        f"/api/audits/{audit_data['audit_id']}/review",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={
            "actor_role": "AUTHORISED_REVIEWER",
            "decision": "APPROVE",
            "override_justification": "Trying to bypass maker-checker via role spoofing",
        },
    )
    assert spoof_rev.status_code == 403
    assert spoof_rev.json()["detail"]["error"] == "ROLE_SPOOFING_FORBIDDEN"

    # 5. Authorised Reviewer in ORG-ALPHA legitimately approves the escalated audit
    valid_rev = client.post(
        f"/api/audits/{audit_data['audit_id']}/review",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={
            "actor_role": "AUTHORISED_REVIEWER",
            "decision": "APPROVE",
            "override_justification": "Approved for internal engineering review.",
        },
    )
    assert valid_rev.status_code == 200
    assert valid_rev.json()["overall_status"] == "APPROVED"


def test_7_cross_tenant_audit_and_review_isolation_under_verified_jwt(monkeypatch):
    _configure_auth_env(monkeypatch, require_auth=True)
    _seed_test_memberships()

    alpha_creator = _issue_token(sub="user-creator-alpha")
    beta_admin = _issue_token(sub="user-admin-beta")

    audit_alpha = client.post(
        "/api/audits",
        headers={"Authorization": f"Bearer {alpha_creator}"},
        json={"blocks": [{"document_block_id": "b1", "text": "Alpha draft content."}]},
    ).json()

    # ORG-BETA admin cannot view or review ORG-ALPHA's audit
    get_beta = client.get(
        f"/api/audits/{audit_alpha['audit_id']}",
        headers={"Authorization": f"Bearer {beta_admin}"},
    )
    assert get_beta.status_code == 404

    rev_beta = client.post(
        f"/api/audits/{audit_alpha['audit_id']}/review",
        headers={"Authorization": f"Bearer {beta_admin}"},
        json={"actor_role": "WORKSPACE_ADMIN", "decision": "APPROVE"},
    )
    assert rev_beta.status_code == 404


def test_8_missing_jwt_secret_fails_closed_with_503(monkeypatch):
    monkeypatch.setenv("REQUIRE_VERIFIED_TENANT_AUTH", "true")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    token = _issue_token(sub="user-admin-alpha")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 503
    assert resp.json()["detail"]["error"] == "JWT_SECRET_NOT_CONFIGURED"