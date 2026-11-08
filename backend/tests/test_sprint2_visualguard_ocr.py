import base64
import io
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
import app.services.ocr_service as ocr_module

client = TestClient(app)


def _make_banner_png_b64(bg_rgb=(15, 23, 42), fg_rgb=(255, 255, 255), size=(120, 60)) -> str:
    img = Image.new("RGB", size, color=bg_rgb)
    for x in range(size[0]):
        for y in range(size[1] // 2, size[1]):
            img.putpixel((x, y), fg_rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _mock_tesseract_data(tokens_with_conf: list[tuple[str, float]]):
    return {
        "text": [t for t, _ in tokens_with_conf],
        "conf": [c for _, c in tokens_with_conf],
        "left": [10 * (i + 1) for i in range(len(tokens_with_conf))],
        "top": [20 for _ in tokens_with_conf],
        "width": [45 for _ in tokens_with_conf],
        "height": [18 for _ in tokens_with_conf],
    }


def test_1_successful_ocr_extraction_and_metadata(monkeypatch):
    def _fake_image_to_data(img, output_type=None):
        return _mock_tesseract_data(
            [("AURORAGEAR", 94.0), ("portable", 91.0), ("workstation.", 95.0)]
        )

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _fake_image_to_data)
    img = Image.new("RGB", (120, 60), color=(15, 23, 42))
    res = ocr_module.run_tesseract_ocr_on_image(img, min_confidence_threshold=60.0)

    assert res.ocr_status.value == "OCR_SUCCESS"
    assert res.image_width == 120
    assert res.image_height == 60
    assert res.extracted_text == "AURORAGEAR portable workstation."
    assert res.mean_confidence == 93.33
    assert res.regions_count == 3
    assert res.governance_evaluated is True


def test_2_image_containing_no_text_returns_ocr_no_text_detected(monkeypatch):
    def _fake_empty_ocr(img, output_type=None):
        return _mock_tesseract_data([("", -1.0), ("   ", -1.0)])

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _fake_empty_ocr)
    banner_b64 = _make_banner_png_b64()

    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-OCR-EMPTY",
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-empty",
                "filename": "clean_bg.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "Clean navy and white background graphic",
                "enable_ocr": True,
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ai_disclosure_log"]["ocr_telemetry"]["ocr_status"] == "OCR_NO_TEXT_DETECTED"
    assert data["overall_status"] == "READY_FOR_MANAGER_APPROVAL"


