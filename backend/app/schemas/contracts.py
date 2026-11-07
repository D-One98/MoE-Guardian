from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ExecutionState(str, Enum):
    OK = "OK"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"


class FindingType(str, Enum):
    DETERMINISTIC_VIOLATION = "DETERMINISTIC_VIOLATION"
    FACTUAL_CLAIM = "FACTUAL_CLAIM"
    TONE_MESSAGING = "TONE_MESSAGING"
    VISUAL_A11Y_SUBSET = "VISUAL_A11Y_SUBSET"


class VerificationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIABLE = "UNVERIFIABLE"
    NOT_CLAIM_APPLICABLE = "NOT_CLAIM_APPLICABLE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AnchorResolutionStatus(str, Enum):
    RESOLVED_UNIQUE = "RESOLVED_UNIQUE"
    AMBIGUOUS_FALLBACK_TO_BLOCK = "AMBIGUOUS_FALLBACK_TO_BLOCK"
    UNRESOLVED_SIDEBAR_ONLY = "UNRESOLVED_SIDEBAR_ONLY"


class DemoRole(str, Enum):
    CREATOR = "CREATOR"
    BRAND_MANAGER = "BRAND_MANAGER"
    AUTHORISED_REVIEWER = "AUTHORISED_REVIEWER"
    WORKSPACE_ADMIN = "WORKSPACE_ADMIN"


class RuleCategory(str, Enum):
    BANNED_TERM = "BANNED_TERM"
    BRAND_CASING = "BRAND_CASING"
    MANDATORY_DISCLAIMER = "MANDATORY_DISCLAIMER"
    NUMERIC_BOUND = "NUMERIC_BOUND"


class BrandRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(..., min_length=3, max_length=64)
    category: RuleCategory
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    mandatory_flag: bool = True
    severity: Severity
    pattern_or_target: str = Field(..., min_length=1)
    expected_replacement: Optional[str] = None
    numeric_max: Optional[float] = None
    numeric_unit: Optional[str] = None
    document_id: str = Field(default="DOC-BRAND-CONSTITUTION-V1", min_length=1)
    document_name: str = Field(default="Sample_Brand_Guidelines_v1.pdf", min_length=1)
    verified_page_or_row: int = Field(default=1, ge=1)
    version: str = Field(default="1.0", min_length=1)
    campaign_scope: str = Field(default="GLOBAL", min_length=1)

    @field_validator(
        "rule_id",
        "title",
        "description",
        "pattern_or_target",
        "document_id",
        "document_name",
        "version",
        "campaign_scope",
    )
    @classmethod
    def validate_non_blank_rule_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be blank or whitespace only.")
        return v.strip()


class ApprovedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(..., min_length=3, max_length=64)
    topic_key: str = Field(..., min_length=2, max_length=128)
    subject_keywords: List[str] = Field(..., min_length=1)
    canonical_text: str = Field(..., min_length=5)
    approved_numeric_value: float
    numeric_unit: str = Field(..., min_length=1, max_length=64)
    comparator: str = Field(default="up_to", pattern="^(up_to|exact|at_least)$")
    required_conditions: List[str] = Field(default_factory=list)
    prohibited_overstatements: List[str] = Field(default_factory=list)
    document_id: str = Field(default="DOC-APPROVED-FACTS-V1", min_length=1)
    document_name: str = Field(default="Sample_Approved_Facts_Vault_v1.csv", min_length=1)
    verified_page_or_row: int = Field(default=1, ge=1)
    version: str = Field(default="1.0", min_length=1)

    @field_validator(
        "fact_id",
        "topic_key",
        "canonical_text",
        "numeric_unit",
        "document_id",
        "document_name",
        "version",
    )
    @classmethod
    def validate_non_blank_fact_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be blank or whitespace only.")
        return v.strip()

    @field_validator("subject_keywords")
    @classmethod
    def validate_subject_keywords(cls, v: List[str]) -> List[str]:
        cleaned = [kw.strip() for kw in v if kw and kw.strip()]
        if not cleaned:
            raise ValueError("subject_keywords must contain at least one non-blank keyword.")
        return cleaned

class ContentBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_block_id: str = Field(..., min_length=1, description="Stable block ID from canonical editor structure")
    text: str = Field(..., min_length=1, description="Text content of the block")

    @field_validator("document_block_id", "text")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank or whitespace only.")
        return v

