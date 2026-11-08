import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.orm_models import (
    BrandRuleModel,
    ApprovedFactModel,
    BrandPaletteModel,
    BrandIngestionBatchModel,
    AuditRecordModel,
    AuditFindingModel,
    ReviewSnapshotModel,
    OrganizationMembershipModel,
)
from app.schemas.contracts import (
    BrandRule,
    RuleCategory,
    Severity,
    ApprovedFact,
    BrandPaletteItem,
    ExtractedPageMetadata,
    GuidelineUploadPreviewResponse,
    AuditResponse,
    AuditStatus,
    DemoRole,
    ContentBlock,
    EngineExecutionRecord,
    UnifiedFinding,
    ExecutionState,
    FindingType,
    VerificationStatus,
    AnchorResolutionStatus,
    EvidenceReference,
    RewriteCandidate,
    AuditSnapshotRecord,
)
from app.services.seed_data import (
    DEMO_ORG_ID,
    get_demo_brand_rules,
    get_demo_approved_facts,
    get_demo_brand_palette,
)

GENESIS_HMAC = "GENESIS_SNAPSHOT_0000000000000000"


class DuplicateResourceError(Exception):
    pass


class GovernanceRepository:
    def __init__(self, db: Session, org_id: str = DEMO_ORG_ID) -> None:
        self.db = db
        self.org_id = org_id

    def ensure_demo_seed_data(self) -> None:
        """
        Seeds fictional AURORAGEAR demo data ONLY for DEMO_ORG_ID.
        Never seeds or leaks demo records into other tenant organisations.
        """
        if self.org_id != DEMO_ORG_ID:
            return

        try:
            for rule in get_demo_brand_rules():
                exists = self.db.execute(
                    select(BrandRuleModel).where(
                        BrandRuleModel.org_id == self.org_id,
                        BrandRuleModel.rule_id == rule.rule_id,
                    )
                ).scalar_one_or_none()
                if exists is None:
                    self.db.add(
                        BrandRuleModel(
                            rule_id=rule.rule_id,
                            org_id=self.org_id,
                            category=rule.category.value,
                            title=rule.title,
                            description=rule.description,
                            mandatory_flag=rule.mandatory_flag,
                            severity=rule.severity.value,
                            pattern_or_target=rule.pattern_or_target,
                            expected_replacement=rule.expected_replacement,
                            numeric_max=rule.numeric_max,
                            numeric_unit=rule.numeric_unit,
                            document_id=rule.document_id,
                            document_name=rule.document_name,
                            verified_page_or_row=rule.verified_page_or_row,
                            version=rule.version,
                            campaign_scope=rule.campaign_scope,
                            is_custom=False,
                        )
                    )

            for fact in get_demo_approved_facts():
                exists = self.db.execute(
                    select(ApprovedFactModel).where(
                        ApprovedFactModel.org_id == self.org_id,
                        ApprovedFactModel.fact_id == fact.fact_id,
                    )
                ).scalar_one_or_none()
                if exists is None:
                    self.db.add(
                        ApprovedFactModel(
                            fact_id=fact.fact_id,
                            org_id=self.org_id,
                            topic_key=fact.topic_key,
                            subject_keywords_json=json.dumps(fact.subject_keywords),
                            canonical_text=fact.canonical_text,
                            approved_numeric_value=fact.approved_numeric_value,
                            numeric_unit=fact.numeric_unit,
                            comparator=fact.comparator,
                            required_conditions_json=json.dumps(fact.required_conditions),
                            prohibited_overstatements_json=json.dumps(fact.prohibited_overstatements),
                            document_id=fact.document_id,
                            document_name=fact.document_name,
                            verified_page_or_row=fact.verified_page_or_row,
                            version=fact.version,
                            is_custom=False,
                        )
                    )

            for pal in get_demo_brand_palette():
                exists = self.db.execute(
                    select(BrandPaletteModel).where(
                        BrandPaletteModel.org_id == self.org_id,
                        BrandPaletteModel.palette_id == pal["palette_id"],
                    )
                ).scalar_one_or_none()
                if exists is None:
                    self.db.add(
                        BrandPaletteModel(
                            palette_id=pal["palette_id"],
                            org_id=self.org_id,
                            name=pal["name"],
                            hex_code=pal["hex"],
                            max_delta_e=pal["max_delta_e"],
                            document_id=pal["document_id"],
                            document_name=pal["document_name"],
                            verified_page_or_row=pal["verified_page_or_row"],
                            version="1.0",
                            is_custom=False,
                        )
                    )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _to_brand_rule_schema(m: BrandRuleModel) -> BrandRule:
        return BrandRule(
            rule_id=m.rule_id,
            category=RuleCategory(m.category),
            title=m.title,
            description=m.description,
            mandatory_flag=m.mandatory_flag,
            severity=Severity(m.severity),
            pattern_or_target=m.pattern_or_target,
            expected_replacement=m.expected_replacement,
            numeric_max=m.numeric_max,
            numeric_unit=m.numeric_unit,
            document_id=m.document_id,
            document_name=m.document_name,
            verified_page_or_row=m.verified_page_or_row,
            version=m.version,
            campaign_scope=m.campaign_scope,
        )

    @staticmethod
    def _to_approved_fact_schema(m: ApprovedFactModel) -> ApprovedFact:
        return ApprovedFact(
            fact_id=m.fact_id,
            topic_key=m.topic_key,
            subject_keywords=json.loads(m.subject_keywords_json),
            canonical_text=m.canonical_text,
            approved_numeric_value=m.approved_numeric_value,
            numeric_unit=m.numeric_unit,
            comparator=m.comparator,
            required_conditions=json.loads(m.required_conditions_json),
            prohibited_overstatements=json.loads(m.prohibited_overstatements_json),
            document_id=m.document_id,
            document_name=m.document_name,
            verified_page_or_row=m.verified_page_or_row,
            version=m.version,
        )

    @staticmethod
    def _to_palette_schema(m: BrandPaletteModel) -> BrandPaletteItem:
        return BrandPaletteItem(
            palette_id=m.palette_id,
            name=m.name,
            hex=m.hex_code,
            max_delta_e=m.max_delta_e,
            document_id=m.document_id,
            document_name=m.document_name,
            verified_page_or_row=m.verified_page_or_row,
            version=m.version,
        )

    @staticmethod
    def _hex_to_rgb_tuple(hex_code: str):
        h = hex_code.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def list_rules(self) -> List[BrandRule]:
        self.ensure_demo_seed_data()
        rows = (
            self.db.execute(
                select(BrandRuleModel)
                .where(BrandRuleModel.org_id == self.org_id)
                .order_by(BrandRuleModel.id.asc())
            )
            .scalars()
            .all()
        )
        return [self._to_brand_rule_schema(r) for r in rows]

    def create_rule(self, rule: BrandRule) -> BrandRule:
        self.ensure_demo_seed_data()
        existing = self.db.execute(
            select(BrandRuleModel).where(
                BrandRuleModel.org_id == self.org_id,
                BrandRuleModel.rule_id == rule.rule_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateResourceError(
                f"Brand rule with rule_id '{rule.rule_id}' already exists in organisation '{self.org_id}'."
            )

        model = BrandRuleModel(
            rule_id=rule.rule_id,
            org_id=self.org_id,
            category=rule.category.value,
            title=rule.title,
            description=rule.description,
            mandatory_flag=rule.mandatory_flag,
            severity=rule.severity.value,
            pattern_or_target=rule.pattern_or_target,
            expected_replacement=rule.expected_replacement,
            numeric_max=rule.numeric_max,
            numeric_unit=rule.numeric_unit,
            document_id=rule.document_id,
            document_name=rule.document_name,
            verified_page_or_row=rule.verified_page_or_row,
            version=rule.version,
            campaign_scope=rule.campaign_scope,
            is_custom=True,
        )
        try:
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return self._to_brand_rule_schema(model)
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateResourceError(f"Duplicate rule_id '{rule.rule_id}'.") from exc
        except Exception:
            self.db.rollback()
            raise

    def list_facts(self) -> List[ApprovedFact]:
        self.ensure_demo_seed_data()
        rows = (
            self.db.execute(
                select(ApprovedFactModel)
                .where(ApprovedFactModel.org_id == self.org_id)
                .order_by(ApprovedFactModel.id.asc())
            )
            .scalars()
            .all()
        )
        return [self._to_approved_fact_schema(f) for f in rows]

    def create_fact(self, fact: ApprovedFact) -> ApprovedFact:
        self.ensure_demo_seed_data()
        existing = self.db.execute(
            select(ApprovedFactModel).where(
                ApprovedFactModel.org_id == self.org_id,
                ApprovedFactModel.fact_id == fact.fact_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateResourceError(
                f"Approved fact with fact_id '{fact.fact_id}' already exists in organisation '{self.org_id}'."
            )

        model = ApprovedFactModel(
            fact_id=fact.fact_id,
            org_id=self.org_id,
            topic_key=fact.topic_key,
            subject_keywords_json=json.dumps(fact.subject_keywords),
            canonical_text=fact.canonical_text,
            approved_numeric_value=fact.approved_numeric_value,
            numeric_unit=fact.numeric_unit,
            comparator=fact.comparator,
            required_conditions_json=json.dumps(fact.required_conditions),
            prohibited_overstatements_json=json.dumps(fact.prohibited_overstatements),
            document_id=fact.document_id,
            document_name=fact.document_name,
            verified_page_or_row=fact.verified_page_or_row,
            version=fact.version,
            is_custom=True,
        )
        try:
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return self._to_approved_fact_schema(model)
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateResourceError(f"Duplicate fact_id '{fact.fact_id}'.") from exc
        except Exception:
            self.db.rollback()
            raise

    def list_palettes(self) -> List[BrandPaletteItem]:
        self.ensure_demo_seed_data()
        rows = (
            self.db.execute(
                select(BrandPaletteModel)
                .where(BrandPaletteModel.org_id == self.org_id)
                .order_by(BrandPaletteModel.id.asc())
            )
            .scalars()
            .all()
        )
        return [self._to_palette_schema(p) for p in rows]

    def list_palettes_for_visual_guard(self) -> List[Dict[str, Any]]:
        items = self.list_palettes()
        return [
            {
                "palette_id": item.palette_id,
                "name": item.name,
                "hex": item.hex,
                "rgb": self._hex_to_rgb_tuple(item.hex),
                "max_delta_e": item.max_delta_e,
                "document_id": item.document_id,
                "document_name": item.document_name,
                "verified_page_or_row": item.verified_page_or_row,
            }
            for item in items
        ]

    def create_palette_item(self, item: BrandPaletteItem) -> BrandPaletteItem:
        self.ensure_demo_seed_data()
        existing = self.db.execute(
            select(BrandPaletteModel).where(
                BrandPaletteModel.org_id == self.org_id,
                BrandPaletteModel.palette_id == item.palette_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DuplicateResourceError(
                f"Brand palette item '{item.palette_id}' already exists in organisation '{self.org_id}'."
            )

        model = BrandPaletteModel(
            palette_id=item.palette_id,
            org_id=self.org_id,
            name=item.name,
            hex_code=item.hex,
            max_delta_e=item.max_delta_e,
            document_id=item.document_id,
            document_name=item.document_name,
            verified_page_or_row=item.verified_page_or_row,
            version=item.version,
            is_custom=True,
        )
        try:
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return self._to_palette_schema(model)
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateResourceError(f"Duplicate palette_id '{item.palette_id}'.") from exc
        except Exception:
            self.db.rollback()
            raise

    def create_ingestion_preview_batch(
        self,
        document_id: str,
        document_name: str,
        page_count: int,
        extraction_status: str,
        pages: List[ExtractedPageMetadata],
        candidate_rules: List[BrandRule],
        warnings: List[str],
    ) -> GuidelineUploadPreviewResponse:
        batch_id = f"BATCH-{uuid.uuid4().hex[:8].upper()}"
        model = BrandIngestionBatchModel(
            batch_id=batch_id,
            org_id=self.org_id,
            document_id=document_id,
            document_name=document_name,
            status="PENDING_CONFIRMATION",
            page_count=page_count,
            extraction_status=extraction_status,
            pages_json=json.dumps([p.model_dump(mode="json") for p in pages]),
            candidate_rules_json=json.dumps([r.model_dump(mode="json") for r in candidate_rules]),
            warnings_json=json.dumps(warnings),
        )
        try:
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
            return GuidelineUploadPreviewResponse(
                batch_id=model.batch_id,
                org_id=model.org_id,
                document_id=model.document_id,
                document_name=model.document_name,
                status=model.status,
                page_count=model.page_count,
                extraction_status=model.extraction_status,
                prompt_shield_isolated=True,
                pages=pages,
                candidate_rules=candidate_rules,
                warnings=warnings,
            )
        except Exception:
            self.db.rollback()
            raise

    def confirm_ingestion_batch(
        self,
        batch_id: str,
        confirmed_rules: List[BrandRule],
        version: str = "1.0",
    ) -> List[BrandRule]:
        batch = self.db.execute(
            select(BrandIngestionBatchModel).where(
                BrandIngestionBatchModel.batch_id == batch_id,
                BrandIngestionBatchModel.org_id == self.org_id,
            )
        ).scalar_one_or_none()
        if batch is None:
            raise KeyError(f"Ingestion preview batch '{batch_id}' not found for organisation '{self.org_id}'.")

        if batch.status == "CONFIRMED":
            raise ValueError(f"Ingestion preview batch '{batch_id}' has already been confirmed.")

        # Check for duplicates before inserting
        seen_ids: set[str] = set()
        for rule in confirmed_rules:
            if rule.rule_id in seen_ids:
                raise DuplicateResourceError(f"Duplicate rule_id '{rule.rule_id}' in confirmation payload.")
            seen_ids.add(rule.rule_id)
            existing = self.db.execute(
                select(BrandRuleModel).where(
                    BrandRuleModel.org_id == self.org_id,
                    BrandRuleModel.rule_id == rule.rule_id,
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise DuplicateResourceError(
                    f"Brand rule '{rule.rule_id}' already exists in organisation '{self.org_id}'."
                )

        persisted: List[BrandRule] = []
        try:
            for rule in confirmed_rules:
                model = BrandRuleModel(
                    rule_id=rule.rule_id,
                    org_id=self.org_id,
                    category=rule.category.value,
                    title=rule.title,
                    description=rule.description,
                    mandatory_flag=rule.mandatory_flag,
                    severity=rule.severity.value,
                    pattern_or_target=rule.pattern_or_target,
                    expected_replacement=rule.expected_replacement,
                    numeric_max=rule.numeric_max,
                    numeric_unit=rule.numeric_unit,
                    document_id=rule.document_id or batch.document_id,
                    document_name=rule.document_name or batch.document_name,
                    verified_page_or_row=rule.verified_page_or_row,
                    version=version or rule.version,
                    campaign_scope=rule.campaign_scope,
                    is_custom=True,
                )
                self.db.add(model)
                persisted.append(self._to_brand_rule_schema(model))

            batch.status = "CONFIRMED"
            batch.confirmed_at_utc = datetime.now(timezone.utc).isoformat()
            self.db.commit()
            return persisted
        except Exception:
            self.db.rollback()
            raise

    def save_audit(self, audit: AuditResponse) -> AuditResponse:
        try:
            record = AuditRecordModel(
                audit_id=audit.audit_id,
                org_id=audit.org_id,
                campaign_id=audit.campaign_id,
                submitted_by_role=audit.submitted_by_role.value,
                document_revision_hash=audit.document_revision_hash,
                overall_status=audit.overall_status.value,
                human_review_required=audit.human_review_required,
                mandatory_policies_enforced=audit.mandatory_policies_enforced,
                blocks_json=json.dumps([b.model_dump(mode="json") for b in audit.blocks]),
                engine_executions_json=json.dumps([e.model_dump(mode="json") for e in audit.engine_executions]),
                ai_disclosure_log_json=json.dumps(audit.ai_disclosure_log),
                created_at_utc=audit.created_at_utc,
            )
            for f in audit.findings:
                record.findings.append(
                    AuditFindingModel(
                        audit_id=audit.audit_id,
                        finding_id=f.finding_id,
                        expert_engine=f.expert_engine,
                        execution_state=f.execution_state.value,
                        finding_type=f.finding_type.value,
                        severity=f.severity.value,
                        verification_status=f.verification_status.value,
                        document_block_id=f.document_block_id,
                        matched_text=f.matched_text,
                        prefix_context=f.prefix_context,
                        suffix_context=f.suffix_context,
                        anchor_resolution_status=f.anchor_resolution_status.value,
                        explanation=f.explanation,
                        evidence_reference_json=(
                            json.dumps(f.evidence_reference.model_dump(mode="json"))
                            if f.evidence_reference
                            else None
                        ),
                        rewrite_candidate_json=(
                            json.dumps(f.rewrite_candidate.model_dump(mode="json"))
                            if f.rewrite_candidate
                            else None
                        ),
                        human_review_required=f.human_review_required,
                    )
                )
            self.db.add(record)
            self.db.commit()
            return self.get_audit(audit.audit_id)  # type: ignore[return-value]
        except Exception:
            self.db.rollback()
            raise

    def get_audit(self, audit_id: str) -> Optional[AuditResponse]:
        record = self.db.execute(
            select(AuditRecordModel).where(
                AuditRecordModel.audit_id == audit_id,
                AuditRecordModel.org_id == self.org_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return None

        findings: List[UnifiedFinding] = []
        for fm in record.findings:
            ev_ref = (
                EvidenceReference(**json.loads(fm.evidence_reference_json))
                if fm.evidence_reference_json
                else None
            )
            rw_cand = (
                RewriteCandidate(**json.loads(fm.rewrite_candidate_json))
                if fm.rewrite_candidate_json
                else None
            )
            findings.append(
                UnifiedFinding(
                    finding_id=fm.finding_id,
                    expert_engine=fm.expert_engine,
                    execution_state=ExecutionState(fm.execution_state),
                    finding_type=FindingType(fm.finding_type),
                    severity=Severity(fm.severity),
                    verification_status=VerificationStatus(fm.verification_status),
                    document_block_id=fm.document_block_id,
                    matched_text=fm.matched_text,
                    prefix_context=fm.prefix_context,
                    suffix_context=fm.suffix_context,
                    anchor_resolution_status=AnchorResolutionStatus(fm.anchor_resolution_status),
                    explanation=fm.explanation,
                    evidence_reference=ev_ref,
                    rewrite_candidate=rw_cand,
                    human_review_required=fm.human_review_required,
                )
            )

        latest_snap: Optional[AuditSnapshotRecord] = None
        if record.snapshots:
            sm = record.snapshots[-1]
            latest_snap = AuditSnapshotRecord(
                snapshot_id=sm.snapshot_id,
                audit_id=sm.audit_id,
                org_id=sm.org_id,
                campaign_id=sm.campaign_id,
                content_sha256_hash=sm.content_sha256_hash,
                brand_constitution_version=sm.brand_constitution_version,
                facts_vault_version=sm.facts_vault_version,
                rule_engine_version=sm.rule_engine_version,
                router_config_version=sm.router_config_version,
                retrieved_evidence_ids=json.loads(sm.retrieved_evidence_ids_json),
                audit_output_sha256_hash=sm.audit_output_sha256_hash,
                approval_state=AuditStatus(sm.approval_state),
                approver_role=DemoRole(sm.approver_role),
                review_notes=sm.review_notes,
                approved_at_utc=sm.approved_at_utc,
                hmac_key_id=sm.hmac_key_id,
                previous_snapshot_hmac=sm.previous_snapshot_hmac,
                snapshot_hmac_signature=sm.snapshot_hmac_signature,
            )

        return AuditResponse(
            audit_id=record.audit_id,
            org_id=record.org_id,
            campaign_id=record.campaign_id,
            submitted_by_role=DemoRole(record.submitted_by_role),
            document_revision_hash=record.document_revision_hash,
            overall_status=AuditStatus(record.overall_status),
            human_review_required=record.human_review_required,
            mandatory_policies_enforced=record.mandatory_policies_enforced,
            engine_executions=[EngineExecutionRecord(**e) for e in json.loads(record.engine_executions_json)],
            findings=findings,
            blocks=[ContentBlock(**b) for b in json.loads(record.blocks_json)],
            ai_disclosure_log=json.loads(record.ai_disclosure_log_json),
            latest_snapshot=latest_snap,
            created_at_utc=record.created_at_utc,
        )

    def get_latest_snapshot_hmac(self) -> str:
        last_snap = (
            self.db.execute(
                select(ReviewSnapshotModel)
                .where(ReviewSnapshotModel.org_id == self.org_id)
                .order_by(ReviewSnapshotModel.id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        return last_snap.snapshot_hmac_signature if last_snap is not None else GENESIS_HMAC

    def save_review_snapshot(self, audit_id: str, new_status: AuditStatus, snapshot: AuditSnapshotRecord) -> AuditResponse:
        try:
            record = self.db.execute(
                select(AuditRecordModel).where(
                    AuditRecordModel.audit_id == audit_id,
                    AuditRecordModel.org_id == self.org_id,
                )
            ).scalar_one_or_none()
            if record is None:
                raise KeyError(f"Audit '{audit_id}' not found.")

            record.overall_status = new_status.value
            snap_model = ReviewSnapshotModel(
                snapshot_id=snapshot.snapshot_id,
                audit_id=snapshot.audit_id,
                org_id=snapshot.org_id,
                campaign_id=snapshot.campaign_id,
                content_sha256_hash=snapshot.content_sha256_hash,
                brand_constitution_version=snapshot.brand_constitution_version,
                facts_vault_version=snapshot.facts_vault_version,
                rule_engine_version=snapshot.rule_engine_version,
                router_config_version=snapshot.router_config_version,
                retrieved_evidence_ids_json=json.dumps(snapshot.retrieved_evidence_ids),
                audit_output_sha256_hash=snapshot.audit_output_sha256_hash,
                approval_state=snapshot.approval_state.value,
                approver_role=snapshot.approver_role.value,
                review_notes=snapshot.review_notes,
                approved_at_utc=snapshot.approved_at_utc,
                hmac_key_id=snapshot.hmac_key_id,
                previous_snapshot_hmac=snapshot.previous_snapshot_hmac,
                snapshot_hmac_signature=snapshot.snapshot_hmac_signature,
            )
            self.db.add(snap_model)
            self.db.commit()
            return self.get_audit(audit_id)  # type: ignore[return-value]
        except Exception:
            self.db.rollback()
            raise

    def upsert_membership(
        self,
        user_id: str,
        org_id: str,
        role: DemoRole,
        is_active: bool = True,
    ) -> OrganizationMembershipModel:
        try:
            existing = self.db.execute(
                select(OrganizationMembershipModel).where(
                    OrganizationMembershipModel.user_id == user_id,
                    OrganizationMembershipModel.org_id == org_id,
                )
            ).scalar_one_or_none()
            if existing is not None:
                existing.role = role.value
                existing.is_active = is_active
                self.db.commit()
                self.db.refresh(existing)
                return existing

            member = OrganizationMembershipModel(
                user_id=user_id,
                org_id=org_id,
                role=role.value,
                is_active=is_active,
            )
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)
            return member
        except Exception:
            self.db.rollback()
            raise

    def get_active_membership(
        self,
        user_id: str,
        org_id: str,
    ) -> Optional[OrganizationMembershipModel]:
        return self.db.execute(
            select(OrganizationMembershipModel).where(
                OrganizationMembershipModel.user_id == user_id,
                OrganizationMembershipModel.org_id == org_id,
                OrganizationMembershipModel.is_active.is_(True),
            )
        ).scalar_one_or_none()

    def get_primary_active_membership_for_user(
        self,
        user_id: str,
    ) -> Optional[OrganizationMembershipModel]:
        return (
            self.db.execute(
                select(OrganizationMembershipModel)
                .where(
                    OrganizationMembershipModel.user_id == user_id,
                    OrganizationMembershipModel.is_active.is_(True),
                )
                .order_by(OrganizationMembershipModel.id.asc())
                .limit(1)
            )
            .scalars()
            .first()
        )

    def list_active_memberships_for_user(
        self,
        user_id: str,
    ) -> List[OrganizationMembershipModel]:
        return list(
            self.db.execute(
                select(OrganizationMembershipModel)
                .where(
                    OrganizationMembershipModel.user_id == user_id,
                    OrganizationMembershipModel.is_active.is_(True),
                )
                .order_by(OrganizationMembershipModel.id.asc())
            )
            .scalars()
            .all()
        )

    def list_org_snapshots_ordered(self) -> List[ReviewSnapshotModel]:
        return list(
            self.db.execute(
                select(ReviewSnapshotModel)
                .where(ReviewSnapshotModel.org_id == self.org_id)
                .order_by(ReviewSnapshotModel.id.asc())
            )
            .scalars()
            .all()
        )