# MoE-GUARDIAN — API Contract & Frontend Integration Guide

> **Product:** MoE-GUARDIAN (Powered by VERITY MoE)  
> **Team:** THE MOE  
> **Backend Framework:** FastAPI  
> **Frontend Framework:** React + TypeScript  
> **Schema Standard:** Pydantic v2  
> **Local Backend URL:** `http://localhost:8000`  
> **API Prefix:** `/api`  
> **Swagger Documentation:** `http://localhost:8000/docs`  
> **OpenAPI Specification:** `http://localhost:8000/openapi.json`

---

# 1. Purpose & Source of Truth

This document defines the API integration contract between the MoE-GUARDIAN frontend and backend.

It describes the available API endpoints, authentication requirements, governance workflows, request conventions, response behaviour, and frontend integration requirements.

### 1.1 Authoritative Backend Files

| Component | File |
|---|---|
| FastAPI Application | `backend/app/main.py` |
| API Routes | `backend/app/api/routes.py` |
| Pydantic Schemas | `backend/app/schemas/contracts.py` |
| Database Configuration | `backend/app/core/database.py` |
| ORM Models | `backend/app/models/orm_models.py` |
| Governance Repository | `backend/app/repositories/governance_repo.py` |
| Shared TypeScript Contracts | `shared/contracts.ts` |

**Source-of-truth policy:**

- Backend Pydantic schemas define the authoritative request and response structures.
- FastAPI route handlers define actual endpoint behaviour.
- `shared/contracts.ts` provides corresponding TypeScript interfaces.
- This document describes the intended frontend integration contract.

If any discrepancy exists, the actual backend implementation takes precedence. The documentation and TypeScript interfaces must then be synchronized.

---

# 2. API Configuration

## 2.1 Local Development

Configure the frontend environment:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

The centralized frontend API service should use this environment variable.

