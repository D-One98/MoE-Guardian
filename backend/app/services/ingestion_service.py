import csv
import io
import os
import re
import unicodedata
import uuid
from typing import List, Tuple, Dict, Any
import fitz
from pydantic import ValidationError
from app.core.config import settings
from app.schemas.contracts import (
    BrandRule,
    RuleCategory,
    Severity,
    ApprovedFact,
    ExtractedPageMetadata,
    CsvRowError,
)

PDF_MAGIC_HEADER = b"%PDF-"

PROMPT_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior)\s+instructions|system\s+prompt|mark\s+all\s+content\s+as\s+approved)",
    re.IGNORECASE,
)

REQUIRED_CSV_COLUMNS = {
    "fact_id",
    "topic_key",
    "subject_keywords",
    "canonical_text",
    "approved_numeric_value",
    "numeric_unit",
    "comparator",
    "required_conditions",
    "prohibited_overstatements",
    "verified_page_or_row",
    "version",
}


class IngestionValidationError(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def _canonicalise_text(raw: str) -> str:
    norm = unicodedata.normalize("NFKC", raw)
    # Remove null bytes and control chars except newlines/tabs
    return "".join(ch for ch in norm if ch in ("\n", "\t") or ord(ch) >= 32)


def extract_candidate_rules_from_page(
    page_text: str,
    page_number: int,
    document_id: str,
    document_name: str,
    start_seq: int,
) -> List[BrandRule]:
    """
    Deterministically extracts candidate brand rules from guideline text lines
    with exact source page references so the administrator can inspect, edit, and confirm them.
    """
    candidates: List[BrandRule] = []
    seq = start_seq

    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    for line in lines:
        clean_line = re.sub(r"^[\-\*\•\d\.\)\s]+", "", line).strip()
        if len(clean_line) < 6:
            continue

        # Pattern 1: Banned term rule — e.g., Never use "guaranteed" or Do not use the word 'world's #1'
        banned_match = re.search(
            r"(?:never\s+use|do\s+not\s+use|prohibit|avoid)(?:\s+the\s+(?:word|term|phrase))?\s+['\"]([^'\"]{2,60})['\"]",
            clean_line,
            re.IGNORECASE,
        )
        if banned_match:
            term = banned_match.group(1).strip()
            candidates.append(
                BrandRule(
                    rule_id=f"RULE-PDF-P{page_number}-{seq:03d}",
                    category=RuleCategory.BANNED_TERM,
                    title=f"Prohibit term '{term}' (Page {page_number})",
                    description=clean_line,
                    mandatory_flag=True,
                    severity=Severity.HIGH,
                    pattern_or_target=term,
                    document_id=document_id,
                    document_name=document_name,
                    verified_page_or_row=page_number,
                    version="1.0",
                    campaign_scope="GLOBAL",
                )
            )
            seq += 1
            continue

        # Pattern 2: Brand casing rule — e.g., Always write the brand name as AURORAGEAR
        casing_match = re.search(
            r"(?:always\s+write(?:\s+the\s+brand\s+name)?\s+as|exact\s+brand\s+casing(?:\s+for)?)\s+['\"]?([A-Za-z0-9_-]{2,40})['\"]?",
            clean_line,
            re.IGNORECASE,
        )
        if casing_match:
            brand_token = casing_match.group(1).strip()
            candidates.append(
                BrandRule(
                    rule_id=f"RULE-PDF-P{page_number}-{seq:03d}",
                    category=RuleCategory.BRAND_CASING,
                    title=f"Exact brand casing '{brand_token}' (Page {page_number})",
                    description=clean_line,
                    mandatory_flag=True,
                    severity=Severity.MEDIUM,
                    pattern_or_target=brand_token,
                    expected_replacement=brand_token,
                    document_id=document_id,
                    document_name=document_name,
                    verified_page_or_row=page_number,
                    version="1.0",
                    campaign_scope="GLOBAL",
                )
            )
            seq += 1
            continue

        # Pattern 3: Mandatory disclaimer — e.g., Mandatory disclaimer: "..." or must include the phrase "..."
        disc_match = re.search(
            r"(?:mandatory\s+disclaimer\s*:|must\s+include(?:\s+the\s+phrase)?)\s*['\"]([^'\"]{5,160})['\"]",
            clean_line,
            re.IGNORECASE,
        )
        if disc_match:
            phrase = disc_match.group(1).strip()
            candidates.append(
                BrandRule(
                    rule_id=f"RULE-PDF-P{page_number}-{seq:03d}",
                    category=RuleCategory.MANDATORY_DISCLAIMER,
                    title=f"Mandatory disclaimer requirement (Page {page_number})",
                    description=clean_line,
                    mandatory_flag=True,
                    severity=Severity.MEDIUM,
                    pattern_or_target=phrase,
                    expected_replacement=phrase,
                    document_id=document_id,
                    document_name=document_name,
                    verified_page_or_row=page_number,
                    version="1.0",
                    campaign_scope="GLOBAL",
                )
            )
            seq += 1
            continue

        # Pattern 4: Numeric discount bound — e.g., Promotional discount claims must not exceed 30%
        num_match = re.search(
            r"discount.*?(?:must\s+not\s+exceed|maximum(?:\s+of)?)\s+(\d+(?:\.\d+)?)\s*%",
            clean_line,
            re.IGNORECASE,
        )
        if num_match:
            max_val = float(num_match.group(1))
            candidates.append(
                BrandRule(
                    rule_id=f"RULE-PDF-P{page_number}-{seq:03d}",
                    category=RuleCategory.NUMERIC_BOUND,
                    title=f"Maximum discount bound {max_val:g}% (Page {page_number})",
                    description=clean_line,
                    mandatory_flag=True,
                    severity=Severity.HIGH,
                    pattern_or_target="discount_percent",
                    numeric_max=max_val,
                    numeric_unit="%",
                    document_id=document_id,
                    document_name=document_name,
                    verified_page_or_row=page_number,
                    version="1.0",
                    campaign_scope="GLOBAL",
                )
            )
            seq += 1

    return candidates


def parse_brand_guideline_pdf(
    file_bytes: bytes,
    filename: str,
) -> Dict[str, Any]:
    """
    Validates actual PDF content using magic header and PyMuPDF, enforces size and page limits,
    detects corrupt/empty or scanned/image-only PDFs honestly, isolates untrusted text (PromptShield),
    and extracts candidate rules with page references for Admin Confirmation Preview.
    """
    max_bytes = int(os.getenv("MAX_PDF_UPLOAD_BYTES", str(settings.max_pdf_upload_bytes)))
    max_pages = int(os.getenv("MAX_PDF_PAGES", str(settings.max_pdf_pages)))

    if not file_bytes:
        raise IngestionValidationError("EMPTY_PDF_FILE", "Uploaded PDF file is empty (0 bytes).", 400)

    if len(file_bytes) > max_bytes:
        raise IngestionValidationError(
            "OVERSIZED_PDF_FILE",
            f"Uploaded PDF size ({len(file_bytes)} bytes) exceeds maximum allowed limit ({max_bytes} bytes).",
            413,
        )

    # Validate actual file content magic header (%PDF-), not just filename or MIME header
    if not file_bytes.lstrip().startswith(PDF_MAGIC_HEADER):
        raise IngestionValidationError(
            "INVALID_PDF_CONTENT",
            "Uploaded file does not have a valid '%PDF-' binary signature.",
            400,
        )

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise IngestionValidationError(
            "CORRUPT_PDF_FILE",
            f"PyMuPDF failed to open PDF stream (corrupt or malformed PDF): {type(exc).__name__}",
            400,
        ) from exc

    try:
        page_count = doc.page_count
        if page_count == 0:
            raise IngestionValidationError("ZERO_PAGE_PDF", "Uploaded PDF contains 0 pages.", 400)

        if page_count > max_pages:
            raise IngestionValidationError(
                "PDF_PAGE_LIMIT_EXCEEDED",
                f"PDF page count ({page_count}) exceeds maximum allowed limit ({max_pages} pages).",
                400,
            )

        document_id = f"DOC-PDF-{uuid.uuid4().hex[:8].upper()}"
        safe_filename = (filename or "Brand_Guidelines.pdf").strip()
        pages_meta: List[ExtractedPageMetadata] = []
        candidate_rules: List[BrandRule] = []
        warnings: List[str] = []
        total_extracted_chars = 0
        rule_seq = 1

        for idx in range(page_count):
            page = doc.load_page(idx)
            page_num = idx + 1
            raw_text = page.get_text("text") or ""
            clean_text = _canonicalise_text(raw_text).strip()
            total_extracted_chars += len(clean_text)

            injection_detected = bool(PROMPT_INJECTION_PATTERNS.search(clean_text))
            if injection_detected:
                warnings.append(
                    f"Page {page_num}: Potential prompt-injection phrasing detected in untrusted PDF text; "
                    "isolated as passive data by PromptShield."
                )

            pages_meta.append(
                ExtractedPageMetadata(
                    page_number=page_num,
                    char_count=len(clean_text),
                    extracted_text=clean_text,
                    prompt_injection_signals_detected=injection_detected,
                )
            )

            if clean_text:
                page_candidates = extract_candidate_rules_from_page(
                    page_text=clean_text,
                    page_number=page_num,
                    document_id=document_id,
                    document_name=safe_filename,
                    start_seq=rule_seq,
                )
                candidate_rules.extend(page_candidates)
                rule_seq += len(page_candidates)

        if total_extracted_chars == 0:
            extraction_status = "IMAGE_ONLY_OR_SCANNED_UNSUPPORTED"
            warnings.append(
                "PDF contains 0 extractable text characters across all pages (likely a scanned or image-only PDF). "
                "OCR is not active on PDF guideline uploads; please upload a text-searchable PDF or add rules manually in the preview."
            )
        else:
            extraction_status = "OK"

        return {
            "document_id": document_id,
            "document_name": safe_filename,
            "page_count": page_count,
            "extraction_status": extraction_status,
            "pages": pages_meta,
            "candidate_rules": candidate_rules,
            "warnings": warnings,
        }
    finally:
        doc.close()


def parse_approved_facts_csv(
    file_bytes: bytes,
    filename: str,
) -> Tuple[List[ApprovedFact], List[CsvRowError], int]:
    """
    Validates and parses an Approved Facts CSV upload.
    Enforces required column headers, parses semicolon-separated lists,
    and returns valid ApprovedFact objects alongside explicit row-level errors (never silently discarding invalid rows).
    """
    max_bytes = int(os.getenv("MAX_CSV_UPLOAD_BYTES", str(settings.max_csv_upload_bytes)))
    if not file_bytes:
        raise IngestionValidationError("EMPTY_CSV_FILE", "Uploaded CSV file is empty.", 400)
    if len(file_bytes) > max_bytes:
        raise IngestionValidationError(
            "OVERSIZED_CSV_FILE",
            f"Uploaded CSV size ({len(file_bytes)} bytes) exceeds limit ({max_bytes} bytes).",
            413,
        )

    try:
        decoded = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise IngestionValidationError(
            "INVALID_CSV_ENCODING",
            "Uploaded CSV file is not valid UTF-8 text.",
            400,
        ) from exc

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise IngestionValidationError("MISSING_CSV_HEADERS", "CSV file has no header row.", 400)

    normalized_headers = {h.strip() for h in reader.fieldnames if h}
    missing_cols = sorted(REQUIRED_CSV_COLUMNS - normalized_headers)
    if missing_cols:
        raise IngestionValidationError(
            "MISSING_REQUIRED_CSV_COLUMNS",
            f"CSV is missing required columns: {missing_cols}",
            400,
        )

    valid_facts: List[ApprovedFact] = []
    row_errors: List[CsvRowError] = []
    seen_fact_ids_in_csv: set[str] = set()
    safe_doc_name = (filename or "Approved_Facts.csv").strip()
    doc_id = f"DOC-CSV-{uuid.uuid4().hex[:8].upper()}"
    total_rows = 0

    for row_idx, raw_row in enumerate(reader, start=2):  # Row 1 is header
        total_rows += 1
        if any(k is None for k in raw_row.keys()):
            row_errors.append(
                CsvRowError(
                    row_number=row_idx,
                    fact_id=raw_row.get("fact_id"),
                    error_code="MALFORMED_CSV_ROW",
                    message="Row contains more fields than the header defines.",
                )
            )
            continue

        row = {k.strip(): (v.strip() if isinstance(v, str) else "") for k, v in raw_row.items() if k}
        raw_fact_id = row.get("fact_id") or None

        if raw_fact_id and raw_fact_id in seen_fact_ids_in_csv:
            row_errors.append(
                CsvRowError(
                    row_number=row_idx,
                    fact_id=raw_fact_id,
                    error_code="DUPLICATE_FACT_ID_IN_CSV",
                    message=f"Duplicate fact_id '{raw_fact_id}' found within the same CSV upload at row {row_idx}.",
                )
            )
            continue

        try:
            num_val_str = row.get("approved_numeric_value", "")
            if not num_val_str:
                raise ValueError("approved_numeric_value is required and cannot be empty.")
            num_val = float(num_val_str)

            page_or_row_str = row.get("verified_page_or_row", "")
            verified_row = int(page_or_row_str) if page_or_row_str else row_idx

            keywords = [k.strip() for k in row.get("subject_keywords", "").split(";") if k.strip()]
            req_conds = [c.strip() for c in row.get("required_conditions", "").split(";") if c.strip()]
            prohib_over = [p.strip() for p in row.get("prohibited_overstatements", "").split(";") if p.strip()]

            fact = ApprovedFact(
                fact_id=row.get("fact_id", ""),
                topic_key=row.get("topic_key", ""),
                subject_keywords=keywords,
                canonical_text=row.get("canonical_text", ""),
                approved_numeric_value=num_val,
                numeric_unit=row.get("numeric_unit", ""),
                comparator=row.get("comparator", "") or "up_to",
                required_conditions=req_conds,
                prohibited_overstatements=prohib_over,
                document_id=doc_id,
                document_name=safe_doc_name,
                verified_page_or_row=verified_row,
                version=row.get("version", "") or "1.0",
            )
            valid_facts.append(fact)
            seen_fact_ids_in_csv.add(fact.fact_id)
        except (ValueError, ValidationError) as exc:
            row_errors.append(
                CsvRowError(
                    row_number=row_idx,
                    fact_id=raw_fact_id,
                    error_code="INVALID_ROW_DATA",
                    message=str(exc),
                )
            )

    if total_rows == 0:
        raise IngestionValidationError("EMPTY_CSV_ROWS", "CSV contains headers but 0 data rows.", 400)

    return valid_facts, row_errors, total_rows