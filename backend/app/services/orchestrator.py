import hashlib
import hmac
import json
import uuid

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings, get_hmac_key_ring
from app.schemas.contracts import (
    AuditCreateRequest,
    AuditResponse,
    AuditStatus,
    AuditSnapshotRecord,
    ComplianceExportResponse,
    ContentBlock,
    DemoRole,
    ExecutionState,
    OnDemandRewriteRequest,
    OnDemandRewriteResponse,
    Severity,
    SimulatedCmsPayload,
    SnapshotVerificationResponse,
    SnapshotVerificationStatus,
    UnifiedFinding,
    VerificationStatus,
    VisualAssetInput,
)

from app.services.seed_data import DEMO_ORG_ID
from app.repositories.governance_repo import GovernanceRepository

from app.engines.rule_guard import run_rule_guard
from app.engines.claim_guard import run_claim_guard_baseline
from app.engines.visual_guard import run_visual_guard_baseline, run_visual_guard_with_ocr_metadata
from app.schemas.contracts import OcrStatus
from app.engines.voice_guard import run_voice_guard_baseline, generate_on_demand_rewrite_candidates
from app.services.privacy_gate import apply_baseline_privacy_gate

ALLOWED_REVIEW_SOURCE_STATES = {
    AuditStatus.PENDING_REVIEW,
    AuditStatus.READY_FOR_MANAGER_APPROVAL,
    AuditStatus.ESCALATED_TO_AUTHORISED_REVIEWER,
}