Example:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
```

Do not hardcode environment-specific backend URLs throughout frontend components.

## 2.2 API Request Conventions

| Request Type | Content-Type |
|---|---|
| JSON requests | `application/json` |
| PDF upload | `multipart/form-data` |
| CSV upload | `multipart/form-data` |
| Image data in audit request | JSON payload as defined by the backend schema |

For multipart uploads, allow the browser HTTP client to generate the multipart boundary automatically.

---

# 3. Authentication & Tenant Context

## 3.1 Authentication Endpoint

### `GET /api/auth/me`

Returns the server-resolved tenant context.

Documented context fields:

| Field | Description |
|---|---|
| `user_id` | Authenticated user identifier |
| `org_id` | Resolved organisation identifier |
| `role` | Server-resolved organisation role |
| `is_demo_fallback` | Indicates demo fallback context |
| `auth_mode` | Authentication mode used |

## 3.2 Verified Tenant Authentication

The documented production authentication configuration is:

- `REQUIRE_VERIFIED_TENANT_AUTH=true`
- Or `APP_ENV=production`

In this mode, a Bearer JWT is required.

Example:

```http
Authorization: Bearer <JWT>
```

The currently documented implementation uses HS256 JWT verification.

## 3.3 Organisation Selection

If an authenticated user has active memberships in multiple organisations, the target organisation must be selected through the supported mechanism:

- `X-Demo-Org-Id` header, or
- JWT `org_id` claim.

If organisation selection is ambiguous, the documented error is:

`400 AMBIGUOUS_TENANT_MEMBERSHIP_SELECTION_REQUIRED`

## 3.4 Tenant Security Rules

The following security principles apply:

1. JWT identity must be verified by the backend.
2. Organisation membership must be validated server-side.
3. Organisation roles must be resolved from trusted membership data.
4. Client-provided role values must not grant additional privileges.
5. Access to another organisation's records must be rejected unless an active membership permits it.
6. Production authentication must not silently fall back to demo access.

**Frontend restriction:** Never treat a role or organisation ID supplied by the browser as proof of authorization.

> **Implementation verification:** Confirm the exact JWT claim validation, authentication dependencies on individual routes, and production behaviour of `X-Demo-Org-Id` against the current backend before final deployment.

---

# 4. Enumerations & Standard Values

The following values are documented in the existing project API contract.

## 4.1 ExecutionState

| Value | Meaning |
|---|---|
| `OK` | Engine executed successfully |
| `NOT_APPLICABLE` | Engine was not applicable |
| `INSUFFICIENT_DATA` | Available information was insufficient |
| `ERROR` | Engine execution failed |

## 4.2 FindingType

- `DETERMINISTIC_VIOLATION`
- `FACTUAL_CLAIM`
- `TONE_MESSAGING`
- `VISUAL_A11Y_SUBSET`

## 4.3 VerificationStatus

- `SUPPORTED`
- `PARTIAL`
- `CONTRADICTED`
- `UNVERIFIABLE`
- `NOT_CLAIM_APPLICABLE`

## 4.4 Severity

- `CRITICAL`
- `HIGH`
- `MEDIUM`
- `LOW`
- `INFO`

## 4.5 AnchorResolutionStatus

- `RESOLVED_UNIQUE`
- `AMBIGUOUS_FALLBACK_TO_BLOCK`
- `UNRESOLVED_SIDEBAR_ONLY`

## 4.6 DemoRole

- `CREATOR`
- `BRAND_MANAGER`
- `AUTHORISED_REVIEWER`
- `WORKSPACE_ADMIN`

## 4.7 AuditStatus

- `PENDING_REVIEW`
- `READY_FOR_MANAGER_APPROVAL`
- `ESCALATED_TO_AUTHORISED_REVIEWER`
- `APPROVED`
- `CHANGES_REQUESTED`

## 4.8 OCR Status

The subsequent Sprint 2 documentation describes these OCR states. Confirm the exact enum against the current Pydantic schema.

- `NOT_REQUESTED`
- `OCR_SUCCESS`
- `OCR_NO_TEXT_DETECTED`
- `OCR_LOW_CONFIDENCE`
- `OCR_UNAVAILABLE`
- `OCR_FAILED`

## 4.9 SnapshotVerificationStatus

- `VALID`
- `INVALID_SIGNATURE`
- `UNKNOWN_KEY_ID`
- `MALFORMED_SNAPSHOT`
- `BROKEN_HASH_CHAIN`
- `NO_SNAPSHOT_FOUND`

---

# 5. Complete API Endpoint Inventory

The following inventory consolidates the 18 endpoints documented in the project handover.

| # | Method | Endpoint | Description |
|---:|---|---|---|
| 1 | GET | `/api/health` | Service health and version |
| 2 | GET | `/api/auth/me` | Resolve tenant context |
| 3 | GET | `/api/demo/workspace` | Load demo workspace |
| 4 | GET | `/api/brand/rules` | List brand rules |
| 5 | POST | `/api/brand/rules` | Create a brand rule |
| 6 | POST | `/api/brand/guidelines/upload-pdf` | Upload guideline PDF |
| 7 | POST | `/api/brand/guidelines/{batch_id}/confirm` | Confirm staged guideline rules |
| 8 | GET | `/api/brand/facts` | List approved facts |
| 9 | POST | `/api/brand/facts` | Create an approved fact |
| 10 | POST | `/api/brand/facts/upload-csv` | Upload approved facts CSV |
| 11 | GET | `/api/brand/palette` | List brand palette |
| 12 | POST | `/api/brand/palette` | Create palette entry |
| 13 | POST | `/api/audits` | Execute governance audit |
| 14 | GET | `/api/audits/{audit_id}` | Retrieve audit |
| 15 | POST | `/api/audits/{audit_id}/findings/{finding_id}/rewrite` | Generate or validate rewrite |
| 16 | POST | `/api/audits/{audit_id}/review` | Submit human review decision |
| 17 | GET | `/api/audits/{audit_id}/verify-snapshot` | Verify snapshot integrity |
| 18 | GET | `/api/audits/{audit_id}/export` | Retrieve compliance export |

> The endpoint count refers to documented endpoint entries. The live FastAPI OpenAPI specification should be used to confirm actual route registration and HTTP methods.

---

# 6. Workspace & Brand Management APIs

## 6.1 Health Check

### `GET /api/health`

Returns service health and version metadata.

**Purpose:**
- Check whether the backend is responding.
- Support deployment health checks.

## 6.2 Demo Workspace

### `GET /api/demo/workspace`

Returns the pre-seeded fictional AURORAGEAR demo workspace.

The existing documentation describes:

- Demo organisation information.
- Available demo roles.
- Brand-rule information.
- Approved-fact information.
- Sample drafts.

**Frontend usage:**

Use this endpoint to populate the initial demo workspace and sample-content selector.

## 6.3 List Brand Rules

### `GET /api/brand/rules`

Returns active brand rules associated with the resolved organisation.

**Frontend usage:**

- Display brand constitution rules.
- Populate the rule-management interface.
- Refresh the list after a successful rule creation or guideline confirmation.

## 6.4 Create Brand Rule

### `POST /api/brand/rules`

Creates a custom brand rule.

The existing project documentation specifies duplicate protection through:

`409 Conflict`

The exact request fields must follow the backend `BrandRule` schema.

## 6.5 List Approved Facts

### `GET /api/brand/facts`

Returns approved facts for the resolved organisation.

**Frontend usage:**

Display the organisation's Approved Facts Vault.

## 6.6 Create Approved Fact

### `POST /api/brand/facts`

Creates a new approved fact.

The existing project documentation specifies duplicate protection through:

`409 Conflict`

The request structure must follow the current Pydantic schema.

## 6.7 List Brand Palette

### `GET /api/brand/palette`

Returns organisation-scoped brand palette entries.

These entries are used by VisualGuard for colour comparisons.

## 6.8 Create Brand Palette Entry

### `POST /api/brand/palette`

Creates a new brand palette item.

The documented palette uses hexadecimal colour values.

Example colour:

`#0F172A`

