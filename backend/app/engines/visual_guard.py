import base64
import io
import math
import os
import re
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image, UnidentifiedImageError
from app.core.config import settings
from app.schemas.contracts import (
    VisualAssetInput,
    UnifiedFinding,
    ExecutionState,
    FindingType,
    VerificationStatus,
    Severity,
    AnchorResolutionStatus,
    EvidenceReference,
    EngineExecutionRecord,
    OcrExtractionResult,
    OcrStatus,
)
from app.services.seed_data import get_demo_brand_palette
from app.services.ocr_service import run_tesseract_ocr_on_image

SUPPORTED_MIME_TYPES = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/jpg": "JPEG",
}


def _get_max_upload_bytes() -> int:
    return int(os.getenv("MAX_IMAGE_UPLOAD_BYTES", str(settings.max_image_upload_bytes)))


def _get_max_image_pixels() -> int:
    return int(os.getenv("MAX_IMAGE_PIXELS", str(settings.max_image_pixels)))


def _rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Converts sRGB (0-255) to CIE L*a*b* (D65 illuminant)."""
    def _pivot_rgb(n: float) -> float:
        n /= 255.0
        return ((n + 0.055) / 1.055) ** 2.4 if n > 0.04045 else n / 12.92

    r, g, b = _pivot_rgb(rgb[0]), _pivot_rgb(rgb[1]), _pivot_rgb(rgb[2])
    x = (r * 0.4124564 + g * 0.3575761 + b * 0.1804375) / 0.95047
    y = (r * 0.2126729 + g * 0.7151522 + b * 0.0721750) / 1.00000
    z = (r * 0.0193339 + g * 0.1191920 + b * 0.9503041) / 1.08883

    def _pivot_xyz(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t) + (16.0 / 116.0)

    fx, fy, fz = _pivot_xyz(x), _pivot_xyz(y), _pivot_xyz(z)
    L = (116.0 * fy) - 16.0
    a = 500.0 * (fx - fy)
    b_val = 200.0 * (fy - fz)
    return L, a, b_val


def compute_ciede2000_delta_e(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calculates perceptual colour difference using the CIEDE2000 (Delta E 2000) formula."""
    L1, a1, b1 = _rgb_to_lab(rgb1)
    L2, a2, b2 = _rgb_to_lab(rgb2)

    avg_L = (L1 + L2) / 2.0
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    avg_C = (C1 + C2) / 2.0

    G = 0.5 * (1.0 - math.sqrt((avg_C**7) / ((avg_C**7) + (25.0**7))))
    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)
    avg_Cp = (C1p + C2p) / 2.0

    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0 if C1p != 0 else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0 if C2p != 0 else 0.0

    if C1p * C2p == 0:
        delta_hp = 0.0
    elif abs(h2p - h1p) <= 180.0:
        delta_hp = h2p - h1p
    elif h2p - h1p > 180.0:
        delta_hp = (h2p - h1p) - 360.0
    else:
        delta_hp = (h2p - h1p) + 360.0

    delta_Lp = L2 - L1
    delta_Cp = C2p - C1p
    delta_Hp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(delta_hp / 2.0))

    if C1p * C2p == 0:
        avg_hp = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        avg_hp = (h1p + h2p) / 2.0
    elif (h1p + h2p) < 360.0:
        avg_hp = (h1p + h2p + 360.0) / 2.0
    else:
        avg_hp = (h1p + h2p - 360.0) / 2.0

    T = (
        1.0
        - 0.17 * math.cos(math.radians(avg_hp - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * avg_hp))
        + 0.32 * math.cos(math.radians(3.0 * avg_hp + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * avg_hp - 63.0))
    )

    delta_ro = 30.0 * math.exp(-(((avg_hp - 275.0) / 25.0) ** 2))
    R_C = 2.0 * math.sqrt((avg_Cp**7) / ((avg_Cp**7) + (25.0**7)))
    S_L = 1.0 + ((0.015 * ((avg_L - 50.0) ** 2)) / math.sqrt(20.0 + ((avg_L - 50.0) ** 2)))
    S_C = 1.0 + 0.045 * avg_Cp
    S_H = 1.0 + 0.015 * avg_Cp * T
    R_T = -math.sin(math.radians(2.0 * delta_ro)) * R_C

    delta_E = math.sqrt(
        (delta_Lp / S_L) ** 2
        + (delta_Cp / S_C) ** 2
        + (delta_Hp / S_H) ** 2
        + R_T * (delta_Cp / S_C) * (delta_Hp / S_H)
    )
    return round(delta_E, 2)


