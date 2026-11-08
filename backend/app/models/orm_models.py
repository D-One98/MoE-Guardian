from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BrandRuleModel(Base):
    __tablename__ = "brand_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mandatory_flag: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    pattern_or_target: Mapped[str] = mapped_column(Text, nullable=False)
    expected_replacement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    numeric_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    numeric_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_page_or_row: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    campaign_scope: Mapped[str] = mapped_column(String(64), default="GLOBAL", nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at_utc: Mapped[str] = mapped_column(String(64), default=_utc_now_iso, nullable=False)


class ApprovedFactModel(Base):
    __tablename__ = "approved_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fact_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    topic_key: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_keywords_json: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    approved_numeric_value: Mapped[float] = mapped_column(Float, nullable=False)
    numeric_unit: Mapped[str] = mapped_column(String(64), nullable=False)
    comparator: Mapped[str] = mapped_column(String(32), default="up_to", nullable=False)
    required_conditions_json: Mapped[str] = mapped_column(Text, nullable=False)
    prohibited_overstatements_json: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_page_or_row: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at_utc: Mapped[str] = mapped_column(String(64), default=_utc_now_iso, nullable=False)


class BrandPaletteModel(Base):
    __tablename__ = "brand_palettes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    palette_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hex_code: Mapped[str] = mapped_column(String(16), nullable=False)
    max_delta_e: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), default="DOC-BRAND-CONSTITUTION-V1", nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), default="Sample_Brand_Guidelines_v1.pdf", nullable=False)
    verified_page_or_row: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at_utc: Mapped[str] = mapped_column(String(64), default=_utc_now_iso, nullable=False)


class BrandIngestionBatchModel(Base):
    __tablename__ = "brand_ingestion_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING_CONFIRMATION", nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(64), nullable=False)
    pages_json: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at_utc: Mapped[str] = mapped_column(String(64), default=_utc_now_iso, nullable=False)
    confirmed_at_utc: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class AuditRecordModel(Base):
    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    submitted_by_role: Mapped[str] = mapped_column(String(64), nullable=False)
    document_revision_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(64), nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mandatory_policies_enforced: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    blocks_json: Mapped[str] = mapped_column(Text, nullable=False)
    engine_executions_json: Mapped[str] = mapped_column(Text, nullable=False)
    ai_disclosure_log_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at_utc: Mapped[str] = mapped_column(String(64), nullable=False)

    findings: Mapped[List["AuditFindingModel"]] = relationship(
        "AuditFindingModel",
        back_populates="audit",
        cascade="all, delete-orphan",
        order_by="AuditFindingModel.id",
    )
    snapshots: Mapped[List["ReviewSnapshotModel"]] = relationship(
        "ReviewSnapshotModel",
        back_populates="audit",
        cascade="all, delete-orphan",
        order_by="ReviewSnapshotModel.id",
    )


class AuditFindingModel(Base):
    __tablename__ = "audit_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("audit_records.audit_id", ondelete="CASCADE"), index=True, nullable=False
    )
    finding_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expert_engine: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_state: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(64), nullable=False)
    document_block_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    matched_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prefix_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suffix_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anchor_resolution_status: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rewrite_candidate_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    audit: Mapped["AuditRecordModel"] = relationship("AuditRecordModel", back_populates="findings")


class ReviewSnapshotModel(Base):
    __tablename__ = "review_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    audit_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("audit_records.audit_id", ondelete="CASCADE"), index=True, nullable=False
    )
    org_id: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(128), nullable=False)
    content_sha256_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    brand_constitution_version: Mapped[str] = mapped_column(String(32), nullable=False)
    facts_vault_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    router_config_version: Mapped[str] = mapped_column(String(32), nullable=False)
    retrieved_evidence_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    audit_output_sha256_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    approval_state: Mapped[str] = mapped_column(String(64), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(64), nullable=False)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at_utc: Mapped[str] = mapped_column(String(64), nullable=False)
    hmac_key_id: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_snapshot_hmac: Mapped[str] = mapped_column(String(128), nullable=False)
    snapshot_hmac_signature: Mapped[str] = mapped_column(String(128), nullable=False)

    audit: Mapped["AuditRecordModel"] = relationship("AuditRecordModel", back_populates="snapshots")

class OrganizationMembershipModel(Base):
    __tablename__ = "organization_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at_utc: Mapped[str] = mapped_column(String(64), default=_utc_now_iso, nullable=False)


Index("ix_org_memberships_user_org", OrganizationMembershipModel.user_id, OrganizationMembershipModel.org_id, unique=True)
Index("ix_brand_rules_org_rule", BrandRuleModel.org_id, BrandRuleModel.rule_id, unique=True)
Index("ix_approved_facts_org_fact", ApprovedFactModel.org_id, ApprovedFactModel.fact_id, unique=True)
Index("ix_brand_palettes_org_palette", BrandPaletteModel.org_id, BrandPaletteModel.palette_id, unique=True)
Index("ix_audit_findings_audit_finding", AuditFindingModel.audit_id, AuditFindingModel.finding_id, unique=True)