The exact request fields and validation limits must follow the backend schema.

---

# 7. Brand Guideline PDF Ingestion

The PDF ingestion workflow allows administrators to upload brand guidelines, inspect extracted candidate rules, and explicitly confirm which rules should become active.

## 7.1 Upload Guideline PDF

### `POST /api/brand/guidelines/upload-pdf`

**Content-Type:** `multipart/form-data`

**Form field:** `file`

Documented constraints:

| Constraint | Limit |
|---|---:|
| Maximum file size | 10 MB |
| Maximum page count | 50 pages |
| File signature | `%PDF-` |
| PDF parser | PyMuPDF |

### Processing Workflow

1. Receive the PDF file.
2. Validate the PDF signature.
3. Validate PDF structure.
4. Extract available text using PyMuPDF.
5. Isolate untrusted extracted content using PromptShield.
6. Generate candidate brand rules.
7. Store the ingestion batch in a pending-confirmation state.
8. Return the preview information to the frontend.

Initial batch state:

`PENDING_CONFIRMATION`

### Illustrative Response

The following is an illustrative response excerpt, not a complete schema definition.

```json
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
```

### Important Frontend Behaviour

- Display the extracted text.
- Display candidate rules.
- Clearly identify the pending-confirmation state.
- Allow the authorised user to inspect and edit candidate rules where supported.
- Do not automatically activate extracted rules.

## 7.2 Confirm Guideline Rules

### `POST /api/brand/guidelines/{batch_id}/confirm`

This endpoint confirms staged guideline rules.

Documented workflow:

1. Identify the ingestion batch.
2. Submit the confirmation request.
3. Validate the submitted rules.
4. Activate the confirmed rules.
5. Make the rules available to subsequent governance audits.

The existing handover describes the request model as:

`GuidelineConfirmRequest`

The exact accepted fields must be read from the current Pydantic schema.

### Illustrative Request