class VerityMoEOrchestrator:

    @staticmethod
    def compute_document_revision_hash(
        blocks: List[ContentBlock],
        alt_text: Optional[str] = None,
        visual_asset: Optional[VisualAssetInput] = None,
    ) -> str:

        canonical: Dict[str, Any] = {
            "blocks": [
                {
                    "document_block_id": b.document_block_id,
                    "text": b.text.strip(),
                }
                for b in blocks
            ],
            "alt_text": (alt_text or "").strip(),
        }

        if visual_asset is not None:
            canonical["visual_asset"] = {
                "document_block_id": visual_asset.document_block_id,
                "filename": visual_asset.filename,
                "mime_type": visual_asset.mime_type,
                "image_sha256": hashlib.sha256(
                    visual_asset.image_base64.encode("utf-8")
                ).hexdigest(),
                "alt_text": (visual_asset.alt_text or "").strip(),
            }

        payload = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return f"sha256:{hashlib.sha256(payload).hexdigest()}"

    @staticmethod
    def build_canonical_snapshot_payload(
        snapshot_id: str,
        audit_id: str,
        org_id: str,
        campaign_id: str,
        content_sha256_hash: str,
        retrieved_evidence_ids: List[str],
        audit_output_sha256_hash: str,
        approval_state: str,
        approver_role: str,
        review_notes: Optional[str],
        approved_at_utc: str,
        hmac_key_id: str,
        previous_snapshot_hmac: str,
    ) -> Dict[str, Any]:
        return {
            "snapshot_id": snapshot_id,
            "audit_id": audit_id,
            "org_id": org_id,
            "campaign_id": campaign_id,
            "content_sha256_hash": content_sha256_hash,
            "brand_constitution_version": "1.0",
            "facts_vault_version": "1.0",
            "rule_engine_version": "0.2.0",
            "router_config_version": "mandatory-v1",
            "retrieved_evidence_ids": sorted(retrieved_evidence_ids),
            "audit_output_sha256_hash": audit_output_sha256_hash,
            "approval_state": approval_state,
            "approver_role": approver_role,
            "review_notes": review_notes,
            "approved_at_utc": approved_at_utc,
            "hmac_key_id": hmac_key_id,
            "previous_snapshot_hmac": previous_snapshot_hmac,
        }

    @classmethod
    def compute_snapshot_hmac(
        cls,
        canonical_payload: Dict[str, Any],
        signing_secret: Optional[str] = None,
    ) -> str:
        secret_to_use = signing_secret
        if secret_to_use is None:
            _, active_secret, _ = get_hmac_key_ring()
            secret_to_use = active_secret

        canonical_bytes = json.dumps(
            canonical_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hmac.new(
            secret_to_use.encode("utf-8"),
            canonical_bytes,
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def verify_snapshot_hmac_detailed(
        cls,
        snapshot: AuditSnapshotRecord,
    ) -> tuple[bool, SnapshotVerificationStatus, str]:
        """
        Verifies a snapshot's canonical payload using the key_id stored in the snapshot
        against the configured key ring (active signing key + retired verification keys).
        Distinguishes UNKNOWN_KEY_ID, INVALID_SIGNATURE, and MALFORMED_SNAPSHOT.
        """
        try:
            if not snapshot or not isinstance(snapshot.hmac_key_id, str) or not snapshot.hmac_key_id.strip():
                return (
                    False,
                    SnapshotVerificationStatus.MALFORMED_SNAPSHOT,
                    "Snapshot is missing a valid hmac_key_id.",
                )
            if not isinstance(snapshot.snapshot_hmac_signature, str) or len(snapshot.snapshot_hmac_signature) != 64:
                return (
                    False,
                    SnapshotVerificationStatus.MALFORMED_SNAPSHOT,
                    "Snapshot signature is missing or not a valid 64-character hex SHA256 digest.",
                )

            _, _, key_map = get_hmac_key_ring()
            key_id = snapshot.hmac_key_id.strip()
            verification_secret = key_map.get(key_id)
            if verification_secret is None:
                return (
                    False,
                    SnapshotVerificationStatus.UNKNOWN_KEY_ID,
                    f"HMAC key identifier '{key_id}' is not present in the configured verification key ring.",
                )

            expected_payload = cls.build_canonical_snapshot_payload(
                snapshot_id=snapshot.snapshot_id,
                audit_id=snapshot.audit_id,
                org_id=snapshot.org_id,
                campaign_id=snapshot.campaign_id,
                content_sha256_hash=snapshot.content_sha256_hash,
                retrieved_evidence_ids=snapshot.retrieved_evidence_ids,
                audit_output_sha256_hash=snapshot.audit_output_sha256_hash,
                approval_state=snapshot.approval_state.value,
                approver_role=snapshot.approver_role.value,
                review_notes=snapshot.review_notes,
                approved_at_utc=snapshot.approved_at_utc,
                hmac_key_id=key_id,
                previous_snapshot_hmac=snapshot.previous_snapshot_hmac,
            )

            expected_sig = cls.compute_snapshot_hmac(
                expected_payload,
                signing_secret=verification_secret,
            )

            if hmac.compare_digest(expected_sig, snapshot.snapshot_hmac_signature):
                return (
                    True,
                    SnapshotVerificationStatus.VALID,
                    f"Snapshot signature verified successfully using key '{key_id}'.",
                )
            return (
                False,
                SnapshotVerificationStatus.INVALID_SIGNATURE,
                "Snapshot HMAC signature mismatch; payload or signature has been tampered with.",
            )
        except RuntimeError:
            raise
        except Exception as exc:
            return (
                False,
                SnapshotVerificationStatus.MALFORMED_SNAPSHOT,
                f"Malformed snapshot structure ({type(exc).__name__}).",
            )

    @classmethod
    def verify_snapshot_hmac(cls, snapshot: AuditSnapshotRecord) -> bool:
        is_valid, _, _ = cls.verify_snapshot_hmac_detailed(snapshot)
        return is_valid

    def request_on_demand_rewrite(
        self,
        db: Session,
        audit_id: str,
        finding_id: str,
        payload: OnDemandRewriteRequest,
        org_id: str = DEMO_ORG_ID,
    ) -> OnDemandRewriteResponse:
        repo = GovernanceRepository(db, org_id=org_id)
        audit = repo.get_audit(audit_id)
        if not audit:
            raise KeyError(f"Audit '{audit_id}' not found in organisation '{org_id}'.")

        target_finding = next(
            (f for f in audit.findings if f.finding_id == finding_id),
            None,
        )
        if target_finding is None:
            raise KeyError(f"Finding '{finding_id}' not found in audit '{audit_id}'.")

        target_block = next(
            (b for b in audit.blocks if b.document_block_id == target_finding.document_block_id),
            audit.blocks[0],
        )

        rules = repo.list_rules()
        facts = repo.list_facts()

        mandatory_rules = [r for r in rules if r.mandatory_flag]
        active_rules = mandatory_rules + [r for r in rules if not r.mandatory_flag]

        candidates = generate_on_demand_rewrite_candidates(
            block_text=target_block.text,
            finding=target_finding,
            rules=active_rules,
            facts=facts,
            custom_candidate_text=payload.custom_candidate_text,
        )

        primary = next(
            (c for c in candidates if c.backend_revalidation.revalidation_passed),
            None,
        )

        return OnDemandRewriteResponse(
            audit_id=audit.audit_id,
            org_id=audit.org_id,
            finding_id=target_finding.finding_id,
            original_matched_text=target_finding.matched_text or target_block.text,
            original_finding_type=target_finding.finding_type,
            original_verification_status=target_finding.verification_status,
            rewrite_candidates=candidates,
            selected_primary_candidate=primary,
        )
    
    def run_audit(self, db: Session, request: AuditCreateRequest, org_id: str = DEMO_ORG_ID) -> AuditResponse:

        repo = GovernanceRepository(db, org_id=org_id)
        palettes = repo.list_palettes_for_visual_guard()

        # Load persisted brand rules and approved facts
        rules = repo.list_rules()
        facts = repo.list_facts()

        # Mandatory rules are evaluated first
        mandatory_rules = [
            r for r in rules if r.mandatory_flag
        ]

        active_rules = mandatory_rules + [
            r for r in rules if not r.mandatory_flag
        ]

        # 1. Execute VisualGuard (including optional Tesseract OCR extraction)
        vg_findings, vg_exec, ocr_result = run_visual_guard_with_ocr_metadata(
            request.visual_asset,
            fallback_alt_text=request.alt_text,
            brand_palette=palettes,
        )

        # 2. If OCR succeeded with sufficient confidence, treat extracted text as untrusted user content
        #    and evaluate it through RuleGuard, ClaimGuard, VoiceGuard, and the Privacy Gate.
        #    OCR text is NEVER added to `facts` (never treated as an Approved Fact).
        effective_blocks: List[ContentBlock] = list(request.blocks)
        if (
            ocr_result is not None
            and ocr_result.ocr_status == OcrStatus.OCR_SUCCESS
            and ocr_result.extracted_text.strip()
        ):
            visual_block_id = (
                request.visual_asset.document_block_id
                if request.visual_asset is not None
                else "blk-visual-asset-01"
            )
            effective_blocks.append(
                ContentBlock(
                    document_block_id=f"{visual_block_id}:ocr",
                    text=ocr_result.extracted_text,
                )
            )

        # 3. Execute text governance engines across submitted blocks + high-confidence OCR block
        rg_findings, rg_exec = run_rule_guard(
            effective_blocks,
            active_rules,
        )

        cg_findings, cg_exec = run_claim_guard_baseline(
            effective_blocks,
            facts,
            active_rules,
        )

        voice_findings, voice_exec = run_voice_guard_baseline(
            effective_blocks,
            active_rules,
        )

        all_findings: List[UnifiedFinding] = (
            rg_findings + cg_findings + vg_findings + voice_findings
        )

        engine_executions = [
            rg_exec,
            cg_exec,
            vg_exec,
            voice_exec,
        ]

        # 4. Execute baseline regex privacy gate inspection across all blocks (including OCR text)
        privacy_report = apply_baseline_privacy_gate(effective_blocks)

        # Fail-closed engine execution check
        any_engine_failed = any(
            execution.execution_state in (
                ExecutionState.ERROR,
                ExecutionState.INSUFFICIENT_DATA,
            )
            for execution in engine_executions
        )

        #INSUFFICIENT_DATA and ERROR both set mandatory_policies_enforced to False
        mandatory_policies_enforced = all(
            execution.mandatory_enforced
            and execution.execution_state in (
                ExecutionState.OK,
                ExecutionState.NOT_APPLICABLE,
            )
            for execution in engine_executions
        )

        # Include finding-level execution failures in risk assessment
        has_high_risk_finding = any(
            finding.severity in (
                Severity.CRITICAL,
                Severity.HIGH,
            )
            or finding.execution_state in (
                ExecutionState.ERROR,
                ExecutionState.INSUFFICIENT_DATA,
            )
            or finding.verification_status in (
                VerificationStatus.PARTIAL,
                VerificationStatus.CONTRADICTED,
                VerificationStatus.UNVERIFIABLE,
            )
            for finding in all_findings
        )

        if any_engine_failed or has_high_risk_finding or not mandatory_policies_enforced:
            overall_status = (
                AuditStatus.ESCALATED_TO_AUTHORISED_REVIEWER
            )
            human_review_required = True
        else:
            overall_status = (
                AuditStatus.READY_FOR_MANAGER_APPROVAL
            )
            human_review_required = True

        # Generate document revision hash
        doc_rev_hash = self.compute_document_revision_hash(
            request.blocks,
            request.alt_text,
            request.visual_asset,
        )

        audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"

        now_utc = datetime.now(timezone.utc).isoformat()

        executed_engines = [
            "RuleGuard",
            "ClaimGuard_Baseline",
            "VoiceGuard_Baseline"
        ]
        if vg_exec.execution_state != ExecutionState.NOT_APPLICABLE:
            executed_engines.append("VisualGuard_Baseline")

        response = AuditResponse(
            audit_id=audit_id,
            org_id=org_id,
            campaign_id=request.campaign_id,
            submitted_by_role=request.submitted_by_role,
            document_revision_hash=doc_rev_hash,
            overall_status=overall_status,
            human_review_required=human_review_required,
            mandatory_policies_enforced=mandatory_policies_enforced,
            engine_executions=engine_executions,
            findings=all_findings,
            blocks=request.blocks,
            ai_disclosure_log={
                "llm_provider": settings.llm_provider,
                "external_data_shared": False,
                "deterministic_engines_executed": executed_engines,
                "privacy_masking_mode": privacy_report["privacy_masking_mode"],
                "sensitive_matches_masked_count": privacy_report["sensitive_matches_masked_count"],
                "sensitive_categories_detected": privacy_report["sensitive_categories_detected"],
                "ocr_telemetry": (
                    {
                        "ocr_status": ocr_result.ocr_status.value,
                        "mean_confidence": ocr_result.mean_confidence,
                        "min_confidence_threshold": ocr_result.min_confidence_threshold,
                        "regions_count": ocr_result.regions_count,
                        "prompt_injection_signals_detected": ocr_result.prompt_injection_signals_detected,
                        "governance_evaluated": ocr_result.governance_evaluated,
                    }
                    if ocr_result is not None
                    else {"ocr_status": "NOT_REQUESTED"}
                ),
                "timestamp_utc": now_utc,
            },
            latest_snapshot=None,
            created_at_utc=now_utc,
        )

        # Persist audit and findings in database
        return repo.save_audit(response)

    def get_audit(self, db: Session, audit_id: str, org_id: str = DEMO_ORG_ID) -> Optional[AuditResponse]:

        repo = GovernanceRepository(
            db,
            org_id=org_id,
        )

        return repo.get_audit(audit_id)

    def record_review_decision(self, db: Session, audit_id: str, actor_role: DemoRole, decision: str, override_justification: Optional[str] = None, org_id: str = DEMO_ORG_ID) -> AuditResponse:

        repo = GovernanceRepository(
            db,
            org_id=org_id,
        )

        audit = repo.get_audit(audit_id)

        if not audit:
            raise KeyError(
                f"Audit '{audit_id}' not found."
            )
        
        # Issue 5 Fix: Explicit allowed-state transition table enforcement
        if audit.overall_status not in ALLOWED_REVIEW_SOURCE_STATES:
            raise ValueError(
                f"Invalid state transition: Audit '{audit_id}' is already in terminal review state "
                f"'{audit.overall_status.value}' and cannot be reviewed again without submitting a new draft revision."
            )

        # Maker-Checker enforcement
        if actor_role == DemoRole.CREATOR:
            raise PermissionError(
                "Maker-Checker violation: Content Creators cannot approve or sign off their own submissions."
            )

        # High-risk approval restriction
        if (
            decision == "APPROVE"
            and audit.overall_status
            == AuditStatus.ESCALATED_TO_AUTHORISED_REVIEWER
            and actor_role not in (
                DemoRole.AUTHORISED_REVIEWER,
                DemoRole.WORKSPACE_ADMIN,
            )
        ):
            raise PermissionError(
                "High-risk or unverifiable findings require sign-off by an AUTHORISED_REVIEWER."
            )

        # Check unresolved violations (any finding that is not SUPPORTED, or any engine failure)
        unresolved_violations = [
            finding
            for finding in audit.findings
            if finding.verification_status != VerificationStatus.SUPPORTED
            or finding.execution_state != ExecutionState.OK
        ]

        if (
            decision == "APPROVE"
            and (unresolved_violations or not audit.mandatory_policies_enforced)
            and not (
                override_justification
                and override_justification.strip()
            )
        ):
            raise ValueError(
                "Approving a draft with flagged violations, inconclusive checks, or unverified claims requires a non-empty override_justification."
            )

        new_status = (
            AuditStatus.APPROVED
            if decision == "APPROVE"
            else AuditStatus.CHANGES_REQUESTED
        )

        now_utc = datetime.now(timezone.utc).isoformat()

        # Normalize review notes before signing
        cleaned_notes = (
            override_justification.strip()
            if override_justification and override_justification.strip()
            else None
        )

        # Collect evidence references
        evidence_ids = sorted(
            {
                finding.evidence_reference.reference_id
                for finding in audit.findings
                if finding.evidence_reference is not None
            }
        )

        # Hash audit findings
        findings_serialized = json.dumps(
            [
                finding.model_dump(mode="json")
                for finding in audit.findings
            ],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        output_hash = (
            f"sha256:{hashlib.sha256(findings_serialized).hexdigest()}"
        )

        # Retrieve previous HMAC from persistent database
        prev_hmac = repo.get_latest_snapshot_hmac()

        snapshot_id = f"SNAP-{uuid.uuid4().hex[:8].upper()}"

        active_key_id, active_secret, _ = get_hmac_key_ring()

        # Canonical payload includes review notes BEFORE signing
        canonical_snapshot_payload = self.build_canonical_snapshot_payload(
            snapshot_id=snapshot_id,
            audit_id=audit.audit_id,
            org_id=audit.org_id,
            campaign_id=audit.campaign_id,
            content_sha256_hash=audit.document_revision_hash,
            retrieved_evidence_ids=evidence_ids,
            audit_output_sha256_hash=output_hash,
            approval_state=new_status.value,
            approver_role=actor_role.value,
            review_notes=cleaned_notes,
            approved_at_utc=now_utc,
            hmac_key_id=active_key_id,
            previous_snapshot_hmac=prev_hmac,
        )

        # Generate HMAC-SHA256 signature using the active key
        signature = self.compute_snapshot_hmac(
            canonical_snapshot_payload,
            signing_secret=active_secret,
        )

        snapshot = AuditSnapshotRecord(
            **canonical_snapshot_payload,
            snapshot_hmac_signature=signature,
        )

        # Persist review snapshot and updated audit status
        return repo.save_review_snapshot(
            audit_id,
            new_status,
            snapshot,
        )

    def verify_audit_snapshot_integrity(
        self,
        db: Session,
        audit_id: str,
        org_id: str = DEMO_ORG_ID,
    ) -> SnapshotVerificationResponse:
        repo = GovernanceRepository(db, org_id=org_id)
        audit = repo.get_audit(audit_id)
        if not audit:
            raise KeyError(f"Audit '{audit_id}' not found in organisation '{org_id}'.")

        snap = audit.latest_snapshot
        if snap is None:
            return SnapshotVerificationResponse(
                audit_id=audit.audit_id,
                org_id=audit.org_id,
                snapshot_id=None,
                hmac_key_id=None,
                is_valid=False,
                status_code=SnapshotVerificationStatus.NO_SNAPSHOT_FOUND,
                chain_integrity_verified=False,
                message="Audit has not yet been reviewed or signed with an audit snapshot.",
            )

        is_valid, status_code, msg = self.verify_snapshot_hmac_detailed(snap)

        # Verify hash-chain continuity across persisted organisation snapshots
        org_snapshots = repo.list_org_snapshots_ordered()
        chain_ok = True
        expected_prev = "GENESIS_SNAPSHOT_0000000000000000"
        found_target = False
        for s_row in org_snapshots:
            if s_row.previous_snapshot_hmac != expected_prev:
                chain_ok = False
                break
            if s_row.snapshot_id == snap.snapshot_id:
                found_target = True
                break
            expected_prev = s_row.snapshot_hmac_signature

        if not found_target:
            chain_ok = False

        if is_valid and not chain_ok:
            return SnapshotVerificationResponse(
                audit_id=audit.audit_id,
                org_id=audit.org_id,
                snapshot_id=snap.snapshot_id,
                hmac_key_id=snap.hmac_key_id,
                is_valid=False,
                status_code=SnapshotVerificationStatus.BROKEN_HASH_CHAIN,
                chain_integrity_verified=False,
                message="Snapshot signature matched, but previous_snapshot_hmac hash-chain continuity failed.",
            )

        return SnapshotVerificationResponse(
            audit_id=audit.audit_id,
            org_id=audit.org_id,
            snapshot_id=snap.snapshot_id,
            hmac_key_id=snap.hmac_key_id,
            is_valid=(is_valid and chain_ok),
            status_code=status_code,
            chain_integrity_verified=chain_ok if is_valid else False,
            message=msg,
        )

    def export_compliance_package(
        self,
        db: Session,
        audit_id: str,
        org_id: str = DEMO_ORG_ID,
    ) -> ComplianceExportResponse:
        repo = GovernanceRepository(db, org_id=org_id)
        audit = repo.get_audit(audit_id)
        if not audit:
            raise KeyError(f"Audit '{audit_id}' not found in organisation '{org_id}'.")

        snap_verification = self.verify_audit_snapshot_integrity(
            db=db,
            audit_id=audit_id,
            org_id=org_id,
        )

        is_approved_and_verified = (
            audit.overall_status == AuditStatus.APPROVED
            and audit.latest_snapshot is not None
            and snap_verification.is_valid
        )

        # Separate machine findings summary from human review decision
        by_engine: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        claim_ledger_counts: Dict[str, int] = {}
        for f in audit.findings:
            by_engine[f.expert_engine] = by_engine.get(f.expert_engine, 0) + 1
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            if f.finding_type.value == "FACTUAL_CLAIM":
                claim_ledger_counts[f.verification_status.value] = (
                    claim_ledger_counts.get(f.verification_status.value, 0) + 1
                )

        human_decision: Optional[Dict[str, Any]] = None
        if audit.latest_snapshot is not None:
            human_decision = {
                "snapshot_id": audit.latest_snapshot.snapshot_id,
                "approval_state": audit.latest_snapshot.approval_state.value,
                "approver_role": audit.latest_snapshot.approver_role.value,
                "review_notes": audit.latest_snapshot.review_notes,
                "approved_at_utc": audit.latest_snapshot.approved_at_utc,
                "brand_constitution_version": audit.latest_snapshot.brand_constitution_version,
                "facts_vault_version": audit.latest_snapshot.facts_vault_version,
                "retrieved_evidence_ids": audit.latest_snapshot.retrieved_evidence_ids,
            }

        # Simulated CMS payload: ONLY includes approved_blocks when audit is APPROVED and snapshot is valid
        cms_payload = SimulatedCmsPayload(
            cms_export_mode="SIMULATED_PRE_PUBLICATION_PAYLOAD",
            external_cms_published=False,
            export_ready_for_cms=is_approved_and_verified,
            approval_status=audit.overall_status,
            audit_reference_id=audit.audit_id,
            document_revision_hash=audit.document_revision_hash,
            snapshot_id=audit.latest_snapshot.snapshot_id if audit.latest_snapshot else None,
            snapshot_hmac_signature=(
                audit.latest_snapshot.snapshot_hmac_signature if is_approved_and_verified and audit.latest_snapshot else None
            ),
            approved_blocks=audit.blocks if is_approved_and_verified else [],
            approved_alt_text=None,
            notice=(
                "Simulated CMS export payload ready for downstream publishing."
                if is_approved_and_verified
                else "Draft is NOT approved for publication; approved_blocks are withheld until human sign-off and valid HMAC snapshot verification."
            ),
        )

        return ComplianceExportResponse(
            export_version="1.0",
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            audit_id=audit.audit_id,
            org_id=audit.org_id,
            campaign_id=audit.campaign_id,
            created_at_utc=audit.created_at_utc,
            submitted_by_role=audit.submitted_by_role,
            document_revision_hash=audit.document_revision_hash,
            overall_status=audit.overall_status,
            human_review_required=audit.human_review_required,
            mandatory_policies_enforced=audit.mandatory_policies_enforced,
            machine_governance_summary={
                "total_findings": len(audit.findings),
                "findings_by_engine": by_engine,
                "findings_by_severity": by_severity,
                "claim_evidence_ledger_counts": claim_ledger_counts,
            },
            engine_executions=audit.engine_executions,
            machine_findings=audit.findings,
            human_review_decision=human_decision,
            snapshot_integrity=snap_verification,
            ai_disclosure_log=audit.ai_disclosure_log,
            simulated_cms_payload=cms_payload,
        )
        
orchestrator = VerityMoEOrchestrator()