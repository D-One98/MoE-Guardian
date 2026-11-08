```markdown
# MoE-GUARDIAN — Project State & Development Progress

> **Project:** MoE-GUARDIAN (Powered by VERITY MoE)
> **Team:** THE MOE
> **Backend Owner:** Divy Mishra
> **Frontend Owner:** Lavanya Bani
> **Current Development Focus:** Round 2 End-to-End Integration

---

## 1. Project Overview

MoE-GUARDIAN is a pre-publication brand-governance and compliance system.

It evaluates marketing content against brand rules, approved facts, visual requirements, tone guidelines, and human approval workflows.

The system uses the VERITY MoE orchestration layer to coordinate specialist governance engines.

Core components:

- RuleGuard
- ClaimGuard
- VisualGuard
- VoiceGuard
- RewriteValidationCoordinator
- Maker-Checker Review Workflow
- HMAC-SHA256 Review Snapshots
- Compliance Export

---

## 2. Session 1 — Foundation

### Implemented

- Runnable FastAPI application.
- CORS configuration and Swagger documentation.
- Unified Pydantic v2 data contracts.
- Matching TypeScript interfaces.
- Deterministic RuleGuard engine.
- Baseline ClaimGuard engine.
- Canonical document-block anchoring.
- Maker-Checker review-state enforcement.
- HMAC-SHA256 audit snapshot signing.

### Important Files

- `backend/app/main.py`
- `backend/app/api/routes.py`
- `backend/app/schemas/contracts.py`
- `backend/app/engines/rule_guard.py`
- `backend/app/engines/claim_guard.py`
- `backend/app/services/anchoring.py`
- `backend/app/services/orchestrator.py`
- `shared/contracts.ts`

### Testing

Initial reported result:

**8 automated Pytest tests passing.**

---

## 3. Session 2 — Persistence & Governance Foundation

### 3.1 SQLAlchemy Persistence

Implemented SQLAlchemy 2.x persistence through:

- `backend/app/core/database.py`
- `backend/app/models/orm_models.py`
- `backend/app/repositories/governance_repo.py`

Documented persistent models:

- `BrandRuleModel`
- `ApprovedFactModel`
- `AuditRecordModel`
- `AuditFindingModel`
- `ReviewSnapshotModel`

Additional database behaviour:

- SQLite foreign-key enforcement.
- Idempotent demo seeding.
- Transaction rollback.
- Persistent governance records.

### 3.2 Brand Rule & Fact APIs

Implemented:

- `POST /api/brand/rules`
- `POST /api/brand/facts`

Capabilities:

- Custom rule creation.
- Approved-fact creation.
- Duplicate protection.
- Availability of newly ingested records to subsequent audits.

### 3.3 VisualGuard Baseline

Implemented static-image governance capabilities:

- PNG/JPEG validation.
- 5 MB image-size limit.
- 16 MP decompression-bomb protection.
- CIEDE2000 (ΔE) brand-palette comparison.
- Alternative-text validation.
- WCAG relative-luminance contrast checks.
- Insufficient-data escalation for uncertain visual regions.

### 3.4 HMAC Review Snapshots

Implemented:

- Canonical review snapshot signing.
- Review-note inclusion in the signed payload.
- Persistent snapshot storage.
- Previous-snapshot HMAC chaining.
- Snapshot tamper verification.

### 3.5 Session 2 Testing

Original Session 2 checkpoint:

**27 Pytest tests passing** across four test modules, as recorded in the original project-state document.

---

## 4. Subsequent Development — Task 1

### Brand Constitution Ingestion

Documented implementation:

- PDF guideline upload.
- PyMuPDF-based text extraction.
- PromptShield isolation of untrusted extracted text.
- Candidate-rule staging.
- Explicit confirmation workflow.

Endpoints:

- `POST /api/brand/guidelines/upload-pdf`
- `POST /api/brand/guidelines/{batch_id}/confirm`

Candidate rules enter:

`PENDING_CONFIRMATION`

They become active only after confirmation.

### Approved Facts CSV

Implemented endpoint:

`POST /api/brand/facts/upload-csv`

Documented capabilities:

- CSV validation.
- Required-column checks.
- Duplicate and malformed row reporting.
- Structured `row_errors`.
- Tenant-scoped fact persistence.

### Brand Palette APIs

Implemented endpoints:

- `GET /api/brand/palette`
- `POST /api/brand/palette`

The palette supports VisualGuard colour comparison.

### Testing Checkpoint

User-reported Task 1 result:

**36/36 tests passing.**

---

## 5. Subsequent Development — Task 2

### VoiceGuard

Documented capabilities:

- Tone and messaging analysis.
- On-demand rewrite generation.
- Intent-preserving rewrite suggestions.

### RewriteValidationCoordinator

Implemented workflow:

- Candidate rewrite validation.
- RuleGuard revalidation.
- Conditional ClaimGuard revalidation.
- Fail-closed validation behaviour.
- Prevention of recursive VoiceGuard calls.

Endpoint:

`POST /api/audits/{audit_id}/findings/{finding_id}/rewrite`

### Testing Checkpoint

User-reported Task 2 result:

**47/47 tests passing.**

---

## 6. Sprint 1 — Tenant Authentication & Security Hardening

Subsequent implementation notes document:

- HS256 JWT verification.
- Tenant context resolution.
- Organisation membership lookup.
- Server-side role resolution.
- Multi-membership organisation selection.
- Role-spoofing prevention.
- PostgreSQL RLS migration files.

Authentication endpoint:

`GET /api/auth/me`

Documented tenant context:

- `user_id`
- `org_id`
- `role`
- `is_demo_fallback`
- `auth_mode`

### Testing Checkpoint

User-reported authentication test result:

**55/55 tests passing.**

### Verification Boundary

SQLite-based tests do not execute PostgreSQL RLS policies.

PostgreSQL integration testing and cross-tenant isolation verification remain separate validation requirements.

---

## 7. Sprint 2 — VisualGuard OCR Integration

Subsequent implementation notes document Tesseract OCR integration.

Important implementation area:

`backend/app/services/ocr_service.py`

Documented capabilities:

- OCR text extraction.
- Bounding-box and confidence information.
- Confidence-threshold handling.
- Treatment of extracted text as untrusted input.
- Routing eligible OCR text through governance checks.
- Insufficient-data escalation for low-confidence or unavailable OCR.

### Testing Checkpoint

User-reported OCR test result:

**64/64 tests passing.**

### Remaining Boundary

OCR text extraction does not guarantee semantic correctness or reliable foreground/background colour separation.

---

## 8. Sprint 3 — Compliance Export & HMAC Hardening

Subsequent implementation notes document:

### HMAC Key Rotation

- Active key identification through `HMAC_KEY_ID`.
- Retired-key configuration through `HMAC_RETIRED_KEYS`.
- Historical snapshot verification.
- Signature verification.
- Hash-chain continuity checking.

### Snapshot Verification

Endpoint:

`GET /api/audits/{audit_id}/verify-snapshot`

### Compliance Export

Endpoint:

`GET /api/audits/{audit_id}/export`

Documented export components:

- Machine findings.
- Human review decision.
- Snapshot integrity.
- AI disclosure information.
- Simulated CMS payload.

The simulated CMS payload is gated by approval and snapshot-integrity conditions.

### Testing Checkpoint

User-reported final regression result:

**69/69 tests passing.**

This is the latest reported automated test checkpoint.

It does not independently establish production deployment, PostgreSQL RLS enforcement, or complete frontend integration.

---

## 9. Current Backend Capability Inventory

The following capabilities are documented as implemented in the current project state:

| Component | Documented Capability |
|---|---|
| FastAPI | Backend API application |
| Pydantic v2 | Structured request/response contracts |
| SQLAlchemy 2.x | Persistent governance records |
| RuleGuard | Deterministic brand-policy checks |
| ClaimGuard | Baseline claim verification |
| VisualGuard | Static-image validation |
| VoiceGuard | Tone and rewrite functionality |
| PromptShield | Isolation of untrusted guideline text |
| PDF Ingestion | Guideline extraction and confirmation |
| CSV Ingestion | Approved-fact import |
| Tenant Context | Authentication and organisation resolution |
| HMAC | Signed review snapshots and verification |
| Compliance Export | Structured governance export |

---

## 10. Remaining Work — Session 3

### Frontend Integration & End-to-End Workflow

**Status: Pending completion.**

Frontend development is owned by Lavanya Bani.

The existing React/TypeScript frontend must be connected to the latest backend implementation.

Integration scope:

- Workspace loading.
- Authentication and tenant context.
- Brand rules.
- Approved facts.
- PDF guideline upload and confirmation.
- CSV facts upload.
- Brand palette management.
- Canonical block editor.
- Audit creation.
- Inline findings.
- On-demand rewrite workflow.
- Maker-Checker review.
- Snapshot verification.
- Compliance export.

### Frontend Integration Requirements

- Synchronize TypeScript contracts with backend Pydantic schemas.
- Correct API base URL configuration.
- Integrate authentication headers.
- Handle structured backend errors.
- Preserve document block IDs.
- Handle stale findings and document revisions.
- Replace mock-dependent production behaviour with real API calls.

---

## 11. Remaining Work — Session 4

### Deployment & Production Hardening

**Status: Pending completion.**

Planned deployment targets:

- Frontend: Vercel.
- Backend: Render or Railway.
- Database: PostgreSQL.

Required work:

- Configure production environment variables.
- Configure CORS.
- Configure authentication secrets.
- Configure database connectivity.
- Validate tenant isolation.
- Configure native Tesseract dependencies.
- Configure HMAC signing keys.
- Run live deployment smoke tests.
- Verify public application accessibility.
- Test the application in an incognito browser session.

---

## 12. Round 3 — Planned Improvements

The following improvements are roadmap items and must not be represented as completed until implemented and tested.

### Improvement 01 — Advanced Claim Verification

Planned scope:

- Structured numeric units.
- Numeric ranges and comparators.
- Locale-aware numeric interpretation.
- Testing-condition qualifiers.
- Expiry and validity conditions.
- Contradiction detection across documents.

### Improvement 02 — Advanced Visual Understanding

Planned scope:

- Multi-page PDF and carousel analysis.
- Supplementary CLIP-based semantic similarity.
- More advanced visual-content evaluation.

### Improvement 03 — Advanced Governance Intelligence

Planned scope includes improvements such as:

- Guideline ambiguity signalling.
- Upload-time conflict detection.
- Advanced multi-stage privacy redaction.

The final scope must remain aligned with the original Round 1 proposal.

---

## 13. Project Completion Criteria

The Round 2 core workflow is considered complete only after:

- [ ] Backend APIs are integrated with the frontend.
- [ ] Guideline ingestion and confirmation work end-to-end.
- [ ] Approved facts can be created and imported.
- [ ] Brand palette management works.
- [ ] Document audits return usable findings.
- [ ] Rewrite suggestions are validated by the backend.
- [ ] Human review and approval work correctly.
- [ ] HMAC snapshot verification works.
- [ ] Compliance export works.
- [ ] Tenant authentication and isolation are validated.
- [ ] Frontend and backend pass end-to-end integration tests.
- [ ] Public deployment is accessible and verified.

---

**End of Project State Document**