class OcrStatus(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    OCR_SUCCESS = "OCR_SUCCESS"
    OCR_NO_TEXT_DETECTED = "OCR_NO_TEXT_DETECTED"
    OCR_LOW_CONFIDENCE = "OCR_LOW_CONFIDENCE"
    OCR_UNAVAILABLE = "OCR_UNAVAILABLE"
    OCR_FAILED = "OCR_FAILED"


class OcrTextRegion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    confidence: float
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0


class OcrExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ocr_status: OcrStatus
    image_width: int = 0
    image_height: int = 0
    extracted_text: str = ""
    mean_confidence: Optional[float] = None
    min_confidence_threshold: float = 60.0
    regions_count: int = 0
    regions: List[OcrTextRegion] = Field(default_factory=list)
    prompt_injection_signals_detected: bool = False
    governance_evaluated: bool = False
    notes: Optional[str] = None


class VisualAssetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_block_id: str = Field(default="blk-visual-asset-01", min_length=1)
    filename: str = Field(default="creative.png", min_length=1)
    mime_type: str = Field(..., min_length=1, description="Declared MIME type (image/png or image/jpeg)")
    image_base64: str = Field(..., min_length=4, description="Base64-encoded image bytes")
    alt_text: Optional[str] = None
    declared_foreground_hex: Optional[str] = Field(
        default=None, description="Optional reliably known foreground text hex (#RRGGBB)"
    )
    declared_background_hex: Optional[str] = Field(
        default=None, description="Optional reliably known background hex (#RRGGBB)"
    )
    enable_ocr: Optional[bool] = Field(
        default=None,
        description="Whether to run Tesseract OCR text extraction on this visual asset.",
    )
    ocr_min_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional override for minimum acceptable OCR confidence percentage (0-100).",
    )
class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(..., description="BRAND_RULE or APPROVED_FACT")
    reference_id: str
    document_id: str
    document_name: str
    verified_page_or_row: int
    canonical_excerpt_from_db: str


class BackendRevalidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_by: str = "BACKEND_COORDINATOR"
    executed_checks: Dict[str, Any]
    candidate_verification_status: VerificationStatus
    revalidation_passed: bool


class RewriteCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    suggested_text: str
    backend_revalidation: BackendRevalidationResult


class UnifiedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    expert_engine: str
    execution_state: ExecutionState
    finding_type: FindingType
    severity: Severity
    verification_status: VerificationStatus
    document_block_id: Optional[str] = None
    matched_text: Optional[str] = None
    prefix_context: Optional[str] = None
    suffix_context: Optional[str] = None
    anchor_resolution_status: AnchorResolutionStatus = AnchorResolutionStatus.RESOLVED_UNIQUE
    explanation: str
    evidence_reference: Optional[EvidenceReference] = None
    rewrite_candidate: Optional[RewriteCandidate] = None
    human_review_required: bool = True


class EngineExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expert_engine: str
    mandatory_enforced: bool
    execution_state: ExecutionState
    findings_count: int
    notes: Optional[str] = None


class AuditCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str = Field(default="CAMP-DEMO-2026", min_length=1)
    submitted_by_role: DemoRole = DemoRole.CREATOR
    blocks: List[ContentBlock] = Field(..., min_length=1)
    alt_text: Optional[str] = None
    visual_asset: Optional[VisualAssetInput] = None

class AuditStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    READY_FOR_MANAGER_APPROVAL = "READY_FOR_MANAGER_APPROVAL"
    ESCALATED_TO_AUTHORISED_REVIEWER = "ESCALATED_TO_AUTHORISED_REVIEWER"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class AuditSnapshotRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: str
    audit_id: str
    org_id: str
    campaign_id: str
    content_sha256_hash: str
    brand_constitution_version: str
    facts_vault_version: str
    rule_engine_version: str
    router_config_version: str
    retrieved_evidence_ids: List[str]
    audit_output_sha256_hash: str
    approval_state: AuditStatus
    approver_role: DemoRole
    review_notes: Optional[str] = None
    approved_at_utc: str
    hmac_key_id: str
    previous_snapshot_hmac: str
    snapshot_hmac_signature: str


class AuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str
    org_id: str
    campaign_id: str
    submitted_by_role: DemoRole
    document_revision_hash: str
    overall_status: AuditStatus
    human_review_required: bool
    mandatory_policies_enforced: bool
    engine_executions: List[EngineExecutionRecord]
    findings: List[UnifiedFinding]
    blocks: List[ContentBlock]
    ai_disclosure_log: Dict[str, Any]
    latest_snapshot: Optional[AuditSnapshotRecord] = None
    created_at_utc: str


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_role: DemoRole
    decision: str = Field(..., pattern="^(APPROVE|REQUEST_CHANGES)$")
    override_justification: Optional[str] = None

import re


class BrandPaletteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    palette_id: str = Field(..., min_length=3, max_length=64)
    name: str = Field(..., min_length=2, max_length=128)
    hex: str = Field(..., description="Hex colour code (#RRGGBB)")
    max_delta_e: float = Field(default=15.0, gt=0.0, le=100.0)
    document_id: str = Field(default="DOC-BRAND-CONSTITUTION-V1", min_length=1)
    document_name: str = Field(default="Sample_Brand_Guidelines_v1.pdf", min_length=1)
    verified_page_or_row: int = Field(default=6, ge=1)
    version: str = Field(default="1.0", min_length=1)

    @field_validator("palette_id", "name", "document_id", "document_name", "version")
    @classmethod
    def validate_non_blank_palette_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be blank.")
        return v.strip()

    @field_validator("hex")
    @classmethod
    def validate_hex_format(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not re.match(r"^#[0-9A-F]{6}$", cleaned):
            raise ValueError("hex must be a valid 6-digit hex colour in '#RRGGBB' format.")
        return cleaned


class ExtractedPageMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(..., ge=1)
    char_count: int = Field(..., ge=0)
    extracted_text: str
    prompt_injection_signals_detected: bool = False


class GuidelineUploadPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str
    org_id: str
    document_id: str
    document_name: str
    status: str = Field(..., description="PENDING_CONFIRMATION or CONFIRMED")
    page_count: int
    extraction_status: str = Field(..., description="OK or IMAGE_ONLY_OR_SCANNED_UNSUPPORTED")
    prompt_shield_isolated: bool = True
    pages: List[ExtractedPageMetadata]
    candidate_rules: List[BrandRule]
    warnings: List[str] = Field(default_factory=list)


class GuidelineConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_constitution_version: str = Field(default="1.0", min_length=1)
    confirmed_rules: List[BrandRule] = Field(..., min_length=1)


class CsvRowError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_number: int
    fact_id: Optional[str] = None
    error_code: str
    message: str


class CsvFactsUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str
    document_name: str
    total_rows_processed: int
    saved_facts_count: int
    saved_facts: List[ApprovedFact]
    row_errors: List[CsvRowError]

class OnDemandRewriteRequest(BaseModel):
    """
    Request payload for on-demand surgical rewrite generation and fail-closed validation.
    extra='forbid' ensures clients cannot forge or supply candidate_verification_status
    or revalidation_passed booleans.
    """
    model_config = ConfigDict(extra="forbid")

    custom_candidate_text: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Optional creator-edited rewrite text to validate; if omitted, VoiceGuard generates candidates on demand.",
    )
    preserve_tone_notes: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional lightweight tone hint (e.g., 'informative', 'confident').",
    )

    @field_validator("custom_candidate_text")
    @classmethod
    def validate_custom_candidate_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("custom_candidate_text must not be blank or whitespace only.")
        return v.strip() if v is not None else None


class OnDemandRewriteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str
    org_id: str
    finding_id: str
    original_matched_text: str
    original_finding_type: FindingType
    original_verification_status: VerificationStatus
    rewrite_candidates: List[RewriteCandidate]
    selected_primary_candidate: Optional[RewriteCandidate] = None
    
class SnapshotVerificationStatus(str, Enum):
    VALID = "VALID"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNKNOWN_KEY_ID = "UNKNOWN_KEY_ID"
    MALFORMED_SNAPSHOT = "MALFORMED_SNAPSHOT"
    BROKEN_HASH_CHAIN = "BROKEN_HASH_CHAIN"
    NO_SNAPSHOT_FOUND = "NO_SNAPSHOT_FOUND"


class SnapshotVerificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str
    org_id: str
    snapshot_id: Optional[str] = None
    hmac_key_id: Optional[str] = None
    is_valid: bool
    status_code: SnapshotVerificationStatus
    chain_integrity_verified: bool
    message: str


class SimulatedCmsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cms_export_mode: str = "SIMULATED_PRE_PUBLICATION_PAYLOAD"
    external_cms_published: bool = False
    export_ready_for_cms: bool
    approval_status: AuditStatus
    audit_reference_id: str
    document_revision_hash: str
    snapshot_id: Optional[str] = None
    snapshot_hmac_signature: Optional[str] = None
    approved_blocks: List[ContentBlock] = Field(default_factory=list)
    approved_alt_text: Optional[str] = None
    notice: str


class ComplianceExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_version: str = "1.0"
    generated_at_utc: str
    audit_id: str
    org_id: str
    campaign_id: str
    created_at_utc: str
    submitted_by_role: DemoRole
    document_revision_hash: str
    overall_status: AuditStatus
    human_review_required: bool
    mandatory_policies_enforced: bool
    machine_governance_summary: Dict[str, Any]
    engine_executions: List[EngineExecutionRecord]
    machine_findings: List[UnifiedFinding]
    human_review_decision: Optional[Dict[str, Any]] = None
    snapshot_integrity: SnapshotVerificationResponse
    ai_disclosure_log: Dict[str, Any]
    simulated_cms_payload: SimulatedCmsPayload