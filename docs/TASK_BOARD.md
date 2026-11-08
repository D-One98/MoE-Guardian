# MoE-GUARDIAN — Team Task Board

> **Team:** THE MOE
> **Project:** MoE-GUARDIAN (Powered by VERITY MoE)

---

## 1. Team Responsibilities

### Divy Mishra — Backend, AI Orchestration, Security & DevOps

Primary ownership:

- Backend architecture.
- FastAPI development.
- Pydantic contracts.
- Database and repository layer.
- Governance engine orchestration.
- Authentication and tenant security.
- HMAC snapshot integrity.
- Backend/frontend integration.
- Code review and merge.
- Deployment and final submission.

### Lavanya Bani — Frontend, UX & Frontend Integration

Primary ownership:

- React/TypeScript frontend.
- Workspace UI.
- Document editor.
- Findings and review interface.
- Frontend API service integration.
- UI state and error handling.
- Frontend build and TypeScript validation.
- Frontend pull request.

**Boundary:** Backend source code and the old backend snapshot bundled in the frontend archive are not part of Lavanya's assigned work.

---

## 2. Divy Mishra — Backend & Infrastructure Tasks

### Foundation

- [x] FastAPI application foundation.
- [x] Unified Pydantic v2 contracts.
- [x] Shared TypeScript contract foundation.
- [x] RuleGuard baseline.
- [x] ClaimGuard baseline.
- [x] VERITY MoE orchestration foundation.
- [x] Canonical document-block anchoring.
- [x] Maker-Checker review-state foundation.
- [x] HMAC-SHA256 snapshot signing.

### Session 2 — Persistence & Governance

- [x] SQLAlchemy 2.x database layer.
- [x] ORM models.
- [x] GovernanceRepository.
- [x] SQLite foreign-key enforcement.
- [x] Idempotent demo seeding.
- [x] Brand rule creation API.
- [x] Approved fact creation API.
- [x] VisualGuard baseline.
- [x] Persistent audit records and findings.
- [x] Persistent review snapshots.

### Task 1 — Knowledge Ingestion

- [x] PDF guideline upload workflow.
- [x] PyMuPDF extraction.
- [x] PromptShield isolation.
- [x] Candidate-rule staging.
- [x] Guideline confirmation workflow.
- [x] Approved Facts CSV ingestion.
- [x] Brand palette APIs.

### Task 2 — VoiceGuard

- [x] VoiceGuard implementation.
- [x] On-demand rewrite endpoint.
- [x] Custom candidate validation.
- [x] Fail-closed RewriteValidationCoordinator.
- [x] RuleGuard rewrite revalidation.
- [x] Conditional ClaimGuard rewrite revalidation.
- [x] Prevention of recursive VoiceGuard calls.

### Sprint 1 — Tenant Authentication & Security

- [x] HS256 JWT authentication implementation.
- [x] Tenant context resolution.
- [x] Organisation membership lookup.
- [x] Server-side role resolution.
- [x] Multi-membership selection handling.
- [x] Role-spoofing protection.
- [x] PostgreSQL RLS migration files.

### Sprint 2 — OCR Integration

- [x] Tesseract OCR service integration.
- [x] OCR confidence handling.
- [x] Bounding-box information.
- [x] Untrusted OCR text handling.
- [x] Governance routing for extracted text.
- [x] Insufficient-data escalation for uncertain OCR results.

### Sprint 3 — Compliance & HMAC Hardening

- [x] HMAC key identification.
- [x] Retired-key configuration.
- [x] Snapshot verification endpoint.
- [x] Hash-chain continuity verification.
- [x] Compliance export endpoint.
- [x] Simulated CMS approval safeguard.
- [x] Reported 69/69 automated test checkpoint.

### Session 3 — Integration

- [ ] Synchronize `shared/contracts.ts` with current Pydantic schemas.
- [ ] Finalize `docs/API_CONTRACT.md`.
- [ ] Review frontend PR.
- [ ] Verify frontend API base URL.
- [ ] Integrate authentication and tenant context.
- [ ] Integrate real API service calls.
- [ ] Resolve CORS and API error mapping.
- [ ] Verify document block identity and revision handling.
- [ ] Integrate guideline PDF upload and confirmation.
- [ ] Integrate CSV facts upload.
- [ ] Integrate palette management.
- [ ] Integrate audit creation and findings.
- [ ] Integrate rewrite workflow.
- [ ] Integrate Maker-Checker review.
- [ ] Integrate snapshot verification.
- [ ] Integrate compliance export.
- [ ] Merge frontend with the latest backend source.

