# MoE-GUARDIAN — Bug Log & Known Technical Limitations

> **Purpose:** Track resolved defects, documented design boundaries, and remaining technical risks.
>
> **Rule:** A limitation must not be marked resolved unless the corresponding implementation and verification evidence exist.

---

## 1. Status Definitions

| Status | Meaning |
|---|---|
| Open | Issue requires investigation or implementation. |
| In Progress | Work is currently underway. |
| Resolved | Fix has been implemented and verified. |
| Documented Design Boundary | Known limitation accepted within the current scope. |
| Verification Required | Implementation or configuration exists, but required validation remains outstanding. |

---

## 2. Bug & Limitation Register

| ID | Severity | Component | Description | Status |
|---|---|---|---|---|
| LIM-001 | LOW | `anchoring.py` | Identical repeated substrings with indistinguishable prefix/suffix context may return `AMBIGUOUS_FALLBACK_TO_BLOCK`. The UI should use block-level fallback instead of placing an unreliable inline highlight. | Documented Design Boundary |
| LIM-002 | LOW | `orchestrator.py` | Earlier in-memory dictionary storage was replaced by SQLAlchemy persistence for governance records, findings, and review snapshots. | Resolved in Session 2 |
| LIM-003 | MEDIUM | `claim_guard.py` | Baseline ClaimGuard uses deterministic matching. Advanced unit conversion, locale-aware numeric interpretation, testing-condition evaluation, expiry handling, and cross-document contradiction detection remain future improvements. | Documented Round 2 Boundary |
| LIM-004 | MEDIUM | `visual_guard.py` | VisualGuard can return `INSUFFICIENT_DATA` when foreground/background regions cannot be reliably isolated. OCR text extraction does not automatically solve contrast-region identification for gradients and complex photographs. | Documented Design Boundary |
| LIM-005 | MEDIUM | `tenant_context.py` | Subsequent implementation notes describe HS256 JWT verification and server-side membership resolution. Exact production issuer/audience configuration and live authentication behaviour require environment-level verification. | Verification Required |
| LIM-006 | HIGH | `migrations/*.sql` | PostgreSQL RLS migration files are documented. SQLite tests do not execute PostgreSQL RLS policies. Live PostgreSQL policy enforcement and cross-tenant isolation must be tested independently. | Verification Required |
| LIM-007 | MEDIUM | OCR Service | Tesseract OCR depends on native executable and language-data availability in the runtime environment. Deployment must verify these dependencies. | Verification Required |
| LIM-008 | MEDIUM | Frontend Integration | Frontend API integration, authentication headers, stale-finding handling, and complete end-to-end workflow remain pending until the frontend is connected and tested against the latest backend. | Open |
| LIM-009 | MEDIUM | Compliance Export | The CMS payload is simulated. A live external CMS publishing integration is not established by the documented export endpoint. | Documented Scope Boundary |
| LIM-010 | HIGH | HMAC Configuration | Snapshot integrity depends on secure signing-key configuration, key retention, and protection against key exposure. Production key management must be validated before deployment. | Verification Required |

---

## 3. Detailed Known Limitations

### 3.1 ClaimGuard — Baseline Verification

Current documented capability:

- `SUPPORTED`
- `PARTIAL`
- `CONTRADICTED`
- `UNVERIFIABLE`

Known boundaries:

- Complex unit conversion.
- Locale-dependent numeric interpretation.
- Advanced comparator evaluation.
- Multi-document contradiction detection.
- Testing-condition and expiry reasoning.

These are planned improvements and must not be represented as fully supported baseline features.

### 3.2 VisualGuard — Contrast Analysis

VisualGuard supports static-image checks and relative-luminance contrast analysis when the required foreground/background information is reliable.

However:

- Complex gradients may prevent reliable region isolation.
- Photographic backgrounds may contain multiple competing colours.
- OCR bounding boxes do not automatically establish pixel-level foreground/background colour values.

The correct behaviour in uncertain cases is to report insufficient data rather than invent a contrast result.

### 3.3 OCR Reliability

OCR extraction is not equivalent to verified semantic understanding.

Potential limitations include:

- Low-confidence extraction.
- Incorrect character recognition.
- Text embedded in complex backgrounds.
- Missing native Tesseract dependencies.
- Language-data configuration.

