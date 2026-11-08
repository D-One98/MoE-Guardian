from fastapi.testclient import TestClient
from app.main import app
from app.schemas.contracts import (
    EngineExecutionRecord,
    ExecutionState,
    FindingType,
    VerificationStatus,
)
from app.services.seed_data import get_demo_approved_facts, get_demo_brand_rules
import app.services.rewrite_coordinator as coord_module
import app.engines.claim_guard as cg_module
import app.engines.voice_guard as vg_voice_module

client = TestClient(app)


def test_1_clean_non_factual_rewrite_passes():
    # Create an audit with a tone violation ('crush the competition!!')
    audit_resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-T2-01",
            "blocks": [
                {
                    "document_block_id": "blk-tone-1",
                    "text": "AURORAGEAR is built to crush the competition!!",
                }
            ],
        },
    )
    assert audit_resp.status_code == 201
    audit_data = audit_resp.json()
    tone_findings = [f for f in audit_data["findings"] if f["expert_engine"] == "VoiceGuard"]
    assert len(tone_findings) >= 1
    # Verify VoiceGuard did NOT auto-generate a rewrite during audit
    assert all(f["rewrite_candidate"] is None for f in tone_findings)

    finding_id = tone_findings[0]["finding_id"]
    # Request on-demand clean non-factual rewrite
    rw_resp = client.post(
        f"/api/audits/{audit_data['audit_id']}/findings/{finding_id}/rewrite",
        json={},
    )
    assert rw_resp.status_code == 200
    rw_data = rw_resp.json()
    cand = rw_data["rewrite_candidates"][0]
    assert cand["backend_revalidation"]["revalidation_passed"] is True
    assert cand["backend_revalidation"]["candidate_verification_status"] == "NOT_CLAIM_APPLICABLE"
    assert cand["backend_revalidation"]["executed_checks"]["RuleGuard_violations_count"] == 0
    assert rw_data["selected_primary_candidate"] is not None


def test_2_rewrite_introducing_supported_factual_claim_passes():
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-SUPP",
        suggested_text="AURORAGEAR provides up to 12 hours of battery life under specified laboratory testing conditions.",
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.TONE_MESSAGING,
        original_matched_text="crush the competition",
    )
    assert cand.backend_revalidation.executed_checks["ClaimGuard_required"] is True
    assert cand.backend_revalidation.candidate_verification_status == VerificationStatus.SUPPORTED
    assert cand.backend_revalidation.revalidation_passed is True


def test_3_rewrite_omitting_mandatory_factual_qualifiers_partial_fails_closed():
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    # Omits 'up to' -> PARTIAL -> must fail closed (revalidation_passed = False)
    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-PARTIAL",
        suggested_text="AURORAGEAR provides 12 hours of battery life under specified laboratory testing conditions.",
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.FACTUAL_CLAIM,
        original_matched_text="12 hours battery",
    )
    assert cand.backend_revalidation.candidate_verification_status == VerificationStatus.PARTIAL
    assert cand.backend_revalidation.revalidation_passed is False


def test_4_rewrite_containing_contradicted_claim_fails_closed():
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    # 36 hours > 12 hours approved spec -> CONTRADICTED -> revalidation_passed = False
    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-CONTRA",
        suggested_text="AURORAGEAR provides up to 36 hours of battery life under specified laboratory testing conditions.",
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.FACTUAL_CLAIM,
        original_matched_text="36 hours battery",
    )
    assert cand.backend_revalidation.candidate_verification_status == VerificationStatus.CONTRADICTED
    assert cand.backend_revalidation.revalidation_passed is False


def test_5_rewrite_containing_unverifiable_claim_fails_closed():
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    # Unbacked deep-space claim -> UNVERIFIABLE -> revalidation_passed = False
    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-UNVER",
        suggested_text="AURORAGEAR is certified to operate at 9000 meters altitude.",
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.TONE_MESSAGING,
        original_matched_text="crush the competition",
    )
    assert cand.backend_revalidation.candidate_verification_status == VerificationStatus.UNVERIFIABLE
    assert cand.backend_revalidation.revalidation_passed is False


def test_6_ruleguard_violation_in_candidate_fails_closed():
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    # Contains wrong brand casing 'AuroraGear' and banned term 'world's #1'
    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-RG-FAIL",
        suggested_text="AuroraGear is the world's #1 portable workstation.",
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.TONE_MESSAGING,
        original_matched_text="mind-blowing",
    )
    assert cand.backend_revalidation.executed_checks["RuleGuard_violations_count"] >= 2
    assert cand.backend_revalidation.revalidation_passed is False


