import os
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.tenant_context import TenantContext, get_tenant_context
from app.schemas.contracts import (
    ApprovedFact,
    AuditCreateRequest,
    AuditResponse,
    BrandPaletteItem,
    BrandRule,
    ComplianceExportResponse,
    CsvFactsUploadResponse,
    CsvRowError,
    DemoRole,
    GuidelineConfirmRequest,
    GuidelineUploadPreviewResponse,
    OnDemandRewriteRequest,
    OnDemandRewriteResponse,
    ReviewDecisionRequest,
    SnapshotVerificationResponse,
)
from app.services.seed_data import (
    DEMO_ORG_NAME,
    get_demo_sample_drafts,
)
from app.repositories.governance_repo import (
    GovernanceRepository,
    DuplicateResourceError,
)
from app.services.ingestion_service import (
    IngestionValidationError,
    parse_approved_facts_csv,
    parse_brand_guideline_pdf,
)
from app.services.orchestrator import orchestrator

router = APIRouter(prefix="/api")

def _require_admin_or_manager_if_authenticated(tenant: TenantContext) -> None:
    if not tenant.is_demo_fallback and tenant.role not in (
        DemoRole.WORKSPACE_ADMIN,
        DemoRole.BRAND_MANAGER,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "INSUFFICIENT_TENANT_ROLE",
                "message": "Modifying brand rules, facts, or palettes requires WORKSPACE_ADMIN or BRAND_MANAGER membership.",
            },
        )

@router.get("/health")
def get_health():
    return {
        "status": "ok",
        "application": "MoE-GUARDIAN",
        "engine": "VERITY MoE",
        "version": settings.app_version,
        "environment": settings.app_env,
    }

@router.get("/auth/me")
def get_authenticated_tenant_profile(
    tenant: TenantContext = Depends(get_tenant_context),
):
    return {
        "user_id": tenant.user_id,
        "org_id": tenant.org_id,
        "role": tenant.role.value if tenant.role else None,
        "is_demo_fallback": tenant.is_demo_fallback,
        "auth_mode": tenant.auth_mode,
    }


@router.get("/demo/workspace")
def get_demo_workspace(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    rules = repo.list_rules()
    facts = repo.list_facts()
    palette = repo.list_palettes()
    return {
        "demo_mode": tenant.is_demo_fallback,
        "auth_mode": tenant.auth_mode,
        "demo_notice": (
            "Public evaluation sandbox with non-sensitive sample data. "
            "Role switching is a demo-only simulation; production deployments enforce server-verified JWT authentication."
        ),
        "org_id": tenant.org_id,
        "org_name": DEMO_ORG_NAME if tenant.org_id == "ORG-SAMPLE-DEMO-01" else f"Tenant Workspace ({tenant.org_id})",
        "allowed_demo_roles": [r.value for r in DemoRole],
        "rules_count": len(rules),
        "facts_count": len(facts),
        "palette_count": len(palette),
        "sample_drafts": get_demo_sample_drafts(),
    }


@router.get("/brand/rules")
def list_brand_rules(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    return {
        "org_id": tenant.org_id,
        "brand_constitution_version": "1.0",
        "rules": repo.list_rules(),
    }


@router.post("/brand/rules", status_code=status.HTTP_201_CREATED)
def create_brand_rule(
    payload: BrandRule,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    _require_admin_or_manager_if_authenticated(tenant)
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    try:
        created_rule = repo.create_rule(payload)
        return {
            "org_id": tenant.org_id,
            "brand_constitution_version": "1.0",
            "rule": created_rule,
        }
    except DuplicateResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "DUPLICATE_RULE_ID",
                "message": str(exc),
            },
        )


@router.post(
    "/brand/guidelines/upload-pdf",
    response_model=GuidelineUploadPreviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_brand_guideline_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    _require_admin_or_manager_if_authenticated(tenant)
    max_pdf_bytes = int(os.getenv("MAX_PDF_UPLOAD_BYTES", str(settings.max_pdf_upload_bytes)))
    file_bytes = await file.read(max_pdf_bytes + 1)
    try:
        parsed = parse_brand_guideline_pdf(file_bytes, file.filename or "Brand_Guidelines.pdf")
    except IngestionValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": exc.error_code, "message": exc.message},
        )

    repo = GovernanceRepository(db, org_id=tenant.org_id)
    return repo.create_ingestion_preview_batch(
        document_id=parsed["document_id"],
        document_name=parsed["document_name"],
        page_count=parsed["page_count"],
        extraction_status=parsed["extraction_status"],
        pages=parsed["pages"],
        candidate_rules=parsed["candidate_rules"],
        warnings=parsed["warnings"],
    )


@router.post("/brand/guidelines/{batch_id}/confirm")
def confirm_brand_guideline_rules(
    batch_id: str,
    payload: GuidelineConfirmRequest,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    _require_admin_or_manager_if_authenticated(tenant)
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    try:
        persisted_rules = repo.confirm_ingestion_batch(
            batch_id=batch_id,
            confirmed_rules=payload.confirmed_rules,
            version=payload.brand_constitution_version,
        )
        return {
            "batch_id": batch_id,
            "org_id": tenant.org_id,
            "status": "CONFIRMED",
            "brand_constitution_version": payload.brand_constitution_version,
            "confirmed_rules_count": len(persisted_rules),
            "rules": persisted_rules,
        }
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "INGESTION_BATCH_NOT_FOUND", "message": str(exc)},
        )
    except DuplicateResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "DUPLICATE_RULE_ID", "message": str(exc)},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BATCH_ALREADY_CONFIRMED", "message": str(exc)},
        )