### Session 4 — Deployment & DevOps

- [ ] Configure production environment variables.
- [ ] Deploy FastAPI backend.
- [ ] Configure PostgreSQL.
- [ ] Configure authentication secrets.
- [ ] Configure HMAC signing keys.
- [ ] Configure native Tesseract dependencies.
- [ ] Configure production CORS.
- [ ] Deploy frontend.
- [ ] Run live API smoke tests.
- [ ] Verify tenant isolation.
- [ ] Verify public application accessibility.
- [ ] Test public application in incognito mode.
- [ ] Complete final Round 2 submission checks.

---

## 3. Lavanya Bani — Frontend Tasks

### Frontend Foundation

- [ ] Review existing React/TypeScript frontend.
- [ ] Preserve existing frontend architecture.
- [ ] Synchronize frontend types with the latest shared contracts.
- [ ] Configure API base URL through environment variables.
- [ ] Prepare centralized API service functions.
- [ ] Run TypeScript checks.
- [ ] Run frontend production build.

### Workspace & Brand Management

- [ ] Connect demo workspace API.
- [ ] Display organisation workspace information.
- [ ] Implement brand rules listing.
- [ ] Implement custom brand rule creation.
- [ ] Implement approved facts listing.
- [ ] Implement custom approved fact creation.
- [ ] Implement brand palette management.

### Knowledge Ingestion

- [ ] Implement PDF guideline upload UI.
- [ ] Display extracted guideline content.
- [ ] Display candidate rules.
- [ ] Implement confirmation workflow.
- [ ] Implement Approved Facts CSV upload.
- [ ] Display row-level validation errors.

### Governance Editor

- [ ] Implement canonical document block editor.
- [ ] Preserve `document_block_id`.
- [ ] Display audit findings.
- [ ] Display evidence references.
- [ ] Display finding severity and verification status.
- [ ] Handle anchor-resolution states.
- [ ] Handle stale findings after document changes.

### Visual & Rewrite Workflow

- [ ] Implement visual asset upload.
- [ ] Display VisualGuard findings.
- [ ] Display OCR-related findings and telemetry where available.
- [ ] Implement on-demand rewrite UI.
- [ ] Display backend rewrite-validation results.
- [ ] Preserve original creator text.

### Human Review & Compliance

- [ ] Implement Maker-Checker review panel.
- [ ] Display available review actions.
- [ ] Handle review justification.
- [ ] Display human review decision.
- [ ] Display snapshot verification status.
- [ ] Implement compliance export UI.
- [ ] Display simulated CMS payload where available.

### Frontend Delivery

- [ ] Run TypeScript validation.
- [ ] Run frontend build.
- [ ] Verify API service behaviour.
- [ ] Raise a separate frontend pull request.
- [ ] Document frontend changes and known limitations.

---

## 4. Shared Integration Tasks

- [ ] Agree on final API contracts.
- [ ] Verify all documented endpoints.
- [ ] Verify request/response schemas.
- [ ] Verify authentication behaviour.
- [ ] Verify organisation-scoped access.
- [ ] Test guideline ingestion end-to-end.
- [ ] Test CSV ingestion end-to-end.
- [ ] Test document audit workflow.
- [ ] Test rewrite validation.
- [ ] Test Maker-Checker review.
- [ ] Test HMAC snapshot verification.
- [ ] Test compliance export.
- [ ] Verify frontend error handling.
- [ ] Verify complete workflow in a fresh browser session.

---

## 5. Ownership & Merge Policy

1. Backend remains under Divy's ownership.
2. Frontend work remains under Lavanya's ownership.
3. Frontend changes should be submitted through a separate pull request.
4. The old backend snapshot inside the frontend archive must not replace the current backend.
5. Divy reviews and merges the frontend changes.
6. Divy handles final backend/frontend integration and deployment.
7. Any shared contract change must be coordinated before integration.

---

## 6. Progress Reporting Rules

Task status must reflect actual work.

- `[ ]` Not completed.
- `[x]` Completed.
- A task is not complete merely because code has been written.
- Integration tasks require connected-component verification.
- Deployment tasks require live-environment verification.
- Production security claims require corresponding security tests.

---

**End of Task Board**