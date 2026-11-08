from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_session_factory
from app.repositories.governance_repo import GovernanceRepository

client = TestClient(app)


def test_create_brand_rule_and_participate_in_audit():
    payload = {
        "rule_id": "RULE-TERM-201",
        "category": "BANNED_TERM",
        "title": "Prohibit phrase 'quantum-proof'",
        "description": "Do not use unverified 'quantum-proof' terminology in product copy.",
        "mandatory_flag": True,
        "severity": "HIGH",
        "pattern_or_target": "quantum-proof",
        "expected_replacement": "hardware-encrypted",
        "document_id": "DOC-CUSTOM-POLICY-V1",
        "document_name": "Custom_Security_Guidelines.pdf",
        "verified_page_or_row": 3,
        "version": "1.0",
        "campaign_scope": "GLOBAL",
    }

    # 1. Valid creation returns 201
    resp = client.post("/api/brand/rules", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["rule"]["rule_id"] == "RULE-TERM-201"

    # 2. Verify persistence across a fresh DB session restart
    session_factory = get_session_factory()
    with session_factory() as fresh_db:
        repo = GovernanceRepository(fresh_db)
        persisted_ids = {r.rule_id for r in repo.list_rules()}
        assert "RULE-TERM-201" in persisted_ids

    # 3. Verify GET /api/brand/rules returns both seeded and custom rules
    list_resp = client.get("/api/brand/rules")
    assert list_resp.status_code == 200
    all_ids = {r["rule_id"] for r in list_resp.json()["rules"]}
    assert "RULE-TERM-001" in all_ids  # Seeded
    assert "RULE-TERM-201" in all_ids  # Custom

    # 4. Verify newly ingested rule is enforced by orchestrator in POST /api/audits
    audit_resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-INGEST-TEST",
            "submitted_by_role": "CREATOR",
            "blocks": [
                {
                    "document_block_id": "blk-1",
                    "text": "AURORAGEAR features a quantum-proof security chip.",
                }
            ],
        },
    )
    assert audit_resp.status_code == 201
    flagged_refs = {
        f["evidence_reference"]["reference_id"]
        for f in audit_resp.json()["findings"]
        if f["evidence_reference"] is not None
    }
    assert "RULE-TERM-201" in flagged_refs


def test_create_brand_rule_duplicate_and_invalid_payloads():
    # 1. Duplicate seeded rule_id returns 409 Conflict
    dup_seeded = {
        "rule_id": "RULE-TERM-001",
        "category": "BANNED_TERM",
        "title": "Duplicate Seed Rule",
        "description": "Attempting to overwrite seeded rule.",
        "mandatory_flag": True,
        "severity": "HIGH",
        "pattern_or_target": "guaranteed",
    }
    resp_dup = client.post("/api/brand/rules", json=dup_seeded)
    assert resp_dup.status_code == 409
    assert resp_dup.json()["detail"]["error"] == "DUPLICATE_RULE_ID"

    # 2. Blank fields / invalid category returns 422 Unprocessable Entity
    resp_invalid = client.post(
        "/api/brand/rules",
        json={
            "rule_id": "   ",
            "category": "NOT_A_CATEGORY",
            "title": "a",
            "description": "short",
            "severity": "HIGH",
            "pattern_or_target": "",
        },
    )
    assert resp_invalid.status_code == 422


def test_create_approved_fact_and_participate_in_audit():
    fact_payload = {
        "fact_id": "FACT-WARR-201",
        "topic_key": "warranty_coverage",
        "subject_keywords": ["warranty", "coverage", "years"],
        "canonical_text": "Up to 3 years of limited hardware warranty under standard registration terms.",
        "approved_numeric_value": 3.0,
        "numeric_unit": "years",
        "comparator": "up_to",
        "required_conditions": ["up to", "under standard registration terms"],
        "prohibited_overstatements": ["lifetime", "unconditional"],
        "document_id": "DOC-WARRANTY-V1",
        "document_name": "Approved_Warranty_Terms.csv",
        "verified_page_or_row": 5,
        "version": "1.0",
    }

    # 1. Valid creation returns 201
    resp = client.post("/api/brand/facts", json=fact_payload)
    assert resp.status_code == 201
    assert resp.json()["fact"]["fact_id"] == "FACT-WARR-201"

    # 2. Verify persistence across fresh DB session restart
    session_factory = get_session_factory()
    with session_factory() as fresh_db:
        repo = GovernanceRepository(fresh_db)
        fact_ids = {f.fact_id for f in repo.list_facts()}
        assert "FACT-WARR-201" in fact_ids

    # 3. Verify newly ingested fact is used by ClaimGuard in POST /api/audits
    audit_resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-FACT-TEST",
            "submitted_by_role": "CREATOR",
            "blocks": [
                {
                    "document_block_id": "blk-warr",
                    "text": "AURORAGEAR includes 5 years of warranty coverage.",
                }
            ],
        },
    )
    assert audit_resp.status_code == 201
    cg_findings = [
        f for f in audit_resp.json()["findings"] if f["expert_engine"] == "ClaimGuard"
    ]
    assert len(cg_findings) == 1
    assert cg_findings[0]["verification_status"] == "CONTRADICTED"
    assert cg_findings[0]["evidence_reference"]["reference_id"] == "FACT-WARR-201"


def test_create_approved_fact_duplicate_and_invalid_payloads():
    # 1. Duplicate seeded fact_id returns 409 Conflict
    dup_fact = {
        "fact_id": "FACT-BAT-001",
        "topic_key": "battery_life",
        "subject_keywords": ["battery"],
        "canonical_text": "Duplicate battery fact entry.",
        "approved_numeric_value": 12.0,
        "numeric_unit": "hours",
        "comparator": "up_to",
    }
    resp_dup = client.post("/api/brand/facts", json=dup_fact)
    assert resp_dup.status_code == 409
    assert resp_dup.json()["detail"]["error"] == "DUPLICATE_FACT_ID"

    # 2. Empty subject_keywords or invalid comparator returns 422
    resp_invalid = client.post(
        "/api/brand/facts",
        json={
            "fact_id": "FACT-BAD-01",
            "topic_key": "weight",
            "subject_keywords": ["   "],
            "canonical_text": "Valid canonical text.",
            "approved_numeric_value": 1.5,
            "numeric_unit": "kg",
            "comparator": "invalid_comparator",
        },
    )
    assert resp_invalid.status_code == 422