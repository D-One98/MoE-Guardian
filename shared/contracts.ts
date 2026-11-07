// ============================================================================
// MoE-GUARDIAN (Powered by VERITY MoE) — Shared Frontend/Backend TypeScript Contract
// Source of Truth: backend/app/schemas/contracts.py
// ============================================================================

export type ExecutionState =
  | "OK"
  | "NOT_APPLICABLE"
  | "INSUFFICIENT_DATA"
  | "ERROR";

export type FindingType =
  | "DETERMINISTIC_VIOLATION"
  | "FACTUAL_CLAIM"
  | "TONE_MESSAGING"
  | "VISUAL_A11Y_SUBSET";

export type VerificationStatus =
  | "SUPPORTED"
  | "PARTIAL"
  | "CONTRADICTED"
  | "UNVERIFIABLE"
  | "NOT_CLAIM_APPLICABLE";

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";

export type AnchorResolutionStatus =
  | "RESOLVED_UNIQUE"
  | "AMBIGUOUS_FALLBACK_TO_BLOCK"
  | "UNRESOLVED_SIDEBAR_ONLY";

export type DemoRole =
  | "CREATOR"
  | "BRAND_MANAGER"
  | "AUTHORISED_REVIEWER"
  | "WORKSPACE_ADMIN";

export type AuditStatus =
  | "PENDING_REVIEW"
  | "READY_FOR_MANAGER_APPROVAL"
  | "ESCALATED_TO_AUTHORISED_REVIEWER"
  | "APPROVED"
  | "CHANGES_REQUESTED";

export interface ContentBlock {
  document_block_id: string;
  text: string;
}

export interface EvidenceReference {
  source_type: "BRAND_RULE" | "APPROVED_FACT" | string;
  reference_id: string;
  document_id: string;
  document_name: string;
  verified_page_or_row: number;
  canonical_excerpt_from_db: string;
}

export interface BackendRevalidationResult {
  assigned_by: "BACKEND_COORDINATOR" | string;
  executed_checks: Record<string, string | number | boolean>;
  candidate_verification_status: VerificationStatus;
  revalidation_passed: boolean;
}

export interface RewriteCandidate {
  candidate_id: string;
  suggested_text: string;
  backend_revalidation: BackendRevalidationResult;
}

export interface UnifiedFinding {
  finding_id: string;
  expert_engine: "RuleGuard" | "ClaimGuard" | "VisualGuard" | "VoiceGuard" | string;
  execution_state: ExecutionState;
  finding_type: FindingType;
  severity: Severity;
  verification_status: VerificationStatus;
  document_block_id: string | null;
  matched_text: string | null;
  prefix_context: string | null;
  suffix_context: string | null;
  anchor_resolution_status: AnchorResolutionStatus;
  explanation: string;
  evidence_reference: EvidenceReference | null;
  rewrite_candidate: RewriteCandidate | null;
  human_review_required: boolean;
}

export interface EngineExecutionRecord {
  expert_engine: string;
  mandatory_enforced: boolean;
  execution_state: ExecutionState;
  findings_count: number;
  notes: string | null;
}

export interface AuditSnapshotRecord {
  snapshot_id: string;
  audit_id: string;
  org_id: string;
  campaign_id: string;
  content_sha256_hash: string;
  brand_constitution_version: string;
  facts_vault_version: string;
  rule_engine_version: string;
  router_config_version: string;
  retrieved_evidence_ids: string[];
  audit_output_sha256_hash: string;
  approval_state: AuditStatus;
  approver_role: DemoRole;
  review_notes: string | null;
  approved_at_utc: string;
  hmac_key_id: string;
  previous_snapshot_hmac: string;
  snapshot_hmac_signature: string;
}

export interface AuditCreateRequest {
  campaign_id?: string;
  submitted_by_role?: DemoRole;
  blocks: ContentBlock[];
  alt_text?: string | null;
  visual_asset?: VisualAssetInput | null;
}

export interface AuditResponse {
  audit_id: string;
  org_id: string;
  campaign_id: string;
  submitted_by_role: DemoRole;
  document_revision_hash: string;
  overall_status: AuditStatus;
  human_review_required: boolean;
  mandatory_policies_enforced: boolean;
  engine_executions: EngineExecutionRecord[];
  findings: UnifiedFinding[];
  blocks: ContentBlock[];
  ai_disclosure_log: Record<string, unknown>;
  latest_snapshot: AuditSnapshotRecord | null;
  created_at_utc: string;
}

export interface ReviewDecisionRequest {
  actor_role: DemoRole;
  decision: "APPROVE" | "REQUEST_CHANGES";
  override_justification?: string | null;
}

export type RuleCategory =
  | "BANNED_TERM"
  | "BRAND_CASING"
  | "MANDATORY_DISCLAIMER"
  | "NUMERIC_BOUND";

export interface BrandRule {
  rule_id: string;
  category: RuleCategory;
  title: string;
  description: string;
  mandatory_flag?: boolean;
  severity: Severity;
  pattern_or_target: string;
  expected_replacement?: string | null;
  numeric_max?: number | null;
  numeric_unit?: string | null;
  document_id?: string;
  document_name?: string;
  verified_page_or_row?: number;
  version?: string;
  campaign_scope?: string;
}

