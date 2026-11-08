import type {
  ApprovedFact,
  AuditCreateRequest,
  AuditResponse,
  BrandPaletteItem,
  BrandRule,
  ComplianceExportResponse,
  CsvFactsUploadResponse,
  GuidelineConfirmRequest,
  GuidelineUploadPreviewResponse,
  OnDemandRewriteRequest,
  OnDemandRewriteResponse,
  ReviewDecisionRequest,
  SnapshotVerificationResponse,
} from '../types/contracts';
import { apiRequest, apiUploadFile } from './api';
import {
  MOCK_APPROVED_FACTS,
  MOCK_BRAND_PALETTE,
  MOCK_BRAND_RULES,
  buildMockComplianceExport,
  buildMockCsvUploadResponse,
  buildMockPdfPreview,
  confirmMockGuidelines,
  createMockAudit,
  generateMockOnDemandRewrite,
  submitMockReviewDecision,
  verifyMockSnapshot,
} from './mockAdapter';

export const FORCE_MOCK_MODE =
  import.meta.env.VITE_USE_MOCK_ADAPTER === 'true';

// 1. GET /api/health
export async function checkBackendHealthService(): Promise<{
  online: boolean;
  details?: Record<string, unknown>;
}> {
  if (FORCE_MOCK_MODE) return { online: false };
  try {
    const res = await apiRequest<Record<string, unknown>>('/health');
    return { online: true, details: res };
  } catch {
    return { online: false };
  }
}

// 2. GET /api/auth/me
export async function fetchAuthContextService(): Promise<Record<string, unknown> | null> {
  if (FORCE_MOCK_MODE) return null;
  try {
    return await apiRequest<Record<string, unknown>>('/auth/me');
  } catch {
    return null;
  }
}

// 3. GET /api/demo/workspace
export async function fetchDemoWorkspaceService(): Promise<Record<string, unknown> | null> {
  if (FORCE_MOCK_MODE) return null;
  try {
    return await apiRequest<Record<string, unknown>>('/demo/workspace');
  } catch {
    return null;
  }
}

// 4 & 5. GET / POST /api/brand/rules
export async function listBrandRulesService(): Promise<BrandRule[]> {
  if (FORCE_MOCK_MODE) return MOCK_BRAND_RULES;
  try {
    return await apiRequest<BrandRule[]>('/brand/rules');
  } catch {
    return MOCK_BRAND_RULES;
  }
}

export async function createBrandRuleService(rule: BrandRule): Promise<BrandRule> {
  if (FORCE_MOCK_MODE) return rule;
  return apiRequest<BrandRule>('/brand/rules', {
    method: 'POST',
    body: JSON.stringify(rule),
  });
}

// 6 & 7. POST /api/brand/guidelines/upload-pdf & /{batch_id}/confirm
export async function uploadGuidelinePdfService(
  file: File
): Promise<GuidelineUploadPreviewResponse> {
  if (FORCE_MOCK_MODE) return buildMockPdfPreview(file.name);
  return apiUploadFile<GuidelineUploadPreviewResponse>(
    '/brand/guidelines/upload-pdf',
    file
  );
}

