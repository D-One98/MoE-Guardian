import os
import shutil
import unicodedata
from typing import Optional
from PIL import Image
from app.core.config import settings
from app.schemas.contracts import (
    OcrExtractionResult,
    OcrStatus,
    OcrTextRegion,
)
from app.services.ingestion_service import PROMPT_INJECTION_PATTERNS

try:
    import pytesseract
    from pytesseract import Output as PyTesseractOutput
    from pytesseract import TesseractNotFoundError, TesseractError
    PYTESSERACT_IMPORTED = True
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore
    PyTesseractOutput = None  # type: ignore
    TesseractNotFoundError = Exception  # type: ignore
    TesseractError = Exception  # type: ignore
    PYTESSERACT_IMPORTED = False


def _canonicalise_ocr_text(raw: str) -> str:
    norm = unicodedata.normalize("NFKC", raw)
    return "".join(ch for ch in norm if ch in ("\n", "\t") or ord(ch) >= 32).strip()


def _resolve_tesseract_cmd() -> Optional[str]:
    """
    Resolves the Tesseract executable path from environment/config (`TESSERACT_CMD`)
    or system PATH without hardcoding machine-specific OS paths.
    """
    configured_cmd = os.getenv("TESSERACT_CMD", settings.tesseract_cmd).strip()
    if configured_cmd:
        return configured_cmd
    return shutil.which("tesseract")


def run_tesseract_ocr_on_image(
    rgb_image: Image.Image,
    min_confidence_threshold: Optional[float] = None,
) -> OcrExtractionResult:
    """
    Extracts visible text and bounding-box confidence telemetry from an in-memory PIL Image.
    - Never writes temporary files to disk.
    - Never logs raw sensitive OCR text.
    - Clearly distinguishes OCR_UNAVAILABLE, OCR_FAILED, OCR_NO_TEXT_DETECTED,
      OCR_LOW_CONFIDENCE, and OCR_SUCCESS.
    """
    width, height = rgb_image.size
    threshold = (
        min_confidence_threshold
        if min_confidence_threshold is not None
        else float(os.getenv("OCR_MIN_CONFIDENCE", str(settings.ocr_min_confidence)))
    )

    if not PYTESSERACT_IMPORTED or pytesseract is None:
        return OcrExtractionResult(
            ocr_status=OcrStatus.OCR_UNAVAILABLE,
            image_width=width,
            image_height=height,
            min_confidence_threshold=threshold,
            notes="Python package 'pytesseract' is not installed in the current environment.",
        )

    configured_cmd = os.getenv("TESSERACT_CMD", settings.tesseract_cmd).strip()
    if configured_cmd:
        pytesseract.pytesseract.tesseract_cmd = configured_cmd

    try:
        data = pytesseract.image_to_data(
            rgb_image,
            output_type=PyTesseractOutput.DICT,
        )
    except TesseractNotFoundError:
        return OcrExtractionResult(
            ocr_status=OcrStatus.OCR_UNAVAILABLE,
            image_width=width,
            image_height=height,
            min_confidence_threshold=threshold,
            notes=(
                "Tesseract OCR executable is unavailable or not found on PATH / TESSERACT_CMD. "
                "Visual text extraction could not be completed."
            ),
        )
    except (TesseractError, OSError, ValueError, RuntimeError) as exc:
        return OcrExtractionResult(
            ocr_status=OcrStatus.OCR_FAILED,
            image_width=width,
            image_height=height,
            min_confidence_threshold=threshold,
            notes=f"Tesseract OCR execution failed ({type(exc).__name__}).",
        )
    except Exception as exc:
        return OcrExtractionResult(
            ocr_status=OcrStatus.OCR_FAILED,
            image_width=width,
            image_height=height,
            min_confidence_threshold=threshold,
            notes=f"Unexpected OCR error ({type(exc).__name__}).",
        )

    texts = data.get("text", []) if isinstance(data, dict) else []
    confs = data.get("conf", []) if isinstance(data, dict) else []
    lefts = data.get("left", []) if isinstance(data, dict) else []
    tops = data.get("top", []) if isinstance(data, dict) else []
    widths = data.get("width", []) if isinstance(data, dict) else []
    heights = data.get("height", []) if isinstance(data, dict) else []

    regions: list[OcrTextRegion] = []
    tokens: list[str] = []
    valid_confidences: list[float] = []

    for idx, raw_token in enumerate(texts):
        cleaned_token = _canonicalise_ocr_text(str(raw_token or ""))
        if not cleaned_token:
            continue

        raw_conf = confs[idx] if idx < len(confs) else -1
        try:
            conf_val = float(raw_conf)
        except (ValueError, TypeError):
            conf_val = -1.0

        # Tesseract uses -1 for non-word layout blocks; skip empty layout markers
        if conf_val < 0.0:
            continue

        left_val = int(lefts[idx]) if idx < len(lefts) else 0
        top_val = int(tops[idx]) if idx < len(tops) else 0
        w_val = int(widths[idx]) if idx < len(widths) else 0
        h_val = int(heights[idx]) if idx < len(heights) else 0

        regions.append(
            OcrTextRegion(
                text=cleaned_token,
                confidence=round(conf_val, 2),
                left=left_val,
                top=top_val,
                width=w_val,
                height=h_val,
            )
        )
        tokens.append(cleaned_token)
        valid_confidences.append(conf_val)

    full_extracted_text = _canonicalise_ocr_text(" ".join(tokens))

    if not full_extracted_text or not regions:
        return OcrExtractionResult(
            ocr_status=OcrStatus.OCR_NO_TEXT_DETECTED,
            image_width=width,
            image_height=height,
            extracted_text="",
            mean_confidence=None,
            min_confidence_threshold=threshold,
            regions_count=0,
            regions=[],
            prompt_injection_signals_detected=False,
            governance_evaluated=False,
            notes="OCR completed successfully; no visible text was detected in the image.",
        )

    mean_conf = round(sum(valid_confidences) / len(valid_confidences), 2)
    injection_detected = bool(PROMPT_INJECTION_PATTERNS.search(full_extracted_text))

    if mean_conf < threshold:
        return OcrExtractionResult(
            ocr_status=OcrStatus.OCR_LOW_CONFIDENCE,
            image_width=width,
            image_height=height,
            extracted_text=full_extracted_text,
            mean_confidence=mean_conf,
            min_confidence_threshold=threshold,
            regions_count=len(regions),
            regions=regions,
            prompt_injection_signals_detected=injection_detected,
            governance_evaluated=False,
            notes=(
                f"OCR extracted candidate text with mean confidence {mean_conf}% "
                f"below required threshold ({threshold}%). Escalated as INSUFFICIENT_DATA "
                "without generating definitive text policy violations from unreliable OCR."
            ),
        )

    return OcrExtractionResult(
        ocr_status=OcrStatus.OCR_SUCCESS,
        image_width=width,
        image_height=height,
        extracted_text=full_extracted_text,
        mean_confidence=mean_conf,
        min_confidence_threshold=threshold,
        regions_count=len(regions),
        regions=regions,
        prompt_injection_signals_detected=injection_detected,
        governance_evaluated=True,
        notes=f"OCR extracted {len(regions)} text region(s) with mean confidence {mean_conf}%.",
    )