```json
{
  "brand_constitution_version": "1.1",
  "confirmed_rules": [
    {
      "rule_id": "RULE-PDF-P1-001",
      "category": "BANNED_TERM",
      "title": "Prohibit guaranteed",
      "description": "Never use guaranteed in promotional copy.",
      "mandatory_flag": true,
      "severity": "HIGH",
      "pattern_or_target": "guaranteed",
      "document_id": "DOC-PDF-1A2B3C4D",
      "document_name": "Brand_Guidelines.pdf",
      "verified_page_or_row": 1,
      "version": "1.1",
      "campaign_scope": "GLOBAL"
    }
  ]
}
```

> This is an illustrative integration example. Verify optional fields, required fields, and exact response structure against `GuidelineConfirmRequest` before using it as a production payload.

---

# 8. Approved Facts CSV Ingestion

## 8.1 Upload CSV

### `POST /api/brand/facts/upload-csv`

**Content-Type:** `multipart/form-data`

**Form field:** `file`

Documented maximum file size:

`5 MB`

### Processing Behaviour

1. Receive the CSV.
2. Validate the required columns.
3. Validate individual rows.
4. Identify malformed or duplicate records.
5. Persist valid facts under the resolved organisation.
6. Return structured row-level errors.

The documented response model is:

`CsvFactsUploadResponse`

The response is described as containing:

- `saved_facts_count`
- `saved_facts`
- `row_errors`

The documented row-error information includes:

- `row_number`
- `fact_id`
- `error_code`
- `message`

### Frontend Requirements

- Provide a CSV file selector.
- Show upload progress.
- Display successful record count.
- Display row-level validation errors.
- Do not report the entire upload as successful if some rows failed.

The exact required CSV column names and delimiter rules must be confirmed against the ingestion implementation.

---

# 9. Governance Audit API

## 9.1 Create Audit

### `POST /api/audits`

This endpoint executes the VERITY MoE governance workflow.

Documented specialist components:

1. RuleGuard
2. ClaimGuard
3. VisualGuard
4. VoiceGuard
5. Privacy Gate

The request model is documented as:

`AuditCreateRequest`

### Illustrative Request

```json
{
  "campaign_id": "CAMP-LAUNCH-2026",
  "submitted_by_role": "CREATOR",
  "blocks": [
    {
      "document_block_id": "blk-p1",
      "text": "AURORAGEAR delivers 12 hours of guaranteed battery life on a single charge!"
    }
  ],
  "alt_text": null
}
```

### Request Concepts

| Field | Purpose |
|---|---|
| `campaign_id` | Identifies the campaign |
| `submitted_by_role` | Role-related request information in the documented demo contract |
| `blocks` | Canonical document content blocks |
| `document_block_id` | Stable block identifier |
| `text` | Text to evaluate |
| `alt_text` | Optional alternative-text information |

The actual accepted fields must follow the current Pydantic request model.

### Illustrative Visual Asset Structure

The existing Sprint 2 handover describes visual asset information including:

```json
{
  "document_block_id": "blk-img-01",
  "filename": "promo_banner.png",
  "mime_type": "image/png",
  "image_base64": "<base64-encoded-image>",
  "alt_text": "AURORAGEAR navy workstation banner",
  "declared_foreground_hex": "#FFFFFF",
  "declared_background_hex": "#0F172A",
  "enable_ocr": true,
  "ocr_min_confidence": 60.0
}
```

This illustrates the documented visual-asset fields. Its exact nesting and accepted request structure must match the current `AuditCreateRequest` schema.

### Audit Response

The existing contract documents the response model:

`AuditResponse`

The response is described as containing:

- `audit_id`
- `document_revision_hash`
- `overall_status`
- `engine_executions`
- `findings`
- `ai_disclosure_log`

Individual findings may contain:

- Finding information.
- Severity.
- Verification information.
- Evidence references.
- Rewrite candidate information.
- Anchor-resolution information.

The frontend must display the backend's actual response rather than deriving governance decisions independently.

## 9.2 Retrieve Audit

### `GET /api/audits/{audit_id}`

Retrieves a previously persisted audit.

