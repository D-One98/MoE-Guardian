# MoE-GUARDIAN — System Architecture (Round 2 Foundation)

## 1. System Boundaries & Core Principles
* **Product Identity:** MoE-GUARDIAN (Powered by VERITY MoE)
* **Team:** THE MOE (Divy Mishra & Lavanya Bani)
* **Role:** Pre-publication brand-governance and compliance layer positioned between content creation and publication.
* **Deterministic First:** Explicit rules (`RuleGuard`) and baseline fact/condition comparisons (`ClaimGuard`) execute in pure Python without LLM latency or hallucination.
* **Backend Authority:** Only backend database/seed records serve as authoritative citations (`EvidenceReference`). Rewrite validation statuses (`revalidation_passed`) and HMAC-SHA256 audit snapshots are computed exclusively on the backend.

## 2. End-to-End Data Flow
1. **Workspace & Constitution Loading:** `VerityMoEOrchestrator` loads active `BrandRule` and `ApprovedFact` records.
2. **Mandatory-Policy Enforcement:** Rules marked `mandatory_flag = True` are locked in first so routing/classification never skips required checks.
3. **Specialist Engine Execution:**
   * `RuleGuard` (`backend/app/engines/rule_guard.py`): Evaluates banned terms, exact brand casing (`AURORAGEAR`), mandatory disclaimers, and explicit numeric bounds.
   * `ClaimGuard` Baseline (`backend/app/engines/claim_guard.py`): Evaluates factual/promotional assertions against the Approved Facts Vault across `SUPPORTED`, `PARTIAL`, `CONTRADICTED`, and `UNVERIFIABLE` states.
4. **Canonical Block Anchoring (`backend/app/services/anchoring.py`):** Resolves `matched_text`, `prefix_context`, and `suffix_context` within each submitted `document_block_id` without inventing frontend character offsets.
5. **Fail-Closed Rewrite Validation Coordinator:** Candidate rewrites are re-checked through `RuleGuard` and `ClaimGuard`; `revalidation_passed = True` is assigned by the backend only when `RuleGuard` reports 0 violations and `candidate_verification_status == "SUPPORTED"`.
6. **Maker-Checker & HMAC Audit Snapshot:** Creators are blocked from self-approving (`403 Forbidden`). Validated approvals generate a canonicalised, `HMAC-SHA256` signed `AuditSnapshotRecord` chained to `previous_snapshot_hmac`.

## 3. LLM Boundary & Security Limitations
* **LLM Boundary (`backend/app/services/llm_adapter.py`):** Isolated behind `LLMProviderAdapter` (defaults to `NullDeterministicAdapter`). Local execution requires zero external API keys, and a failed/unconfigured LLM never produces a `SUPPORTED` claim.
* **Current Security Scope:** Public demo endpoints use non-sensitive fictional sample data (`AURORAGEAR`). Role selection in the demo workspace is a simulation for frictionless judge testing; server-side state validation enforces Maker-Checker separation.

## 4. SQLAlchemy 2.x Persistence Architecture
* **Database Engine (`backend/app/core/database.py`):** Supports local SQLite (`sqlite:///./moe_guardian_dev.db` with `PRAGMA foreign_keys=ON`) by default and PostgreSQL via `DATABASE_URL`. Connections are initialized lazily on demand rather than at module import time.
* **Typed ORM Models (`backend/app/models/orm_models.py`):**
  1. `BrandRuleModel` (`brand_rules`): Stores seeded and custom brand constitution rules (`rule_id` unique, indexed by `org_id`).
  2. `ApprovedFactModel` (`approved_facts`): Stores seeded and custom approved facts (`fact_id` unique, indexed by `org_id`).
  3. `AuditRecordModel` (`audit_records`): Stores audit metadata, submitted blocks, engine execution records, and AI disclosure logs, with one-to-many cascading relationships to findings and review snapshots.
  4. `AuditFindingModel` (`audit_findings`): Normalized persistence of every `UnifiedFinding` linked via foreign key (`audit_records.audit_id`, `ondelete="CASCADE"`).
  5. `ReviewSnapshotModel` (`review_snapshots`): Persists signed review decisions and chained `HMAC-SHA256` signatures (`previous_snapshot_hmac`).