@router.get("/brand/facts")
def list_brand_facts(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    return {
        "org_id": tenant.org_id,
        "facts_vault_version": "1.0",
        "facts": repo.list_facts(),
    }


@router.post("/brand/facts", status_code=status.HTTP_201_CREATED)
def create_brand_fact(
    payload: ApprovedFact,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    _require_admin_or_manager_if_authenticated(tenant)
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    try:
        created_fact = repo.create_fact(payload)
        return {
            "org_id": tenant.org_id,
            "facts_vault_version": "1.0",
            "fact": created_fact,
        }
    except DuplicateResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "DUPLICATE_FACT_ID",
                "message": str(exc),
            },
        )


@router.post("/brand/facts/upload-csv", response_model=CsvFactsUploadResponse)
async def upload_approved_facts_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    _require_admin_or_manager_if_authenticated(tenant)
    max_csv_bytes = int(os.getenv("MAX_CSV_UPLOAD_BYTES", str(settings.max_csv_upload_bytes)))
    file_bytes = await file.read(max_csv_bytes + 1)
    try:
        candidate_facts, row_errors, total_rows = parse_approved_facts_csv(
            file_bytes, file.filename or "Approved_Facts.csv"
        )
    except IngestionValidationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": exc.error_code, "message": exc.message},
        )

    repo = GovernanceRepository(db, org_id=tenant.org_id)
    saved_facts = []
    for fact in candidate_facts:
        try:
            saved = repo.create_fact(fact)
            saved_facts.append(saved)
        except DuplicateResourceError as exc:
            row_errors.append(
                CsvRowError(
                    row_number=fact.verified_page_or_row,
                    fact_id=fact.fact_id,
                    error_code="DUPLICATE_FACT_ID",
                    message=str(exc),
                )
            )

    return CsvFactsUploadResponse(
        org_id=tenant.org_id,
        document_name=file.filename or "Approved_Facts.csv",
        total_rows_processed=total_rows,
        saved_facts_count=len(saved_facts),
        saved_facts=saved_facts,
        row_errors=row_errors,
    )