def compute_wcag_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calculates WCAG 2.1 relative-luminance contrast ratio between two RGB colours."""
    def _rel_lum(rgb: Tuple[int, int, int]) -> float:
        channels = []
        for c in rgb:
            v = c / 255.0
            channels.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    l1 = _rel_lum(rgb1)
    l2 = _rel_lum(rgb2)
    brightest = max(l1, l2)
    darkest = min(l1, l2)
    return round((brightest + 0.05) / (darkest + 0.05), 2)


def _parse_hex_color(hex_str: Optional[str]) -> Optional[Tuple[int, int, int]]:
    if not hex_str:
        return None
    match = re.match(r"^#?([0-9a-fA-F]{6})$", hex_str.strip())
    if not match:
        return None
    h = match.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def run_visual_guard_baseline(
    visual_asset: Optional[VisualAssetInput],
    fallback_alt_text: Optional[str] = None,
    brand_palette: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[UnifiedFinding], EngineExecutionRecord]:
    if visual_asset is None:
        return [], EngineExecutionRecord(
            expert_engine="VisualGuard",
            mandatory_enforced=True,
            execution_state=ExecutionState.NOT_APPLICABLE,
            findings_count=0,
            notes="No static visual asset submitted in this audit request.",
        )

    max_bytes = _get_max_upload_bytes()
    max_pixels = _get_max_image_pixels()
    findings: List[UnifiedFinding] = []
    finding_counter = 1
    block_id = visual_asset.document_block_id or "blk-visual-asset-01"

    # 1. Validate declared MIME type
    mime_lower = visual_asset.mime_type.strip().lower()
    if mime_lower not in SUPPORTED_MIME_TYPES:
        findings.append(
            UnifiedFinding(
                finding_id=f"FND-VG-{finding_counter:04d}",
                expert_engine="VisualGuard",
                execution_state=ExecutionState.ERROR,
                finding_type=FindingType.VISUAL_A11Y_SUBSET,
                severity=Severity.HIGH,
                verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                document_block_id=block_id,
                matched_text=visual_asset.filename,
                anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                explanation=(
                    f"Unsupported image MIME type '{visual_asset.mime_type}'. "
                    "VisualGuard baseline supports only static PNG and JPG/JPEG images."
                ),
                evidence_reference=None,
                rewrite_candidate=None,
                human_review_required=True,
            )
        )
        return findings, EngineExecutionRecord(
            expert_engine="VisualGuard",
            mandatory_enforced=False,
            execution_state=ExecutionState.ERROR,
            findings_count=len(findings),
            notes=f"Rejected unsupported MIME type: {visual_asset.mime_type}",
        )

    # 2. Safely decode Base64 in memory without writing temporary files
    try:
        raw_bytes = base64.b64decode(visual_asset.image_base64, validate=True)
    except Exception:
        findings.append(
            UnifiedFinding(
                finding_id=f"FND-VG-{finding_counter:04d}",
                expert_engine="VisualGuard",
                execution_state=ExecutionState.ERROR,
                finding_type=FindingType.VISUAL_A11Y_SUBSET,
                severity=Severity.HIGH,
                verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                document_block_id=block_id,
                matched_text=visual_asset.filename,
                anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                explanation="Invalid or corrupted base64 image payload.",
                evidence_reference=None,
                rewrite_candidate=None,
                human_review_required=True,
            )
        )
        return findings, EngineExecutionRecord(
            expert_engine="VisualGuard",
            mandatory_enforced=False,
            execution_state=ExecutionState.ERROR,
            findings_count=len(findings),
            notes="Corrupted base64 image payload.",
        )

    # 3. Enforce maximum upload byte size
    if len(raw_bytes) > max_bytes:
        findings.append(
            UnifiedFinding(
                finding_id=f"FND-VG-{finding_counter:04d}",
                expert_engine="VisualGuard",
                execution_state=ExecutionState.ERROR,
                finding_type=FindingType.VISUAL_A11Y_SUBSET,
                severity=Severity.HIGH,
                verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                document_block_id=block_id,
                matched_text=visual_asset.filename,
                anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                explanation=(
                    f"Image size ({len(raw_bytes)} bytes) exceeds maximum allowed upload limit ({max_bytes} bytes)."
                ),
                evidence_reference=None,
                rewrite_candidate=None,
                human_review_required=True,
            )
        )
        return findings, EngineExecutionRecord(
            expert_engine="VisualGuard",
            mandatory_enforced=False,
            execution_state=ExecutionState.ERROR,
            findings_count=len(findings),
            notes="Oversized image upload rejected.",
        )

    # 4. Validate actual image format & guard against decompression bombs WITHOUT mutating global Image.MAX_IMAGE_PIXELS
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img_verify:
            actual_format = (img_verify.format or "").upper()
            width, height = img_verify.size
            if width <= 0 or height <= 0 or (width * height) > max_pixels:
                raise ValueError(
                    f"Image dimensions ({width}x{height} = {width * height} pixels) exceed decompression-bomb safety limit ({max_pixels} pixels)."
                )
            img_verify.verify()

        expected_format = SUPPORTED_MIME_TYPES[mime_lower]
        if actual_format != expected_format:
            raise ValueError(
                f"Declared MIME type '{visual_asset.mime_type}' does not match actual image format '{actual_format}'."
            )

        with Image.open(io.BytesIO(raw_bytes)) as img:
            if (img.size[0] * img.size[1]) > max_pixels:
                raise ValueError("Image pixel count exceeds safety limit.")
            rgb_img = img.convert("RGB")
            total_pixels = width * height
            colors = rgb_img.getcolors(maxcolors=65536)
            ocr_requested = (
                visual_asset.enable_ocr
                if visual_asset.enable_ocr is not None
                else (os.getenv("VISUALGUARD_OCR_ENABLED", str(settings.visualguard_ocr_enabled)).lower() == "true")
            )
            ocr_result: Optional[OcrExtractionResult] = None
            if ocr_requested:
                ocr_result = run_tesseract_ocr_on_image(
                    rgb_image=rgb_img,
                    min_confidence_threshold=visual_asset.ocr_min_confidence,
                )
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as exc:
        findings.append(
            UnifiedFinding(
                finding_id=f"FND-VG-{finding_counter:04d}",
                expert_engine="VisualGuard",
                execution_state=ExecutionState.ERROR,
                finding_type=FindingType.VISUAL_A11Y_SUBSET,
                severity=Severity.HIGH,
                verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                document_block_id=block_id,
                matched_text=visual_asset.filename,
                anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                explanation=f"Image validation failed: {str(exc)}",
                evidence_reference=None,
                rewrite_candidate=None,
                human_review_required=True,
            )
        )
        return findings, EngineExecutionRecord(
            expert_engine="VisualGuard",
            mandatory_enforced=False,
            execution_state=ExecutionState.ERROR,
            findings_count=len(findings),
            notes=f"Image validation error: {str(exc)}",
        )

    # 5. Validate meaningful alt_text metadata
    effective_alt = visual_asset.alt_text if visual_asset.alt_text is not None else fallback_alt_text
    if not effective_alt or len(effective_alt.strip()) < 5:
        findings.append(
            UnifiedFinding(
                finding_id=f"FND-VG-{finding_counter:04d}",
                expert_engine="VisualGuard",
                execution_state=ExecutionState.OK,
                finding_type=FindingType.VISUAL_A11Y_SUBSET,
                severity=Severity.MEDIUM,
                verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                document_block_id=block_id,
                matched_text=visual_asset.filename,
                anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                explanation=(
                    "Missing or non-meaningful alt_text metadata supplied for static image creative. "
                    "Provide descriptive alt_text (at least 5 characters) for publishing platform accessibility."
                ),
                evidence_reference=EvidenceReference(
                    source_type="BRAND_RULE",
                    reference_id="RULE-A11Y-ALT-001",
                    document_id="DOC-BRAND-CONSTITUTION-V1",
                    document_name="Sample_Brand_Guidelines_v1.pdf",
                    verified_page_or_row=7,
                    canonical_excerpt_from_db="All static visual assets must include descriptive alt_text metadata prior to publication.",
                ),
                rewrite_candidate=None,
                human_review_required=True,
            )
        )
        finding_counter += 1

    # 6. Extract dominant colours & compare against brand palette via CIEDE2000 Delta E
    palette = brand_palette if brand_palette is not None else get_demo_brand_palette()
    overall_engine_state = ExecutionState.OK

    if colors is None:
        # High-colour image (> 65,536 unique colours) -> explicitly report INSUFFICIENT_DATA instead of silently skipping
        overall_engine_state = ExecutionState.INSUFFICIENT_DATA
        sorted_colors = []
        findings.append(
            UnifiedFinding(
                finding_id=f"FND-VG-{finding_counter:04d}",
                expert_engine="VisualGuard",
                execution_state=ExecutionState.INSUFFICIENT_DATA,
                finding_type=FindingType.VISUAL_A11Y_SUBSET,
                severity=Severity.LOW,
                verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                document_block_id=block_id,
                matched_text=visual_asset.filename,
                anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                explanation=(
                    "Image contains more than 65,536 unique colours (complex photograph or continuous gradient). "
                    "Exact dominant-colour palette comparison marked INSUFFICIENT_DATA for human visual review."
                ),
                evidence_reference=None,
                rewrite_candidate=None,
                human_review_required=True,
            )
        )
        finding_counter += 1
    else:
        
        sorted_colors = sorted(colors, key=lambda item: item[0], reverse=True)

        if sorted_colors and palette:
            highest_frequency = sorted_colors[0][0]
            top_colors = [
                rgb
                for count, rgb in sorted_colors
                if count == highest_frequency
            ]

            dom_rgb = min(
                top_colors,
                key=lambda candidate: min(
                    compute_ciede2000_delta_e(candidate, pal["rgb"])
                    for pal in palette
                ),
            )

            dom_hex = _rgb_to_hex(dom_rgb)
            best_match: Optional[Dict[str, Any]] = None
            min_delta_e = float("inf")

            for pal in palette:
                de = compute_ciede2000_delta_e(dom_rgb, pal["rgb"])
                if de < min_delta_e:
                    min_delta_e = de
                    best_match = pal
                    
            assert best_match is not None
            if min_delta_e > best_match["max_delta_e"]:
                findings.append(
                    UnifiedFinding(
                        finding_id=f"FND-VG-{finding_counter:04d}",
                        expert_engine="VisualGuard",
                        execution_state=ExecutionState.OK,
                        finding_type=FindingType.VISUAL_A11Y_SUBSET,
                        severity=Severity.MEDIUM,
                        verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                        document_block_id=block_id,
                        matched_text=dom_hex,
                        anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                        explanation=(
                            f"Dominant image colour {dom_hex} deviates from closest approved brand palette colour "
                            f"{best_match['name']} ({best_match['hex']}) with CIEDE2000 ΔE = {min_delta_e} "
                            f"(maximum allowed ΔE = {best_match['max_delta_e']})."
                        ),
                        evidence_reference=EvidenceReference(
                            source_type="BRAND_PALETTE",
                            reference_id=best_match["palette_id"],
                            document_id=best_match["document_id"],
                            document_name=best_match["document_name"],
                            verified_page_or_row=best_match["verified_page_or_row"],
                            canonical_excerpt_from_db=(
                                f"Approved palette colour {best_match['name']} ({best_match['hex']}), "
                                f"maximum perceptual distance CIEDE2000 ΔE <= {best_match['max_delta_e']}."
                            ),
                        ),
                        rewrite_candidate=None,
                        human_review_required=True,
                    )
                )
                finding_counter += 1

    # 7. WCAG Relative-Luminance Contrast Check (Only when fg/bg colours are reliably known)
    fg_rgb = _parse_hex_color(visual_asset.declared_foreground_hex)
    bg_rgb = _parse_hex_color(visual_asset.declared_background_hex)

    # If not explicitly provided, only infer when the image has two distinct dominant colours covering >= 90% of pixels
    if fg_rgb is None or bg_rgb is None:
        if sorted_colors and len(sorted_colors) >= 2:
            top_two_ratio = (sorted_colors[0][0] + sorted_colors[1][0]) / float(total_pixels)
            if top_two_ratio >= 0.90 and sorted_colors[0][1] != sorted_colors[1][1]:
                bg_rgb = sorted_colors[0][1]
                fg_rgb = sorted_colors[1][1]

    if fg_rgb is not None and bg_rgb is not None:
        contrast_ratio = compute_wcag_contrast_ratio(fg_rgb, bg_rgb)
        if contrast_ratio < 4.5:
            findings.append(
                UnifiedFinding(
                    finding_id=f"FND-VG-{finding_counter:04d}",
                    expert_engine="VisualGuard",
                    execution_state=ExecutionState.OK,
                    finding_type=FindingType.VISUAL_A11Y_SUBSET,
                    severity=Severity.HIGH,
                    verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                    document_block_id=block_id,
                    matched_text=f"{_rgb_to_hex(fg_rgb)} on {_rgb_to_hex(bg_rgb)}",
                    anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                    explanation=(
                        f"WCAG relative-luminance contrast ratio between {_rgb_to_hex(fg_rgb)} and "
                        f"{_rgb_to_hex(bg_rgb)} is {contrast_ratio}:1, below the WCAG AA 4.5:1 minimum threshold."
                    ),
                    evidence_reference=EvidenceReference(
                        source_type="BRAND_RULE",
                        reference_id="RULE-A11Y-CONTRAST-001",
                        document_id="DOC-BRAND-CONSTITUTION-V1",
                        document_name="Sample_Brand_Guidelines_v1.pdf",
                        verified_page_or_row=8,
                        canonical_excerpt_from_db=(
                            "Text-to-background relative luminance contrast must meet WCAG AA minimum 4.5:1 "
                            "where foreground and background colours are reliably known."
                        ),
                    ),
                    rewrite_candidate=None,
                    human_review_required=True,
                )
            )
            finding_counter += 1
    else:
        overall_engine_state = ExecutionState.INSUFFICIENT_DATA
        findings.append(
            UnifiedFinding(
                finding_id=f"FND-VG-{finding_counter:04d}",
                expert_engine="VisualGuard",
                execution_state=ExecutionState.INSUFFICIENT_DATA,
                finding_type=FindingType.VISUAL_A11Y_SUBSET,
                severity=Severity.LOW,
                verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                document_block_id=block_id,
                matched_text=visual_asset.filename,
                anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                explanation=(
                    "Foreground and background colours could not be reliably isolated from this image "
                    "(single-tone, gradient, or multi-colour creative without declared region colours). "
                    "WCAG contrast check returned INSUFFICIENT_DATA for human visual review."
                ),
                evidence_reference=None,
                rewrite_candidate=None,
                human_review_required=True,
            )
        )
        finding_counter += 1
       
    # 8. Evaluate OCR extraction status (preserving palette & contrast checks above even if OCR fails)
    if ocr_result is not None:
        if ocr_result.ocr_status == OcrStatus.OCR_UNAVAILABLE:
            overall_engine_state = ExecutionState.INSUFFICIENT_DATA
            findings.append(
                UnifiedFinding(
                    finding_id=f"FND-VG-{finding_counter:04d}",
                    expert_engine="VisualGuard",
                    execution_state=ExecutionState.INSUFFICIENT_DATA,
                    finding_type=FindingType.VISUAL_A11Y_SUBSET,
                    severity=Severity.MEDIUM,
                    verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                    document_block_id=block_id,
                    matched_text=visual_asset.filename,
                    anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                    explanation=(
                        "Tesseract OCR executable is unavailable or misconfigured; embedded image text "
                        "could not be audited automatically. Escalated as INSUFFICIENT_DATA for human review."
                    ),
                    evidence_reference=None,
                    rewrite_candidate=None,
                    human_review_required=True,
                )
            )
            finding_counter += 1
        elif ocr_result.ocr_status == OcrStatus.OCR_FAILED:
            overall_engine_state = ExecutionState.ERROR
            findings.append(
                UnifiedFinding(
                    finding_id=f"FND-VG-{finding_counter:04d}",
                    expert_engine="VisualGuard",
                    execution_state=ExecutionState.ERROR,
                    finding_type=FindingType.VISUAL_A11Y_SUBSET,
                    severity=Severity.HIGH,
                    verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                    document_block_id=block_id,
                    matched_text=visual_asset.filename,
                    anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                    explanation=(
                        f"Tesseract OCR failed while inspecting '{visual_asset.filename}'. "
                        "Visual text audit could not be completed; escalated for human review."
                    ),
                    evidence_reference=None,
                    rewrite_candidate=None,
                    human_review_required=True,
                )
            )
            finding_counter += 1
        elif ocr_result.ocr_status == OcrStatus.OCR_LOW_CONFIDENCE:
            if overall_engine_state == ExecutionState.OK:
                overall_engine_state = ExecutionState.INSUFFICIENT_DATA
            findings.append(
                UnifiedFinding(
                    finding_id=f"FND-VG-{finding_counter:04d}",
                    expert_engine="VisualGuard",
                    execution_state=ExecutionState.INSUFFICIENT_DATA,
                    finding_type=FindingType.VISUAL_A11Y_SUBSET,
                    severity=Severity.MEDIUM,
                    verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                    document_block_id=block_id,
                    matched_text=visual_asset.filename,
                    anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                    explanation=(
                        f"Low-confidence OCR extraction (mean confidence {ocr_result.mean_confidence}% < "
                        f"{ocr_result.min_confidence_threshold}% threshold). Definitive policy findings "
                        "were not generated from uncertain OCR text; manual human review required."
                    ),
                    evidence_reference=None,
                    rewrite_candidate=None,
                    human_review_required=True,
                )
            )
            finding_counter += 1
        elif ocr_result.ocr_status == OcrStatus.OCR_SUCCESS and ocr_result.prompt_injection_signals_detected:
            findings.append(
                UnifiedFinding(
                    finding_id=f"FND-VG-{finding_counter:04d}",
                    expert_engine="VisualGuard",
                    execution_state=ExecutionState.OK,
                    finding_type=FindingType.VISUAL_A11Y_SUBSET,
                    severity=Severity.HIGH,
                    verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                    document_block_id=block_id,
                    matched_text=visual_asset.filename,
                    anchor_resolution_status=AnchorResolutionStatus.UNRESOLVED_SIDEBAR_ONLY,
                    explanation=(
                        "PromptShield alert: Potential instruction-override / prompt-injection phrasing "
                        "detected inside OCR-extracted image text. Isolated as untrusted data."
                    ),
                    evidence_reference=None,
                    rewrite_candidate=None,
                    human_review_required=True,
                )
            )
            finding_counter += 1

    # Store the latest OCR result on the execution record notes or via attribute for orchestrator consumption
    exec_record = EngineExecutionRecord(
        expert_engine="VisualGuard",
        mandatory_enforced=(overall_engine_state != ExecutionState.ERROR),
        execution_state=overall_engine_state,
        findings_count=len(findings),
        notes=(
            f"Deterministic image validation, CIEDE2000 palette, alt-text, and WCAG contrast executed. "
            f"OCR status: {ocr_result.ocr_status.value if ocr_result else 'NOT_REQUESTED'}."
        ),
    )
    return findings, exec_record

def run_visual_guard_with_ocr_metadata(
    visual_asset: Optional[VisualAssetInput],
    fallback_alt_text: Optional[str] = None,
    brand_palette: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[UnifiedFinding], EngineExecutionRecord, Optional[OcrExtractionResult]]:
    findings, exec_record = run_visual_guard_baseline(
        visual_asset=visual_asset,
        fallback_alt_text=fallback_alt_text,
        brand_palette=brand_palette,
    )
    if visual_asset is None or exec_record.execution_state == ExecutionState.ERROR and not any(
        "Tesseract OCR failed" in f.explanation for f in findings
    ):
        return findings, exec_record, None

    ocr_requested = (
        visual_asset.enable_ocr
        if visual_asset.enable_ocr is not None
        else (os.getenv("VISUALGUARD_OCR_ENABLED", str(settings.visualguard_ocr_enabled)).lower() == "true")
    )
    if not ocr_requested:
        return findings, exec_record, None

    raw_bytes = base64.b64decode(visual_asset.image_base64, validate=True)
    with Image.open(io.BytesIO(raw_bytes)) as img:
        rgb_img = img.convert("RGB")
        ocr_res = run_tesseract_ocr_on_image(
            rgb_image=rgb_img,
            min_confidence_threshold=visual_asset.ocr_min_confidence,
        )
    return findings, exec_record, ocr_res