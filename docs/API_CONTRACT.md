# MoE-GUARDIAN — Frontend/Backend API Contract

* **Backend Source of Truth:** `backend/app/schemas/contracts.py`
* **Shared TypeScript Contract:** `shared/contracts.ts`
* **Base URL (Local):** `http://localhost:8000`
* **Interactive Swagger UI:** `http://localhost:8000/docs`

---

## 1. Allowed Orthogonal Enum Values

* **`ExecutionState`:** `"OK"` | `"NOT_APPLICABLE"` | `"INSUFFICIENT_DATA"` | `"ERROR"`
* **`FindingType`:** `"DETERMINISTIC_VIOLATION"` | `"FACTUAL_CLAIM"` | `"TONE_MESSAGING"` | `"VISUAL_A11Y_SUBSET"`
* **`VerificationStatus`:** `"SUPPORTED"` | `"PARTIAL"` | `"CONTRADICTED"` | `"UNVERIFIABLE"` | `"NOT_CLAIM_APPLICABLE"`
* **`Severity`:** `"CRITICAL"` | `"HIGH"` | `"MEDIUM"` | `"LOW"` | `"INFO"`
* **`AnchorResolutionStatus`:** `"RESOLVED_UNIQUE"` | `"AMBIGUOUS_FALLBACK_TO_BLOCK"` | `"UNRESOLVED_SIDEBAR_ONLY"`
* **`DemoRole`:** `"CREATOR"` | `"BRAND_MANAGER"` | `"AUTHORISED_REVIEWER"` | `"WORKSPACE_ADMIN"`
* **`AuditStatus`:** `"PENDING_REVIEW"` | `"READY_FOR_MANAGER_APPROVAL"` | `"ESCALATED_TO_AUTHORISED_REVIEWER"` | `"APPROVED"` | `"CHANGES_REQUESTED"`

---

## 2. Endpoints

### `GET /api/health`
Returns service health and version metadata.

### `GET /api/demo/workspace`
Returns the pre-seeded fictional demo brand (`AURORAGEAR`), allowed `DemoRole` list, and 3 ready-to-load `sample_drafts` for 1-click judge testing.

### `GET /api/brand/rules` & `GET /api/brand/facts`
Returns active Brand Constitution rules and Approved Facts Vault entries.