def test_3_and_4_low_confidence_ocr_does_not_generate_definitive_policy_violations(monkeypatch):
    # Even though tokens contain banned word 'guaranteed' and wrong casing 'AuroraGear',
    # mean confidence is 35.0% (< 60.0% threshold). Must NOT emit definitive RuleGuard/ClaimGuard
    # violations from unreliable OCR; must emit INSUFFICIENT_DATA finding for human review!
    def _fake_low_conf_ocr(img, output_type=None):
        return _mock_tesseract_data(
            [("AuroraGear", 32.0), ("guaranteed", 38.0), ("24", 35.0), ("hours", 35.0)]
        )

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _fake_low_conf_ocr)
    banner_b64 = _make_banner_png_b64()

    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-OCR-LOWCONF",
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-blurry",
                "filename": "blurry.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "Blurry product teaser graphic",
                "enable_ocr": True,
                "ocr_min_confidence": 60.0,
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["ai_disclosure_log"]["ocr_telemetry"]["ocr_status"] == "OCR_LOW_CONFIDENCE"
    assert data["ai_disclosure_log"]["ocr_telemetry"]["governance_evaluated"] is False
    assert data["mandatory_policies_enforced"] is False
    assert data["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"

    # Verify no definitive RuleGuard findings were generated on the OCR block
    ocr_rg_findings = [
        f for f in data["findings"] if f["document_block_id"] == "blk-img-blurry:ocr"
    ]
    assert len(ocr_rg_findings) == 0

    # Verify VisualGuard emitted an INSUFFICIENT_DATA finding explaining low OCR confidence
    vg_findings = [f for f in data["findings"] if f["expert_engine"] == "VisualGuard"]
    assert any(
        f["execution_state"] == "INSUFFICIENT_DATA" and "Low-confidence OCR" in f["explanation"]
        for f in vg_findings
    )


def test_5_invalid_or_corrupted_image_rejected_before_ocr():
    corrupt_b64 = base64.b64encode(b"corrupted-non-image-binary-payload").decode("utf-8")
    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-OCR-CORRUPT",
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "filename": "corrupt.png",
                "mime_type": "image/png",
                "image_base64": corrupt_b64,
                "alt_text": "Corrupt image file",
                "enable_ocr": True,
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    vg_exec = [e for e in data["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec["execution_state"] == "ERROR"
    assert data["mandatory_policies_enforced"] is False
    assert data["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"


def test_6_and_11_tesseract_unavailable_or_failed_is_not_reported_as_clean_audit(monkeypatch):
    # 1. Simulate TesseractNotFoundError (binary not installed on host)
    def _raise_not_found(img, output_type=None):
        raise ocr_module.TesseractNotFoundError()

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _raise_not_found)
    banner_b64 = _make_banner_png_b64()

    resp_unavail = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-OCR-UNAVAIL",
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-unavail",
                "filename": "banner.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "AURORAGEAR banner image",
                "enable_ocr": True,
            },
        },
    )
    assert resp_unavail.status_code == 201
    data_unavail = resp_unavail.json()
    assert data_unavail["ai_disclosure_log"]["ocr_telemetry"]["ocr_status"] == "OCR_UNAVAILABLE"
    assert data_unavail["mandatory_policies_enforced"] is False
    assert data_unavail["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"

    # 2. Simulate runtime OCR engine crash
    def _raise_runtime_err(img, output_type=None):
        raise RuntimeError("Simulated Tesseract crash")

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _raise_runtime_err)
    resp_fail = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-OCR-FAIL",
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-fail",
                "filename": "banner.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "AURORAGEAR banner image",
                "enable_ocr": True,
            },
        },
    )
    assert resp_fail.status_code == 201
    data_fail = resp_fail.json()
    assert data_fail["ai_disclosure_log"]["ocr_telemetry"]["ocr_status"] == "OCR_FAILED"
    vg_exec = [e for e in data_fail["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec["execution_state"] == "ERROR"
    assert data_fail["mandatory_policies_enforced"] is False
    assert data_fail["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"


def test_7_governance_checks_run_on_high_confidence_ocr_text(monkeypatch):
    # High-confidence OCR text containing:
    # - Brand casing violation ('AuroraGear') -> RuleGuard
    # - Banned term ('guaranteed') -> RuleGuard
    # - Contradicted battery claim ('24 hours of battery life') -> ClaimGuard
    # - Aggressive tone ('crush the competition!!') -> VoiceGuard
    # - Sensitive email ('secret@auroragear.example.com') -> Privacy Gate
    def _fake_violation_ocr(img, output_type=None):
        return _mock_tesseract_data(
            [
                ("AuroraGear", 92.0),
                ("delivers", 95.0),
                ("24", 96.0),
                ("hours", 94.0),
                ("of", 98.0),
                ("guaranteed", 91.0),
                ("battery", 95.0),
                ("life", 95.0),
                ("to", 97.0),
                ("crush", 90.0),
                ("the", 98.0),
                ("competition!!", 89.0),
                ("Contact", 93.0),
                ("secret@auroragear.example.com", 90.0),
            ]
        )

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _fake_violation_ocr)
    banner_b64 = _make_banner_png_b64()

    resp = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-OCR-GOV",
            "blocks": [{"document_block_id": "blk-clean-copy", "text": "AURORAGEAR portable workstation."}],
            "visual_asset": {
                "document_block_id": "blk-banner-01",
                "filename": "promo_banner.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "Promotional workstation banner",
                "enable_ocr": True,
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    ocr_findings = [
        f for f in data["findings"] if f["document_block_id"] == "blk-banner-01:ocr"
    ]
    engines_on_ocr = {f["expert_engine"] for f in ocr_findings}
    assert "RuleGuard" in engines_on_ocr
    assert "ClaimGuard" in engines_on_ocr
    assert "VoiceGuard" in engines_on_ocr

    # Verify ClaimGuard flagged the 24-hour OCR claim as CONTRADICTED
    cg_ocr = [f for f in ocr_findings if f["expert_engine"] == "ClaimGuard"][0]
    assert cg_ocr["verification_status"] == "CONTRADICTED"

    # Verify Privacy Gate scanned the OCR block and masked the email without logging raw email text
    disclosure = data["ai_disclosure_log"]
    assert disclosure["sensitive_matches_masked_count"] >= 1
    assert "email" in disclosure["sensitive_categories_detected"]
    assert "secret@auroragear.example.com" not in str(disclosure)


def test_8_ocr_text_never_becomes_an_approved_fact_automatically(monkeypatch):
    def _fake_new_claim_ocr(img, output_type=None):
        return _mock_tesseract_data(
            [("Certified", 95.0), ("to", 95.0), ("survive", 95.0), ("9999", 95.0), ("meters", 95.0), ("depth.", 95.0)]
        )

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _fake_new_claim_ocr)
    facts_before = len(client.get("/api/brand/facts").json()["facts"])

    banner_b64 = _make_banner_png_b64()
    resp = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "b1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-unbacked",
                "filename": "depth.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "Depth rating graphic",
                "enable_ocr": True,
            },
        },
    )
    assert resp.status_code == 201
    facts_after = len(client.get("/api/brand/facts").json()["facts"])
    assert facts_after == facts_before

    # Moreover, the unbacked OCR claim must be flagged as UNVERIFIABLE
    cg_findings = [
        f for f in resp.json()["findings"]
        if f["expert_engine"] == "ClaimGuard" and f["document_block_id"] == "blk-img-unbacked:ocr"
    ]
    assert len(cg_findings) == 1
    assert cg_findings[0]["verification_status"] == "UNVERIFIABLE"