Documented response model:

`AuditResponse`

The frontend should use this endpoint to retrieve the latest persisted audit state.

The frontend must handle a missing audit without assuming that the record exists.

---

# 10. VisualGuard & OCR Integration

VisualGuard evaluates uploaded visual assets against documented brand and accessibility requirements.

## 10.1 Baseline Image Validation

Documented capabilities:

- PNG/JPEG validation.
- 5 MB image-size limit.
- 16 MP decompression-bomb protection.
- CIEDE2000 (ΔE) palette comparison.
- `alt_text` validation.
- WCAG relative-luminance contrast checks.

## 10.2 OCR Integration

Subsequent Sprint 2 documentation describes Tesseract OCR integration.

Documented behaviour:

1. OCR extracts text from the submitted image.
2. Confidence information is collected.
3. Extracted text is treated as untrusted input.
4. Eligible extracted text is routed through governance checks.
5. Low-confidence or unavailable OCR results must not create invented violations.
6. Uncertain results are escalated using insufficient-data behaviour.

### OCR Telemetry

The handover documentation describes these telemetry fields:

- `ocr_status`
- `mean_confidence`
- `regions_count`
- `governance_evaluated`

The exact response location and field names must be synchronized with the backend Pydantic response schema.

### Frontend Requirements

- Display OCR-related findings when returned.
- Distinguish OCR failure from a genuine policy violation.
- Display insufficient-data results accurately.
- Do not treat extracted OCR text as user-approved evidence.

---

# 11. On-Demand Rewrite API

## 11.1 Generate or Validate Rewrite

### `POST /api/audits/{audit_id}/findings/{finding_id}/rewrite`

This endpoint supports on-demand rewrite generation and custom candidate validation.

The documented implementation uses:

- VoiceGuard.
- RewriteValidationCoordinator.
- RuleGuard.
- Conditional ClaimGuard.

### Illustrative Request

```json
{
  "custom_candidate_text": "AURORAGEAR provides up to 12 hours of battery life under specified laboratory testing conditions.",
  "preserve_tone_notes": "confident and accurate"
}
```

The documented request model is:

`OnDemandRewriteRequest`

### Validation Behaviour

1. Identify the audit and finding.
2. Generate a rewrite or accept custom candidate text.
3. Run the candidate through the validation coordinator.
4. Evaluate applicable deterministic rules.
5. Evaluate applicable factual claims.
6. Return the backend-generated validation result.

### Security & Validation Rules

- The frontend must not assign `revalidation_passed`.
- The frontend must not manufacture `candidate_verification_status`.
- The backend must determine the final validation result.
- Invalid candidate text must not be represented as approved.
- Original creator content must remain unchanged unless the user explicitly applies an accepted suggestion.

---

# 12. Maker-Checker Human Review

## 12.1 Submit Review Decision

### `POST /api/audits/{audit_id}/review`

Records a human review decision and generates a signed review snapshot according to the documented workflow.

The existing contract identifies:

`ReviewDecisionRequest`

### Illustrative Request

```json
{
  "actor_role": "AUTHORISED_REVIEWER",
  "decision": "APPROVE",
  "override_justification": "Approved for internal teaser with lab testing footnote."
}
```

> This example reflects the earlier demo-oriented contract. In verified tenant-authentication mode, authorization must be based on the authenticated server-side role, not a client-provided `actor_role`. Confirm whether the current schema still accepts this field.

### Maker-Checker Rules

The documented workflow includes:

- A creator must not approve their own submission.
- Escalated audits require an appropriately authorised reviewer.
- Non-supported findings may require an override justification before approval.

The backend remains authoritative for review permissions and decisions.

### Frontend Responsibilities

- Display the available review actions.
- Display the authenticated reviewer's context.
- Collect override justification where required.
- Submit the review request.
- Display the backend's resulting decision.
- Never generate HMAC signatures in the browser.

---

# 13. Review Snapshot Verification

## 13.1 Verify Snapshot

### `GET /api/audits/{audit_id}/verify-snapshot`

