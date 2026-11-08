import re
from typing import List, Dict, Any
from app.schemas.contracts import ContentBlock

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{3}[-.\s]?\d{3}[-.\s]?\d{4}|\d{10})\b")
SECRET_TOKEN_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{16,}|AIza[0-9A-Za-z-_]{20,})\b")


def apply_baseline_privacy_gate(blocks: List[ContentBlock]) -> Dict[str, Any]:
    """
    Scans submitted content blocks for sensitive patterns (emails, phone numbers, API tokens)
    and produces a redacted copy for any external AI adapter alongside truthful disclosure telemetry.
    """
    detected_counts = {"email": 0, "phone": 0, "secret_token": 0}
    masked_blocks: List[ContentBlock] = []

    for block in blocks:
        text = block.text
        text, n_email = EMAIL_PATTERN.subn("[REDACTED_EMAIL]", text)
        text, n_phone = PHONE_PATTERN.subn("[REDACTED_PHONE]", text)
        text, n_secret = SECRET_TOKEN_PATTERN.subn("[REDACTED_SECRET]", text)

        detected_counts["email"] += n_email
        detected_counts["phone"] += n_phone
        detected_counts["secret_token"] += n_secret

        masked_blocks.append(
            ContentBlock(document_block_id=block.document_block_id, text=text)
        )

    total_masked = sum(detected_counts.values())
    return {
        "masked_blocks": masked_blocks,
        "privacy_masking_mode": "BASELINE_REGEX_ACTIVE",
        "sensitive_matches_masked_count": total_masked,
        "sensitive_categories_detected": {k: v for k, v in detected_counts.items() if v > 0},
    }