Extracted text must remain untrusted input and must pass through the relevant governance checks.

### 3.4 Tenant Security & PostgreSQL RLS

The project documentation describes tenant authentication and PostgreSQL RLS migrations.

Important distinction:

- Application-level tenant filtering is not the same as database-enforced RLS.
- SQLite does not execute PostgreSQL RLS policies.
- Migration files alone do not establish that policies work correctly.
- Membership-management policies require special attention because incorrect policy conditions may create privilege-escalation risks.

Required verification:

- Test two separate organisations.
- Attempt cross-tenant record access.
- Test inactive memberships.
- Test organisation selection.
- Test role escalation attempts.
- Verify RLS under the actual application database role.

### 3.5 Authentication Configuration

The documented authentication mode uses HS256 JWT verification.

Before production deployment, verify:

- JWT signature verification.
- Expiration validation.
- Not-before validation.
- Issuer validation where configured.
- Audience validation where configured.
- Server-side membership lookup.
- Organisation-selection behaviour.
- Demo fallback restrictions.

If the identity provider uses asymmetric signing, the authentication implementation must support the actual signing configuration rather than assuming HS256 compatibility.

### 3.6 HMAC Key Management

HMAC signatures establish integrity only while the signing secret remains protected.

Required operational safeguards:

- Strong signing secrets.
- Secure environment-variable storage.
- Explicit active key identification.
- Retention of required retired keys.
- Protection against accidental key disclosure.
- Verification of historical snapshots after rotation.

### 3.7 Frontend Integration

The frontend must not assume that backend capabilities are fully integrated merely because the corresponding API exists.

Potential integration issues:

- Incorrect API base URL.
- Missing authentication headers.
- Stale TypeScript contracts.
- Inconsistent error handling.
- Stale findings after document edits.
- Missing multipart upload handling.
- Incorrect review-role UI.
- Snapshot verification state not displayed correctly.

These must be addressed during Session 3 integration.

---

## 4. Resolved Testing Checkpoints

The following regression checkpoints were reported during development:

| Checkpoint | Reported Result |
|---|---:|
| Initial Foundation | 8/8 |
| Task 1 | 36/36 |
| Task 2 | 47/47 |
| Tenant Authentication | 55/55 |
| OCR Integration | 64/64 |
| Compliance Export & HMAC Hardening | 69/69 |

**Latest reported result: 69/69 tests passing.**

These are reported development checkpoints, not proof that every production integration has been verified.

---

## 5. Open Verification Checklist

### Backend

- [ ] Verify all documented routes against FastAPI route registration.
- [ ] Verify Pydantic request and response schemas.
- [ ] Verify endpoint-level authorization dependencies.
- [ ] Verify JWT issuer and audience configuration.
- [ ] Verify tenant membership enforcement.
- [ ] Review PostgreSQL RLS policies.
- [ ] Execute PostgreSQL cross-tenant isolation tests.
- [ ] Verify HMAC key rotation in a real configured environment.
- [ ] Verify Tesseract installation and language data.

### Frontend

- [ ] Verify API base URL.
- [ ] Verify authentication header propagation.
- [ ] Verify frontend contract synchronization.
- [ ] Verify PDF and CSV uploads.
- [ ] Verify document block anchoring.
- [ ] Verify stale-finding handling.
- [ ] Verify rewrite-validation display.
- [ ] Verify Maker-Checker workflow.
- [ ] Verify snapshot verification display.
- [ ] Verify compliance export.

### Deployment

- [ ] Verify environment variables.
- [ ] Verify CORS.
- [ ] Verify database connectivity.
- [ ] Verify authentication configuration.
- [ ] Verify public frontend access.
- [ ] Verify public backend access.
- [ ] Run complete end-to-end smoke tests.

---

## 6. Round 3 Improvement Candidates

The following are roadmap items, not resolved bugs or completed capabilities.

1. Advanced ClaimGuard numeric, unit, locale, condition, expiry, and contradiction handling.
2. Multi-page visual analysis and supplementary semantic image understanding.
3. Guideline ambiguity signalling, upload-time conflict detection, and advanced privacy redaction.

The final implementation scope must remain consistent with the original Round 1 proposal.

---

**End of Bug Log**