@router.get("/brand/palette")
def list_brand_palette(
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    return {
        "org_id": tenant.org_id,
        "palette": repo.list_palettes(),
    }


@router.post("/brand/palette", status_code=status.HTTP_201_CREATED)
def create_brand_palette_item(
    payload: BrandPaletteItem,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    _require_admin_or_manager_if_authenticated(tenant)
    repo = GovernanceRepository(db, org_id=tenant.org_id)
    try:
        created = repo.create_palette_item(payload)
        return {
            "org_id": tenant.org_id,
            "palette_item": created,
        }
    except DuplicateResourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "DUPLICATE_PALETTE_ID", "message": str(exc)},
        )


@router.post("/audits", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
def create_audit(
    payload: AuditCreateRequest,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    effective_payload = (
        payload.model_copy(update={"submitted_by_role": tenant.role})
        if (not tenant.is_demo_fallback and tenant.role is not None)
        else payload
    )
    return orchestrator.run_audit(db, effective_payload, org_id=tenant.org_id)


@router.get("/audits/{audit_id}", response_model=AuditResponse)
def get_audit_by_id(
    audit_id: str,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    audit = orchestrator.get_audit(db, audit_id, org_id=tenant.org_id)
    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "AUDIT_NOT_FOUND", "message": f"No audit found with ID '{audit_id}'."},
        )
    return audit


@router.post("/audits/{audit_id}/review", response_model=AuditResponse)
def review_audit(
    audit_id: str,
    payload: ReviewDecisionRequest,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    effective_role = payload.actor_role
    if not tenant.is_demo_fallback and tenant.role is not None:
        if payload.actor_role != tenant.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ROLE_SPOOFING_FORBIDDEN",
                    "message": (
                        f"Authenticated membership role '{tenant.role.value}' does not match "
                        f"client-supplied actor_role '{payload.actor_role.value}'."
                    ),
                },
            )
        effective_role = tenant.role

    try:
        return orchestrator.record_review_decision(
            db=db,
            audit_id=audit_id,
            actor_role=effective_role,
            decision=payload.decision,
            override_justification=payload.override_justification,
            org_id=tenant.org_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "AUDIT_NOT_FOUND", "message": str(exc)},
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "MAKER_CHECKER_OR_ROLE_FORBIDDEN", "message": str(exc)},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_REVIEW_TRANSITION", "message": str(exc)},
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "HMAC_SIGNING_CONFIG_ERROR", "message": str(exc)},
        )

@router.post(
    "/audits/{audit_id}/findings/{finding_id}/rewrite",
    response_model=OnDemandRewriteResponse,
)
def generate_and_validate_finding_rewrite(
    audit_id: str,
    finding_id: str,
    payload: OnDemandRewriteRequest,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    try:
        return orchestrator.request_on_demand_rewrite(
            db=db,
            audit_id=audit_id,
            finding_id=finding_id,
            payload=payload,
            org_id=tenant.org_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "AUDIT_OR_FINDING_NOT_FOUND", "message": str(exc)},
        )
       
@router.get(
    "/audits/{audit_id}/verify-snapshot",
    response_model=SnapshotVerificationResponse,
)
def verify_audit_snapshot(
    audit_id: str,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    try:
        return orchestrator.verify_audit_snapshot_integrity(
            db=db,
            audit_id=audit_id,
            org_id=tenant.org_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "AUDIT_NOT_FOUND", "message": str(exc)},
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "HMAC_SIGNING_CONFIG_ERROR", "message": str(exc)},
        )


@router.get(
    "/audits/{audit_id}/export",
    response_model=ComplianceExportResponse,
)
def export_audit_compliance_report(
    audit_id: str,
    db: Session = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_context),
):
    try:
        return orchestrator.export_compliance_package(
            db=db,
            audit_id=audit_id,
            org_id=tenant.org_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "AUDIT_NOT_FOUND", "message": str(exc)},
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "HMAC_SIGNING_CONFIG_ERROR", "message": str(exc)},
        )