def test_7_engine_error_during_revalidation_fails_closed(monkeypatch):
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    def _broken_rule_guard(blocks, active_rules):
        return [], EngineExecutionRecord(
            expert_engine="RuleGuard",
            mandatory_enforced=False,
            execution_state=ExecutionState.ERROR,
            findings_count=0,
            notes="Simulated RuleGuard engine crash",
        )

    monkeypatch.setattr(coord_module, "run_rule_guard", _broken_rule_guard)

    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-ERROR",
        suggested_text="AURORAGEAR portable workstation.",
        rules=rules,
        facts=facts,
    )
    assert cand.backend_revalidation.executed_checks["RuleGuard_execution_state"] == "ERROR"
    assert cand.backend_revalidation.revalidation_passed is False


def test_8_insufficient_data_result_during_revalidation_fails_closed(monkeypatch):
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    def _insufficient_claim_guard(blocks, active_facts, active_rules, generate_rewrites=False):
        return [], EngineExecutionRecord(
            expert_engine="ClaimGuard",
            mandatory_enforced=True,
            execution_state=ExecutionState.INSUFFICIENT_DATA,
            findings_count=0,
            notes="Simulated INSUFFICIENT_DATA state",
        )

    monkeypatch.setattr(cg_module, "run_claim_guard_baseline", _insufficient_claim_guard)

    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-INSUFF",
        suggested_text="AURORAGEAR provides up to 12 hours of battery life under specified laboratory testing conditions.",
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.FACTUAL_CLAIM,
    )
    assert cand.backend_revalidation.executed_checks["ClaimGuard_execution_state"] == "INSUFFICIENT_DATA"
    assert cand.backend_revalidation.revalidation_passed is False


def test_9_no_recursive_voiceguard_invocation():
    vg_voice_module.VOICE_GUARD_INVOCATION_LOG.clear()
    rules = get_demo_brand_rules()
    facts = get_demo_approved_facts()

    cand = coord_module.validate_rewrite_candidate(
        candidate_id="RW-TEST-NOREC",
        suggested_text="AURORAGEAR delivers reliable engineering performance.",
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.TONE_MESSAGING,
        original_matched_text="crush the competition",
    )
    assert cand.backend_revalidation.revalidation_passed is True
    assert cand.backend_revalidation.executed_checks["VoiceGuard_recursive_call"] == "SKIPPED_BY_DESIGN"
    # Verify run_voice_guard_baseline was NOT called during candidate validation
    assert "run_voice_guard_baseline" not in vg_voice_module.VOICE_GUARD_INVOCATION_LOG


def test_10_tenant_isolation_during_rewrite_validation():
    org_a = {"X-Demo-Org-Id": "ORG-TENANT-RW-A"}
    org_b = {"X-Demo-Org-Id": "ORG-TENANT-RW-B"}

    # Add a custom banned term 'velociraptor' ONLY in ORG-TENANT-RW-A
    client.post(
        "/api/brand/rules",
        headers=org_a,
        json={
            "rule_id": "RULE-A-ONLY-01",
            "category": "BANNED_TERM",
            "title": "Ban velociraptor in Org A",
            "description": "Never use 'velociraptor' in Org A copy.",
            "mandatory_flag": True,
            "severity": "HIGH",
            "pattern_or_target": "velociraptor",
        },
    )

    # Create an audit in ORG-TENANT-RW-A
    audit_a = client.post(
        "/api/audits",
        headers=org_a,
        json={"blocks": [{"document_block_id": "b1", "text": "Buy now or regret!!"}]},
    ).json()
    finding_id_a = audit_a["findings"][0]["finding_id"]

    # 1. ORG-TENANT-RW-B cannot access or request rewrites on ORG-TENANT-RW-A's audit
    cross_tenant_resp = client.post(
        f"/api/audits/{audit_a['audit_id']}/findings/{finding_id_a}/rewrite",
        headers=org_b,
        json={"custom_candidate_text": "Clean engineering text."},
    )
    assert cross_tenant_resp.status_code == 404

    # 2. Within ORG-TENANT-RW-A, a rewrite containing Org A's banned term 'velociraptor' fails closed
    same_tenant_resp = client.post(
        f"/api/audits/{audit_a['audit_id']}/findings/{finding_id_a}/rewrite",
        headers=org_a,
        json={"custom_candidate_text": "Explore our velociraptor workstation."},
    )
    assert same_tenant_resp.status_code == 200
    assert same_tenant_resp.json()["rewrite_candidates"][0]["backend_revalidation"]["revalidation_passed"] is False


def test_11_client_attempts_to_forge_revalidation_passed_or_verification_status_rejected():
    audit_resp = client.post(
        "/api/audits",
        json={"blocks": [{"document_block_id": "b1", "text": "AURORAGEAR is mind-blowing!!"}]},
    ).json()
    finding_id = audit_resp["findings"][0]["finding_id"]

    # Client attempts to inject revalidation_passed=True and candidate_verification_status='SUPPORTED'
    forge_resp = client.post(
        f"/api/audits/{audit_resp['audit_id']}/findings/{finding_id}/rewrite",
        json={
            "custom_candidate_text": "AuroraGear world's #1 guaranteed",
            "revalidation_passed": True,
            "candidate_verification_status": "SUPPORTED",
        },
    )
    assert forge_resp.status_code == 422