Returns the documented:

`SnapshotVerificationResponse`

### Verification Process

The backend documentation describes the following operations:

1. Reconstruct the canonical snapshot payload.
2. Retrieve the signing key using the snapshot key identifier.
3. Resolve the active or retired signing key.
4. Verify the HMAC-SHA256 signature.
5. Verify previous-snapshot hash-chain continuity.
6. Return the verification result.

### Documented Verification States

| Status | Meaning |
|---|---|
| `VALID` | Snapshot signature and required integrity checks passed |
| `INVALID_SIGNATURE` | Signature verification failed |
| `UNKNOWN_KEY_ID` | Signing key could not be identified |
| `MALFORMED_SNAPSHOT` | Snapshot structure is invalid |
| `BROKEN_HASH_CHAIN` | Previous-snapshot chain verification failed |
| `NO_SNAPSHOT_FOUND` | No review snapshot exists |

### Illustrative Response

```json
{
  "audit_id": "AUD-1A2B3C4D",
  "org_id": "ORG-SAMPLE-DEMO-01",
  "snapshot_id": "SNAP-9F8E7D6C",
  "hmac_key_id": "key-v2-2026",
  "is_valid": true,
  "status_code": "VALID",
  "chain_integrity_verified": true,
  "message": "Snapshot signature verified successfully."
}
```

This is an illustrative example, not a guaranteed complete response schema.

### Frontend Behaviour

- Show the returned verification status.
- Display integrity failure clearly.
- Do not independently mark a snapshot valid.
- Do not modify snapshot data.

---

# 14. Compliance Export

## 14.1 Export Audit

### `GET /api/audits/{audit_id}/export`

Returns the documented:

`ComplianceExportResponse`

### Export Components

The documented response separates:

| Component | Description |
|---|---|
| `machine_findings` | Findings from governance engines |
| `human_review_decision` | Human review outcome |
| `snapshot_integrity` | Snapshot verification information |
| `ai_disclosure_log` | AI and engine execution disclosures |
| `simulated_cms_payload` | Simulated publication payload |

### Machine Findings

The project documentation describes findings from:

- RuleGuard
- ClaimGuard
- VisualGuard
- VoiceGuard

VisualGuard may also provide OCR-related telemetry.

### CMS Approval Safeguard

The documented export behaviour requires both conditions:

```text
overall_status == "APPROVED"
```

and

```text
snapshot_integrity.is_valid == true
```

Only when both conditions hold should `approved_blocks` be populated in the simulated CMS payload.

**Important:** This is a simulated CMS payload. It does not establish a live external CMS publishing integration.

---

# 15. Standard Error Handling

The existing API contract documents structured domain errors in the following form:

```json
{
  "detail": {
    "error": "ERROR_CODE_CONSTANT",
    "message": "Human-readable explanation of the failure."
  }
}
```

### Common HTTP Status Categories

| HTTP Status | Meaning | Frontend Behaviour |
|---|---|---|
| `200` | Successful request | Process response |
| `201` | Resource created | Update UI state |
| `400` | Invalid request or selection | Display actionable message |
| `401` | Authentication required or invalid | Handle authentication state |
| `403` | Insufficient permission | Display access-denied message |
| `404` | Resource not found | Display not-found state |
| `409` | Duplicate or conflicting operation | Display conflict message |
| `422` | Request validation failure | Display validation errors |
| `500` | Internal server failure | Display safe error message |

These are common HTTP categories, not a guarantee that every endpoint uses each status.

FastAPI validation errors may have a different structure from custom domain errors.

The frontend must handle both structured domain errors and framework-level validation responses.

### Error Handling Rules

- Never display stack traces to end users.
- Never expose access tokens or secrets.
- Preserve useful validation messages.
- Distinguish authentication errors from authorization errors.
- Provide retry behaviour only where appropriate.
- Do not silently discard failed uploads or review requests.

---

# 16. Frontend Integration Standards

## 16.1 Centralized API Service

All backend requests should pass through a centralized API service.