def test_9_tenant_isolation_preserved_for_ocr_governance_checks(monkeypatch):
    org_a = {"X-Demo-Org-Id": "ORG-OCR-TENANT-A"}
    org_b = {"X-Demo-Org-Id": "ORG-OCR-TENANT-B"}

    # Add banned term 'starlight' ONLY in ORG-OCR-TENANT-A
    client.post(
        "/api/brand/rules",
        headers=org_a,
        json={
            "rule_id": "RULE-OCR-A-01",
            "category": "BANNED_TERM",
            "title": "Ban starlight in Org A",
            "description": "Never use 'starlight' in Org A visuals.",
            "mandatory_flag": True,
            "severity": "HIGH",
            "pattern_or_target": "starlight",
        },
    )

    def _fake_starlight_ocr(img, output_type=None):
        return _mock_tesseract_data([("Introducing", 95.0), ("starlight", 94.0), ("edition", 96.0)])

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _fake_starlight_ocr)
    banner_b64 = _make_banner_png_b64()

    # Audit in Org A flags 'starlight' inside the image
    resp_a = client.post(
        "/api/audits",
        headers=org_a,
        json={
            "blocks": [{"document_block_id": "b1", "text": "Clean text."}],
            "visual_asset": {
                "document_block_id": "blk-img-a",
                "filename": "a.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "Starlight banner",
                "enable_ocr": True,
            },
        },
    ).json()
    assert any(
        f["evidence_reference"] and f["evidence_reference"]["reference_id"] == "RULE-OCR-A-01"
        for f in resp_a["findings"]
    )

    # Audit in Org B with the exact same image does NOT trigger Org A's rule
    resp_b = client.post(
        "/api/audits",
        headers=org_b,
        json={
            "blocks": [{"document_block_id": "b1", "text": "Clean text."}],
            "visual_asset": {
                "document_block_id": "blk-img-b",
                "filename": "b.png",
                "mime_type": "image/png",
                "image_base64": banner_b64,
                "alt_text": "Starlight banner",
                "enable_ocr": True,
            },
        },
    ).json()
    assert not any(
        f["evidence_reference"] and f["evidence_reference"]["reference_id"] == "RULE-OCR-A-01"
        for f in resp_b["findings"]
    )


def test_10_existing_palette_and_contrast_checks_remain_intact_when_ocr_unavailable(monkeypatch):
    def _raise_not_found(img, output_type=None):
        raise ocr_module.TesseractNotFoundError()

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_data", _raise_not_found)

    # Off-palette neon magenta (255, 0, 255) + low contrast light pink (255, 190, 255) + missing alt_text
    bad_banner_b64 = _make_banner_png_b64(bg_rgb=(255, 0, 255), fg_rgb=(255, 190, 255))
    resp = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "b1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-bad",
                "filename": "bad.png",
                "mime_type": "image/png",
                "image_base64": bad_banner_b64,
                "alt_text": "",
                "enable_ocr": True,
            },
        },
    )
    assert resp.status_code == 201
    vg_explanations = " | ".join(
        f["explanation"] for f in resp.json()["findings"] if f["expert_engine"] == "VisualGuard"
    )
    assert "alt_text" in vg_explanations
    assert "CIEDE2000" in vg_explanations
    assert "WCAG relative-luminance contrast" in vg_explanations
    assert "Tesseract OCR executable is unavailable" in vg_explanations