### `POST /api/audits`
Runs a full `VERITY MoE` governance audit on canonical content blocks.
* **Request Body (`AuditCreateRequest`):**
```json
{
  "campaign_id": "CAMP-DEMO-2026",
  "submitted_by_role": "CREATOR",
  "blocks": [
    {
      "document_block_id": "blk-p1",
      "text": "AURORAGEAR delivers 12 hours of guaranteed battery life on a single charge!"
    }
  ],
  "alt_text": null
}

Response (201 Created — AuditResponse): Returns audit_id, document_revision_hash, overall_status, engine_executions, findings (each with backend-resolved evidence_reference and optional fail-closed rewrite_candidate), and ai_disclosure_log.

GET /api/audits/{audit_id}
Retrieves an existing AuditResponse by ID. Returns 404 with {"detail": {"error": "AUDIT_NOT_FOUND", "message": "..."}} if not found.

POST /api/audits/{audit_id}/review
Records a human review decision and generates an HMAC-SHA256 signed AuditSnapshotRecord.

Request Body (ReviewDecisionRequest):

JSON
{
  "actor_role": "AUTHORISED_REVIEWER",
  "decision": "APPROVE",
  "override_justification": "Approved for internal teaser with lab testing footnote."
}
Validation Rules:

Returns 403 Forbidden if actor_role == "CREATOR" (Maker-Checker enforcement).

Returns 403 Forbidden if overall_status == "ESCALATED_TO_AUTHORISED_REVIEWER" and actor_role is not "AUTHORISED_REVIEWER" or "WORKSPACE_ADMIN".

Returns 400 Bad Request if approving a draft with non-SUPPORTED findings without a non-empty override_justification.

# MoE-GUARDIAN — Project State (Session 2 Complete)

## 1. Implemented & Verified in Sessions 1 & 2
* **FastAPI & Unified Contracts:** Strict orthogonal Pydantic v2 schemas (`backend/app/schemas/contracts.py`) and synchronized TypeScript interfaces (`shared/contracts.ts`).
* **SQLAlchemy 2.x Persistence (`backend/app/core/database.py`, `backend/app/models/orm_models.py`, `backend/app/repositories/governance_repo.py`):** Persistent storage for `BrandRuleModel`, `ApprovedFactModel`, `AuditRecordModel`, `AuditFindingModel`, and `ReviewSnapshotModel` with SQLite foreign-key enforcement, idempotent demo seeding, and transaction rollback.
* **Brand Ingestion APIs (`POST /api/brand/rules`, `POST /api/brand/facts`):** Validated custom rule and fact ingestion with `409 Conflict` duplicate protection and immediate availability in subsequent audits.
* **Deterministic Specialist Engines:**
  * `RuleGuard`: Banned terms, brand casing (`AURORAGEAR`), mandatory disclaimers, and discount bounds.
  * `ClaimGuard` Baseline: 4-state claim verification (`SUPPORTED`, `PARTIAL`, `CONTRADICTED`, `UNVERIFIABLE`) and fail-closed Rewrite Validation Coordinator.
  * `VisualGuard` Baseline: Static PNG/JPEG validation, 5 MB size cap, 16 MP decompression-bomb protection, CIEDE2000 ($\Delta E$) brand palette comparison, `alt_text` check, and WCAG relative-luminance contrast (with `INSUFFICIENT_DATA` escalation when foreground/background regions cannot be reliably isolated).
* **Hardened HMAC-SHA256 Review Snapshots:** Canonical snapshot signing covering `review_notes`, chained via `previous_snapshot_hmac` in persistent storage, with cryptographic tamper verification (`VerityMoEOrchestrator.verify_snapshot_hmac`).
* **Automated Test Suite:** **27 passing Pytest tests** across 4 test modules using isolated temporary SQLite databases (`backend/tests/conftest.py`).

## 2. Remaining Work for Subsequent Sessions
* **Session 3 (Frontend & End-to-End User Workflow):** Connect `frontend/` UI to the Session 2 backend endpoints (`GET /api/demo/workspace`, `GET/POST /api/brand/rules`, `GET/POST /api/brand/facts`, `POST /api/audits`, `POST /api/audits/{audit_id}/review`).
* **Session 4 (Deployment & Hardening):** Public cloud deployment (Vercel + Render/Railway) and Round 2 submission package verification.

{
  "batch_id": "BATCH-9A2F4C11",
  "org_id": "ORG-SAMPLE-DEMO-01",
  "document_id": "DOC-PDF-9A2F4C11",
  "document_name": "Enterprise_Brand_Guidelines.pdf",
  "status": "PENDING_CONFIRMATION",
  "page_count": 2,
  "extraction_status": "OK",
  "prompt_shield_isolated": true,
  "pages": [
    {
      "page_number": 1,
      "char_count": 148,
      "extracted_text": "Never use 'guaranteed' in marketing copy. Always write brand name as AURORAGEAR.",
      "prompt_injection_signals_detected": false
    }
  ],
  "candidate_rules": [
    {
      "rule_id": "RULE-PDF-P1-001",
      "category": "BANNED_TERM",
      "title": "Extracted Banned Term: 'guaranteed'",
      "description": "Never use 'guaranteed' in marketing copy.",
      "mandatory_flag": true,
      "severity": "HIGH",
      "pattern_or_target": "guaranteed",
      "expected_replacement": null,
      "document_id": "DOC-PDF-9A2F4C11",
      "document_name": "Enterprise_Brand_Guidelines.pdf",
      "verified_page_or_row": 1,
      "version": "1.0",
      "campaign_scope": "GLOBAL"
    }
  ],
  "warnings": []
}

---

## 3. Sprint 1–3 Production Hardening & Final Handover Endpoints

### `GET /api/auth/me`
Returns the resolved server-side `TenantContext` (`user_id`, `org_id`, `role`, `is_demo_fallback`, `auth_mode`).
* When `REQUIRE_VERIFIED_TENANT_AUTH=true` (or `APP_ENV=production`), requires `Authorization: Bearer <HS256_JWT>`.
* If an authenticated user holds active memberships in multiple organisations, the request must specify the target organisation via `X-Demo-Org-Id` header or JWT `org_id` claim; otherwise returns `400 AMBIGUOUS_TENANT_MEMBERSHIP_SELECTION_REQUIRED`.

### `POST /api/brand/guidelines/upload-pdf` & `POST /api/brand/guidelines/{batch_id}/confirm`
* Uploads a Brand Guideline PDF (`multipart/form-data`, max 10 MB, max 50 pages), validates `%PDF-` signature and `PyMuPDF` structure, isolates untrusted text via PromptShield, and stages candidate rules in `PENDING_CONFIRMATION`.
* Rules become active in `brand_rules` only after `POST /api/brand/guidelines/{batch_id}/confirm`.

### `POST /api/brand/facts/upload-csv`
* Uploads an Approved Facts CSV (`multipart/form-data`, max 5 MB), validates required columns, persists valid facts under `tenant.org_id`, and returns structured `row_errors` for malformed or duplicate rows.

### `GET /api/brand/palette` & `POST /api/brand/palette`
* Lists and creates tenant-scoped `BrandPaletteItem` hex colours used by `VisualGuard` CIEDE2000 ($\Delta E$) checks.

### `POST /api/audits/{audit_id}/findings/{finding_id}/rewrite`
* Generates intent-preserving surgical rewrites on demand via `VoiceGuard` (or validates `custom_candidate_text`) and runs the fail-closed `RewriteValidationCoordinator` (`RuleGuard` + conditional `ClaimGuard`, zero recursive `VoiceGuard` calls).

### `GET /api/audits/{audit_id}/verify-snapshot`
* Reconstructs the canonical snapshot payload, looks up `snapshot.hmac_key_id` in the configured key ring (`HMAC_KEY_ID` + `HMAC_RETIRED_KEYS`), verifies the `HMAC-SHA256` signature in constant time, and verifies `previous_snapshot_hmac` chain continuity.
* Returns `SnapshotVerificationResponse` (`VALID`, `INVALID_SIGNATURE`, `UNKNOWN_KEY_ID`, `MALFORMED_SNAPSHOT`, `BROKEN_HASH_CHAIN`, or `NO_SNAPSHOT_FOUND`).

### `GET /api/audits/{audit_id}/export`
* Returns a tenant-scoped `ComplianceExportResponse` separating `machine_findings` (`RuleGuard`, `ClaimGuard`, `VisualGuard` with OCR telemetry, `VoiceGuard`) from `human_review_decision`, `snapshot_integrity`, `ai_disclosure_log`, and `simulated_cms_payload` (`approved_blocks` populated only when `overall_status == "APPROVED"` and `snapshot_integrity.is_valid == true`).