export interface ApprovedFact {
  fact_id: string;
  topic_key: string;
  subject_keywords: string[];
  canonical_text: string;
  approved_numeric_value: number;
  numeric_unit: string;
  comparator?: "up_to" | "exact" | "at_least";
  required_conditions?: string[];
  prohibited_overstatements?: string[];
  document_id?: string;
  document_name?: string;
  verified_page_or_row?: number;
  version?: string;
}

export type OcrStatus =
  | "NOT_REQUESTED"
  | "OCR_SUCCESS"
  | "OCR_NO_TEXT_DETECTED"
  | "OCR_LOW_CONFIDENCE"
  | "OCR_UNAVAILABLE"
  | "OCR_FAILED";

export interface OcrTextRegion {
  text: string;
  confidence: number;
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface OcrExtractionResult {
  ocr_status: OcrStatus;
  image_width: number;
  image_height: number;
  extracted_text: string;
  mean_confidence: number | null;
  min_confidence_threshold: number;
  regions_count: number;
  regions: OcrTextRegion[];
  prompt_injection_signals_detected: boolean;
  governance_evaluated: boolean;
  notes: string | null;
}

export interface VisualAssetInput {
  document_block_id?: string;
  filename?: string;
  mime_type: "image/png" | "image/jpeg" | "image/jpg" | string;
  image_base64: string;
  alt_text?: string | null;
  declared_foreground_hex?: string | null;
  declared_background_hex?: string | null;
  enable_ocr?: boolean | null;
  ocr_min_confidence?: number | null;
}

export interface BrandPaletteItem {
  palette_id: string;
  name: string;
  hex: string;
  max_delta_e?: number;
  document_id?: string;
  document_name?: string;
  verified_page_or_row?: number;
  version?: string;
}

export interface ExtractedPageMetadata {
  page_number: number;
  char_count: number;
  extracted_text: string;
  prompt_injection_signals_detected: boolean;
}

export interface GuidelineUploadPreviewResponse {
  batch_id: string;
  org_id: string;
  document_id: string;
  document_name: string;
  status: "PENDING_CONFIRMATION" | "CONFIRMED" | string;
  page_count: number;
  extraction_status: "OK" | "IMAGE_ONLY_OR_SCANNED_UNSUPPORTED" | string;
  prompt_shield_isolated: boolean;
  pages: ExtractedPageMetadata[];
  candidate_rules: BrandRule[];
  warnings: string[];
}

export interface GuidelineConfirmRequest {
  brand_constitution_version?: string;
  confirmed_rules: BrandRule[];
}

export interface CsvRowError {
  row_number: number;
  fact_id: string | null;
  error_code: string;
  message: string;
}

export interface CsvFactsUploadResponse {
  org_id: string;
  document_name: string;
  total_rows_processed: number;
  saved_facts_count: number;
  saved_facts: ApprovedFact[];
  row_errors: CsvRowError[];
}

export interface OnDemandRewriteRequest {
  custom_candidate_text?: string | null;
  preserve_tone_notes?: string | null;
}

export interface OnDemandRewriteResponse {
  audit_id: string;
  org_id: string;
  finding_id: string;
  original_matched_text: string;
  original_finding_type: FindingType;
  original_verification_status: VerificationStatus;
  rewrite_candidates: RewriteCandidate[];
  selected_primary_candidate: RewriteCandidate | null;
}

export type SnapshotVerificationStatus =
  | "VALID"
  | "INVALID_SIGNATURE"
  | "UNKNOWN_KEY_ID"
  | "MALFORMED_SNAPSHOT"
  | "BROKEN_HASH_CHAIN"
  | "NO_SNAPSHOT_FOUND";

export interface SnapshotVerificationResponse {
  audit_id: string;
  org_id: string;
  snapshot_id: string | null;
  hmac_key_id: string | null;
  is_valid: boolean;
  status_code: SnapshotVerificationStatus;
  chain_integrity_verified: boolean;
  message: string;
}

export interface SimulatedCmsPayload {
  cms_export_mode: "SIMULATED_PRE_PUBLICATION_PAYLOAD" | string;
  external_cms_published: boolean;
  export_ready_for_cms: boolean;
  approval_status: AuditStatus;
  audit_reference_id: string;
  document_revision_hash: string;
  snapshot_id: string | null;
  snapshot_hmac_signature: string | null;
  approved_blocks: ContentBlock[];
  approved_alt_text: string | null;
  notice: string;
}

export interface ComplianceExportResponse {
  export_version: string;
  generated_at_utc: string;
  audit_id: string;
  org_id: string;
  campaign_id: string;
  created_at_utc: string;
  submitted_by_role: DemoRole;
  document_revision_hash: string;
  overall_status: AuditStatus;
  human_review_required: boolean;
  mandatory_policies_enforced: boolean;
  machine_governance_summary: Record<string, unknown>;
  engine_executions: EngineExecutionRecord[];
  machine_findings: UnifiedFinding[];
  human_review_decision: Record<string, unknown> | null;
  snapshot_integrity: SnapshotVerificationResponse;
  ai_disclosure_log: Record<string, unknown>;
  simulated_cms_payload: SimulatedCmsPayload;
}