* **Repository Layer (`backend/app/repositories/governance_repo.py`):** Separates SQLAlchemy persistence and transaction rollback handling from FastAPI route handlers and `VerityMoEOrchestrator`. Seeds fictional `AURORAGEAR` demo rules and facts idempotently without overwriting administrator-created records.

## 5. Specialist Engines & Orchestration Flow
1. **`RuleGuard` (`backend/app/engines/rule_guard.py`):** Deterministic regex and bound validation for banned terms, exact brand casing (`AURORAGEAR`), mandatory disclaimers, and discount bounds.
2. **`ClaimGuard` Baseline (`backend/app/engines/claim_guard.py`):** Evaluates promotional/factual claims against `ApprovedFact` records across `SUPPORTED`, `PARTIAL`, `CONTRADICTED`, and `UNVERIFIABLE` states, paired with the fail-closed Rewrite Validation Coordinator.
3. **`VisualGuard` Baseline (`backend/app/engines/visual_guard.py`):** Validates static PNG and JPG/JPEG creatives in memory (MIME + Pillow header match, 5 MB size cap, 16 MP decompression-bomb guard), compares dominant colours against the brand palette using **CIEDE2000 ($\Delta E$)**, checks `alt_text` metadata presence, and computes **WCAG 2.1 relative-luminance contrast** only when foreground/background colours are reliably known (returning `INSUFFICIENT_DATA` otherwise).
4. **Fail-Closed Orchestration & HMAC Chaining (`backend/app/services/orchestrator.py`):** Any engine error sets `mandatory_policies_enforced = False` and escalates the audit to `ESCALATED_TO_AUTHORISED_REVIEWER`. Review decisions include `review_notes` inside the canonical JSON payload prior to `HMAC-SHA256` signing and chain against the latest persisted snapshot signature.

# MoE-GUARDIAN — System Architecture

> **Product:** MoE-GUARDIAN (Powered by VERITY MoE)
> **Team:** THE MOE
> **Architecture:** Modular FastAPI Backend + React/TypeScript Frontend
> **Primary Goal:** Pre-publication brand governance and compliance.

---

## 1. System Boundaries & Core Principles

MoE-GUARDIAN is a pre-publication brand-governance layer positioned between content creation and publication.

Its purpose is to evaluate marketing content against:

- Brand rules.
- Approved factual information.
- Visual identity requirements.
- Accessibility considerations.
- Tone and messaging guidelines.
- Human approval requirements.

### Core Principles

**1. Deterministic First**

Explicit policy checks and baseline factual comparisons execute through deterministic backend logic wherever possible.

**2. Evidence-Grounded Decisions**

Only backend records and verified evidence references are authoritative.

**3. Backend Authority**

The frontend cannot independently assign:

- Claim verification status.
- Rewrite validation status.
- Human approval status.
- Snapshot signatures.
- Snapshot integrity results.

**4. Fail-Closed Validation**

If mandatory validation cannot be completed reliably, the system must not silently treat the content as approved.

**5. Human Accountability**

Machine-generated findings and human review decisions remain separate.

---

## 2. High-Level Architecture

```text
                    ┌──────────────────────────┐
                    │       React Frontend     │
                    │                          │
                    │  Workspace / Editor      │
                    │  Findings / Review UI     │
                    │  Upload / Export          │
                    └────────────┬─────────────┘
                                 │
                                 │ HTTP / JSON
                                 │ Multipart Uploads
                                 ▼
                    ┌──────────────────────────┐
                    │       FastAPI API        │
                    │                          │
                    │ Authentication & Tenant  │
                    │ Request Validation       │
                    │ API Route Handling       │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   VERITY MoE Orchestrator│
                    │                          │
                    │ Audit Coordination       │
                    │ Specialist Execution     │
                    │ Review Workflow          │
                    └────────────┬─────────────┘
                                 │
             ┌───────────────────┼──────────────────┐
             ▼                   ▼                  ▼
        RuleGuard            ClaimGuard        VisualGuard
                                                   │
                                                   ▼
                                               OCR Service

                                 │
                                 ▼
                             VoiceGuard
                                 │
                                 ▼
                     Rewrite Validation Coordinator

                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Governance Repository    │
                    │                          │
                    │ SQLAlchemy ORM            │
                    │ Tenant-Scoped Records     │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ SQLite / PostgreSQL       │
                    │                          │
                    │ Rules / Facts / Audits    │
                    │ Findings / Snapshots      │
                    └──────────────────────────┘