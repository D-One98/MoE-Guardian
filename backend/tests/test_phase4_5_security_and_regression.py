import base64
import io
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.contracts import (
    AuditSnapshotRecord,
    EngineExecutionRecord,
    ExecutionState,
)
from app.services.orchestrator import VerityMoEOrchestrator
import app.services.orchestrator as orch_module

client = TestClient(app)


def _make_two_tone_png_b64(bg_rgb=(15, 23, 42), fg_rgb=(255, 255, 255)) -> str:
    img = Image.new("RGB", (60, 60), color=bg_rgb)
    for x in range(60):
        for y in range(30, 60):
            img.putpixel((x, y), fg_rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def test_hmac_signature_verification_and_review_note_tampering_detection():
    payload = {
        "campaign_id": "CAMP-SEC-01",
        "submitted_by_role": "CREATOR",
        "blocks": [
            {
                "document_block_id": "blk-sec-1",
                "text": "AURORAGEAR delivers 12 hours of guaranteed battery life.",
            }
        ],
    }
    audit_id = client.post("/api/audits", json=payload).json()["audit_id"]

    rev_resp = client.post(
        f"/api/audits/{audit_id}/review",
        json={
            "actor_role": "AUTHORISED_REVIEWER",
            "decision": "APPROVE",
            "override_justification": "Approved for controlled lab preview only.",
        },
    )
    assert rev_resp.status_code == 200
    snap_dict = rev_resp.json()["latest_snapshot"]
    snap_obj = AuditSnapshotRecord(**snap_dict)

    # 1. Untampered snapshot passes cryptographic verification
    assert VerityMoEOrchestrator.verify_snapshot_hmac(snap_obj) is True

    # 2. Tampering with review_notes invalidates the HMAC signature
    tampered_notes_snap = snap_obj.model_copy(
        update={"review_notes": "Tampered justification after sign-off"}
    )
    assert VerityMoEOrchestrator.verify_snapshot_hmac(tampered_notes_snap) is False

    # 3. Tampering with approver_role or content_sha256_hash invalidates the HMAC signature
    tampered_role_snap = snap_obj.model_copy(update={"approver_role": "BRAND_MANAGER"})
    assert VerityMoEOrchestrator.verify_snapshot_hmac(tampered_role_snap) is False


def test_combined_multi_engine_orchestration_ruleguard_claimguard_visualguard():
    # Submit a draft with a RuleGuard violation, a ClaimGuard violation, and a VisualGuard violation
    off_palette_b64 = _make_two_tone_png_b64(bg_rgb=(250, 0, 250), fg_rgb=(255, 200, 255))
    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-MULTI-01",
            "submitted_by_role": "CREATOR",
            "blocks": [
                {
                    "document_block_id": "blk-text-01",
                    "text": "AuroraGear delivers 24 hours of battery life under specified laboratory testing conditions.",
                }
            ],
            "visual_asset": {
                "document_block_id": "blk-img-01",
                "filename": "promo.png",
                "mime_type": "image/png",
                "image_base64": off_palette_b64,
                "alt_text": "",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    engines_triggered = {f["expert_engine"] for f in data["findings"]}
    assert "RuleGuard" in engines_triggered
    assert "ClaimGuard" in engines_triggered
    assert "VisualGuard" in engines_triggered
    assert data["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"
    assert set(data["ai_disclosure_log"]["deterministic_engines_executed"]) == {
        "RuleGuard",
        "ClaimGuard_Baseline",
        "VisualGuard_Baseline",
        "VoiceGuard_Baseline"
    }


def test_fail_closed_orchestration_when_text_engine_errors(monkeypatch):
    # Simulate an internal failure in RuleGuard -> must set mandatory_policies_enforced=False and escalate
    def _mock_broken_rule_guard(blocks, rules):
        return [], EngineExecutionRecord(
            expert_engine="RuleGuard",
            mandatory_enforced=True,
            execution_state=ExecutionState.ERROR,
            findings_count=0,
            notes="Simulated RuleGuard failure",
        )

    monkeypatch.setattr(orch_module, "run_rule_guard", _mock_broken_rule_guard)

    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-FAILCLOSED-01",
            "blocks": [
                {
                    "document_block_id": "blk-clean",
                    "text": "AURORAGEAR provides up to 12 hours of battery life under specified laboratory testing conditions.",
                }
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mandatory_policies_enforced"] is False
    assert data["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"

    # Brand Manager cannot approve an audit where an engine failed
    mgr_rev = client.post(
        f"/api/audits/{data['audit_id']}/review",
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE", "override_justification": "Try approve"},
    )
    assert mgr_rev.status_code == 403


def test_brand_manager_can_approve_clean_compliant_draft_without_override_note():
    compliant_b64 = _make_two_tone_png_b64(bg_rgb=(15, 23, 42), fg_rgb=(255, 255, 255))
    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-CLEAN-APPROVE",
            "blocks": [
                {
                    "document_block_id": "blk-clean",
                    "text": "AURORAGEAR provides up to 12 hours of battery life under specified laboratory testing conditions.",
                }
            ],
            "visual_asset": {
                "document_block_id": "blk-img-clean",
                "filename": "clean.png",
                "mime_type": "image/png",
                "image_base64": compliant_b64,
                "alt_text": "AURORAGEAR compliant navy and white product graphic",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["overall_status"] == "READY_FOR_MANAGER_APPROVAL"
    assert data["mandatory_policies_enforced"] is True

    rev = client.post(
        f"/api/audits/{data['audit_id']}/review",
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE"},
    )
    assert rev.status_code == 200
    assert rev.json()["overall_status"] == "APPROVED"


def test_request_changes_workflow_creates_signed_snapshot():
    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-REJECT-01",
            "blocks": [{"document_block_id": "blk-1", "text": "AuroraGear world's #1 laptop."}],
        },
    )
    audit_id = resp.json()["audit_id"]

    rev = client.post(
        f"/api/audits/{audit_id}/review",
        json={
            "actor_role": "BRAND_MANAGER",
            "decision": "REQUEST_CHANGES",
            "override_justification": "Please fix brand casing and remove superlative.",
        },
    )
    assert rev.status_code == 200
    data = rev.json()
    assert data["overall_status"] == "CHANGES_REQUESTED"
    assert data["latest_snapshot"]["approval_state"] == "CHANGES_REQUESTED"
    assert data["latest_snapshot"]["review_notes"] == "Please fix brand casing and remove superlative."
    
def test_mandatory_policies_enforced_is_false_when_visualguard_returns_insufficient_data():
    # Issue 1 regression test: Single-tone image -> INSUFFICIENT_DATA -> mandatory_policies_enforced must be False
    img = Image.new("RGB", (40, 40), color=(15, 23, 42))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    single_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-ISSUE1",
            "blocks": [{"document_block_id": "b1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "filename": "single.png",
                "mime_type": "image/png",
                "image_base64": single_b64,
                "alt_text": "Single tone navy card",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mandatory_policies_enforced"] is False
    assert data["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"


def test_privacy_gate_detects_and_reports_sensitive_patterns():
    # Issue 2 regression test: Verify real regex detection for email & phone in ai_disclosure_log
    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-ISSUE2",
            "blocks": [
                {
                    "document_block_id": "b1",
                    "text": "Contact AURORAGEAR support at lead@auroragear.example.com or 9876543210.",
                }
            ],
        },
    )
    assert resp.status_code == 201
    log = resp.json()["ai_disclosure_log"]
    assert log["privacy_masking_mode"] == "BASELINE_REGEX_ACTIVE"
    assert log["sensitive_matches_masked_count"] >= 2
    assert "email" in log["sensitive_categories_detected"]


def test_review_transition_table_blocks_duplicate_review_on_already_approved_audit():
    # Issue 5 regression test: Approved audit cannot be reviewed a second time
    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-ISSUE5",
            "blocks": [
                {
                    "document_block_id": "b1",
                    "text": "AURORAGEAR provides up to 12 hours of battery life under specified laboratory testing conditions.",
                }
            ],
        },
    )
    audit_id = resp.json()["audit_id"]

    first_rev = client.post(
        f"/api/audits/{audit_id}/review",
        json={"actor_role": "BRAND_MANAGER", "decision": "APPROVE"},
    )
    assert first_rev.status_code == 200

    # Second review attempt on already APPROVED audit must fail with 400 Bad Request
    second_rev = client.post(
        f"/api/audits/{audit_id}/review",
        json={"actor_role": "AUTHORISED_REVIEWER", "decision": "REQUEST_CHANGES", "override_justification": "Late change"},
    )
    assert second_rev.status_code == 400
    assert "terminal review state" in second_rev.json()["detail"]["message"]