Recommended responsibilities:

- Base URL configuration.
- Authentication headers.
- JSON request handling.
- Multipart upload handling.
- Response parsing.
- Error normalization.
- TypeScript response typing.

Avoid duplicating API request logic across UI components.

## 16.2 Canonical Document Block Identity

The frontend must preserve:

- `document_block_id`
- Document revision information.
- Backend-provided evidence references.
- Finding-to-block relationships.

Do not use array indexes as permanent document block identifiers.

## 16.3 Stale Finding Protection

When a document changes after an audit:

1. Recognize that previous findings may refer to an older revision.
2. Do not present stale findings as current validation.
3. Require a new audit where applicable.
4. Use backend-provided revision and audit information to determine current state.

## 16.4 Human Review & Machine Findings

Keep these separate:

1. Machine-generated findings.
2. Rewrite suggestions.
3. Rewrite-validation results.
4. Human review decisions.
5. Snapshot-integrity results.
6. Compliance export.

A machine finding is not a human approval decision.

A rewrite suggestion is not automatically a validated rewrite.

A successful review request is not proof of snapshot integrity until verification succeeds.

## 16.5 Mock Adapter

Mock data may be used during frontend development.

Before deployment:

- Disable unintended mock mode.
- Configure the actual backend URL.
- Integrate authentication.
- Test the real API responses.
- Verify upload and review workflows.

---

# 17. API Integration Testing Checklist

## Authentication & Workspace

- [ ] Health endpoint responds.
- [ ] Authentication context resolves correctly.
- [ ] Demo workspace loads correctly.
- [ ] Organisation selection works as expected.
- [ ] Unauthorised tenant access is rejected.

## Brand Management

- [ ] Brand rules load.
- [ ] Custom rules can be created.
- [ ] Approved facts load.
- [ ] Approved facts can be created.
- [ ] Brand palette loads.
- [ ] Brand palette entries can be created.

## Knowledge Ingestion

- [ ] PDF upload works.
- [ ] PDF extraction preview is displayed.
- [ ] Candidate rules remain pending until confirmation.
- [ ] Confirmed rules become available to audits.
- [ ] CSV upload works.
- [ ] CSV row errors are displayed correctly.

## Governance Audit

- [ ] Audit creation works.
- [ ] Document block IDs are preserved.
- [ ] Findings are displayed correctly.
- [ ] Evidence references are preserved.
- [ ] Engine execution states are displayed.
- [ ] Document revision information is handled correctly.

## Rewrite & Human Review

- [ ] On-demand rewrite works.
- [ ] Custom candidate validation works.
- [ ] Backend validation results are displayed.
- [ ] Maker-Checker restrictions are enforced.
- [ ] Review decisions are persisted.
- [ ] Override justification is handled correctly.

## Integrity & Export

- [ ] Snapshot verification endpoint works.
- [ ] Verification states are displayed correctly.
- [ ] Compliance export works.
- [ ] Simulated CMS approval conditions are respected.

## Final Integration

- [ ] Frontend TypeScript validation passes.
- [ ] Frontend production build passes.
- [ ] Real backend integration works.
- [ ] Authentication headers are correctly propagated.
- [ ] No unintended mock mode remains.
- [ ] End-to-end workflow passes.

---

# 18. Contract Synchronization & Maintenance

Whenever the backend API changes:

1. Update the Pydantic request/response models.
2. Update the corresponding FastAPI route behaviour.
3. Update `shared/contracts.ts`.
4. Update this API documentation.
5. Verify frontend API service compatibility.
6. Run backend and frontend tests.

### Final Source-of-Truth Hierarchy

| Priority | Source |
|---:|---|
| 1 | Actual backend route implementation |
| 2 | Pydantic request/response schemas |
| 3 | Live FastAPI OpenAPI specification |
| 4 | Shared TypeScript contracts |
| 5 | This documentation |

The frontend must integrate with the actual backend behaviour rather than assumptions based on outdated examples.

---

**End of API Contract & Frontend Integration Guide**