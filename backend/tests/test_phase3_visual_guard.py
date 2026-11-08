import base64
import io
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_test_image_b64(
    fmt: str = "PNG",
    size: tuple = (80, 80),
    bg_rgb: tuple = (15, 23, 42),
    fg_rgb: tuple = None,
) -> str:
    img = Image.new("RGB", size, color=bg_rgb)
    if fg_rgb is not None:
        for x in range(size[0]):
            for y in range(size[1] // 2, size[1]):
                img.putpixel((x, y), fg_rgb)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def test_visual_guard_valid_compliant_png_and_jpeg():
    # Brand Navy (#0F172A -> 15,23,42) + Crisp White (#FFFFFF -> 255,255,255): 0 Delta E & 17.4:1 contrast
    png_b64 = _create_test_image_b64(fmt="PNG", bg_rgb=(15, 23, 42), fg_rgb=(255, 255, 255))
    resp_png = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-VG-01",
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR portable workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-1",
                "filename": "hero.png",
                "mime_type": "image/png",
                "image_base64": png_b64,
                "alt_text": "AURORAGEAR deep navy portable workstation banner",
            },
        },
    )
    assert resp_png.status_code == 201
    data_png = resp_png.json()
    vg_findings = [f for f in data_png["findings"] if f["expert_engine"] == "VisualGuard"]
    assert len(vg_findings) == 0
    assert data_png["overall_status"] == "READY_FOR_MANAGER_APPROVAL"

    # Valid JPEG with declared foreground/background hex
    jpg_b64 = _create_test_image_b64(fmt="JPEG", bg_rgb=(15, 23, 42))
    resp_jpg = client.post(
        "/api/audits",
        json={
            "campaign_id": "CAMP-VG-02",
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR portable workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-2",
                "filename": "hero.jpg",
                "mime_type": "image/jpeg",
                "image_base64": jpg_b64,
                "alt_text": "AURORAGEAR product promo card",
                "declared_foreground_hex": "#FFFFFF",
                "declared_background_hex": "#0F172A",
            },
        },
    )
    assert resp_jpg.status_code == 201
    assert len([f for f in resp_jpg.json()["findings"] if f["expert_engine"] == "VisualGuard"]) == 0


def test_visual_guard_unsupported_mime_type_and_format_mismatch():
    valid_png = _create_test_image_b64(fmt="PNG")

    # 1. Unsupported MIME type (image/gif)
    resp_gif = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "filename": "anim.gif",
                "mime_type": "image/gif",
                "image_base64": valid_png,
                "alt_text": "Animated product banner",
            },
        },
    )
    assert resp_gif.status_code == 201
    vg_exec = [e for e in resp_gif.json()["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec["execution_state"] == "ERROR"
    assert resp_gif.json()["mandatory_policies_enforced"] is False
    assert resp_gif.json()["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"

    # 2. Declared image/jpeg but actual bytes are PNG
    resp_mismatch = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "filename": "fake.jpg",
                "mime_type": "image/jpeg",
                "image_base64": valid_png,
                "alt_text": "Mismatched header creative",
            },
        },
    )
    assert resp_mismatch.status_code == 201
    vg_exec_mis = [e for e in resp_mismatch.json()["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec_mis["execution_state"] == "ERROR"


def test_visual_guard_corrupted_image_bytes():
    corrupted_b64 = base64.b64encode(b"not-a-valid-png-or-jpeg-stream").decode("utf-8")
    resp = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "filename": "corrupt.png",
                "mime_type": "image/png",
                "image_base64": corrupted_b64,
                "alt_text": "Corrupted creative",
            },
        },
    )
    assert resp.status_code == 201
    vg_exec = [e for e in resp.json()["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec["execution_state"] == "ERROR"
    assert resp.json()["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"


def test_visual_guard_oversized_file_and_decompression_bomb_protection(monkeypatch):
    valid_png = _create_test_image_b64(fmt="PNG", size=(100, 100))

    # 1. Oversized upload byte limit
    monkeypatch.setenv("MAX_IMAGE_UPLOAD_BYTES", "32")
    resp_size = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "filename": "large.png",
                "mime_type": "image/png",
                "image_base64": valid_png,
                "alt_text": "Oversized creative",
            },
        },
    )
    assert resp_size.status_code == 201
    vg_exec_size = [e for e in resp_size.json()["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec_size["execution_state"] == "ERROR"

    # 2. Decompression-bomb pixel count limit (100x100 = 10,000 pixels > 2,500 limit)
    monkeypatch.setenv("MAX_IMAGE_UPLOAD_BYTES", str(5 * 1024 * 1024))
    monkeypatch.setenv("MAX_IMAGE_PIXELS", "2500")
    resp_bomb = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "filename": "bomb.png",
                "mime_type": "image/png",
                "image_base64": valid_png,
                "alt_text": "High pixel count creative",
            },
        },
    )
    assert resp_bomb.status_code == 201
    vg_exec_bomb = [e for e in resp_bomb.json()["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec_bomb["execution_state"] == "ERROR"
    assert "pixel" in resp_bomb.json()["findings"][0]["explanation"].lower()


def test_visual_guard_palette_deviation_alt_text_and_low_contrast():
    # Off-palette neon green (0, 255, 0) + low contrast light green (180, 255, 180) + empty alt_text
    off_brand_png = _create_test_image_b64(fmt="PNG", bg_rgb=(0, 255, 0), fg_rgb=(180, 255, 180))
    resp = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-off",
                "filename": "neon_banner.png",
                "mime_type": "image/png",
                "image_base64": off_brand_png,
                "alt_text": "   ",
            },
        },
    )
    assert resp.status_code == 201
    vg_findings = [f for f in resp.json()["findings"] if f["expert_engine"] == "VisualGuard"]
    assert len(vg_findings) == 3
    combined_explanations = " ".join(f["explanation"] for f in vg_findings)
    assert "alt_text" in combined_explanations
    assert "CIEDE2000" in combined_explanations
    assert "WCAG relative-luminance contrast" in combined_explanations


def test_visual_guard_insufficient_data_when_contrast_regions_unknown():
    # Single solid colour image without declared foreground/background colours -> INSUFFICIENT_DATA
    solid_navy_png = _create_test_image_b64(fmt="PNG", bg_rgb=(15, 23, 42), fg_rgb=None)
    resp = client.post(
        "/api/audits",
        json={
            "blocks": [{"document_block_id": "blk-1", "text": "AURORAGEAR workstation."}],
            "visual_asset": {
                "document_block_id": "blk-img-solid",
                "filename": "solid.png",
                "mime_type": "image/png",
                "image_base64": solid_navy_png,
                "alt_text": "Solid navy background tile",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    vg_exec = [e for e in data["engine_executions"] if e["expert_engine"] == "VisualGuard"][0]
    assert vg_exec["execution_state"] == "INSUFFICIENT_DATA"
    vg_findings = [f for f in data["findings"] if f["expert_engine"] == "VisualGuard"]
    assert len(vg_findings) == 1
    assert vg_findings[0]["execution_state"] == "INSUFFICIENT_DATA"
    assert data["overall_status"] == "ESCALATED_TO_AUTHORISED_REVIEWER"