export async function confirmGuidelineRulesService(
  batchId: string,
  req: GuidelineConfirmRequest
): Promise<unknown> {
  if (FORCE_MOCK_MODE) return confirmMockGuidelines(req);
  return apiRequest<unknown>(`/brand/guidelines/${batchId}/confirm`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

// 8, 9 & 10. GET / POST /api/brand/facts & /upload-csv
export async function listApprovedFactsService(): Promise<ApprovedFact[]> {
  if (FORCE_MOCK_MODE) return MOCK_APPROVED_FACTS;
  try {
    return await apiRequest<ApprovedFact[]>('/brand/facts');
  } catch {
    return MOCK_APPROVED_FACTS;
  }
}

export async function createApprovedFactService(
  fact: ApprovedFact
): Promise<ApprovedFact> {
  if (FORCE_MOCK_MODE) return fact;
  return apiRequest<ApprovedFact>('/brand/facts', {
    method: 'POST',
    body: JSON.stringify(fact),
  });
}

export async function uploadApprovedFactsCsvService(
  file: File
): Promise<CsvFactsUploadResponse> {
  if (FORCE_MOCK_MODE) return buildMockCsvUploadResponse(file.name);
  return apiUploadFile<CsvFactsUploadResponse>('/brand/facts/upload-csv', file);
}

// 11 & 12. GET / POST /api/brand/palette
export async function listBrandPaletteService(): Promise<BrandPaletteItem[]> {
  if (FORCE_MOCK_MODE) return MOCK_BRAND_PALETTE;
  try {
    return await apiRequest<BrandPaletteItem[]>('/brand/palette');
  } catch {
    return MOCK_BRAND_PALETTE;
  }
}

export async function createBrandPaletteService(
  item: BrandPaletteItem
): Promise<BrandPaletteItem> {
  if (FORCE_MOCK_MODE) return item;
  return apiRequest<BrandPaletteItem>('/brand/palette', {
    method: 'POST',
    body: JSON.stringify(item),
  });
}

// 13 & 14. POST /api/audits & GET /api/audits/{audit_id}
export async function runAuditService(
  req: AuditCreateRequest,
  computedRevisionHash: string
): Promise<AuditResponse> {
  if (FORCE_MOCK_MODE) {
    return new Promise((resolve) => {
      setTimeout(() => resolve(createMockAudit(req, computedRevisionHash)), 1200);
    });
  }
  try {
    return await apiRequest<AuditResponse>('/audits', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  } catch {
    return createMockAudit(req, computedRevisionHash);
  }
}

export async function getAuditByIdService(auditId: string): Promise<AuditResponse> {
  return apiRequest<AuditResponse>(`/audits/${auditId}`);
}

// 15. POST /api/audits/{audit_id}/findings/{finding_id}/rewrite
export async function requestOnDemandRewriteService(
  currentAudit: AuditResponse,
  findingId: string,
  req: OnDemandRewriteRequest
): Promise<OnDemandRewriteResponse> {
  if (FORCE_MOCK_MODE) {
    return generateMockOnDemandRewrite(currentAudit, findingId, req);
  }
  try {
    return await apiRequest<OnDemandRewriteResponse>(
      `/audits/${currentAudit.audit_id}/findings/${findingId}/rewrite`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    );
  } catch {
    return generateMockOnDemandRewrite(currentAudit, findingId, req);
  }
}

// 16. POST /api/audits/{audit_id}/review
export async function submitReviewDecisionService(
  currentAudit: AuditResponse,
  req: ReviewDecisionRequest
): Promise<AuditResponse> {
  if (FORCE_MOCK_MODE) {
    return submitMockReviewDecision(currentAudit, req);
  }
  try {
    return await apiRequest<AuditResponse>(
      `/audits/${currentAudit.audit_id}/review`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    );
  } catch {
    return submitMockReviewDecision(currentAudit, req);
  }
}

// 17. GET /api/audits/{audit_id}/verify-snapshot
export async function verifySnapshotService(
  currentAudit: AuditResponse
): Promise<SnapshotVerificationResponse> {
  if (FORCE_MOCK_MODE) {
    return verifyMockSnapshot(currentAudit);
  }
  try {
    return await apiRequest<SnapshotVerificationResponse>(
      `/audits/${currentAudit.audit_id}/verify-snapshot`
    );
  } catch {
    return verifyMockSnapshot(currentAudit);
  }
}

// 18. GET /api/audits/{audit_id}/export
export async function exportAuditComplianceService(
  currentAudit: AuditResponse
): Promise<ComplianceExportResponse> {
  if (FORCE_MOCK_MODE) {
    return buildMockComplianceExport(currentAudit);
  }
  try {
    return await apiRequest<ComplianceExportResponse>(
      `/audits/${currentAudit.audit_id}/export`
    );
  } catch {
    return buildMockComplianceExport(currentAudit);
  }
}