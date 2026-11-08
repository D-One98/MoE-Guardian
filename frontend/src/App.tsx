import { useState, useMemo, useEffect } from 'react';
import { AppShell } from './components/layout/AppShell';
import type { NavRoute } from './components/layout/Sidebar';
import type {
  AuditResponse,
  ContentBlock,
  DemoRole,
  ReviewDecisionRequest,
  UnifiedFinding,
} from './types/contracts';
import {
  INITIAL_CONTENT_BLOCKS,
  INITIAL_MOCK_AUDIT_RESPONSE,
} from './services/mockAdapter';
import {
  FORCE_MOCK_MODE,
  checkBackendHealthService,
  runAuditService,
  submitReviewDecisionService,
} from './services/auditService';
import { DashboardView } from './components/dashboard/DashboardView';
import { BlockEditorView } from './components/editor/BlockEditorView';
import { FindingsView } from './components/audit/FindingsView';
import { ReviewQueueView } from './components/review/ReviewQueueView';
import { AuditRecordsView } from './components/review/AuditRecordsView';
import { BrandConstitutionView } from './components/constitution/BrandConstitutionView';

function computeEditorRevisionHash(blocks: ContentBlock[], altText: string): string {
  const serialized =
    blocks.map((b) => `${b.document_block_id}:${b.text}`).join('||') +
    `||alt:${altText.trim()}`;
  let h1 = 0xdeadbeef ^ serialized.length;
  let h2 = 0x41c6ce57 ^ serialized.length;
  for (let i = 0, ch; i < serialized.length; i++) {
    ch = serialized.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 =
    Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^
    Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 =
    Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^
    Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  const hex =
    (h2 >>> 0).toString(16).padStart(8, '0') +
    (h1 >>> 0).toString(16).padStart(8, '0');
  return `sha256:${hex}e55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08`;
}

export function App() {
  const [activeRoute, setActiveRoute] = useState<NavRoute>('dashboard');
  const [currentRole, setCurrentRole] = useState<DemoRole>('CREATOR');
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(false);

  // Check if Divy's FastAPI server is live at VITE_API_BASE_URL/health
  useEffect(() => {
    void checkBackendHealthService().then((res) => {
      setIsBackendOnline(res.online);
    });
  }, []);

  // Canonical Editor State
  const [campaignId, setCampaignId] = useState<string>(
    INITIAL_MOCK_AUDIT_RESPONSE.campaign_id
  );
  const [blocks, setBlocks] = useState<ContentBlock[]>(INITIAL_CONTENT_BLOCKS);
  const [altText, setAltText] = useState<string>(
    'Enterprise product banner showing compliance dashboard on dark carbon background'
  );
  const [nextBlockSeq, setNextBlockSeq] = useState<number>(4);

  const [appliedFindingIds, setAppliedFindingIds] = useState<string[]>([]);
  const [findingOverrides, setFindingOverrides] = useState<Record<string, string>>({});

  const currentRevisionHash = useMemo(
    () => computeEditorRevisionHash(blocks, altText),
    [blocks, altText]
  );

  const [audit, setAudit] = useState<AuditResponse>(() => ({
    ...INITIAL_MOCK_AUDIT_RESPONSE,
    document_revision_hash: computeEditorRevisionHash(
      INITIAL_CONTENT_BLOCKS,
      'Enterprise product banner showing compliance dashboard on dark carbon background'
    ),
  }));

  const isStale = currentRevisionHash !== audit.document_revision_hash;

  const handleUpdateBlockText = (blockId: string, newText: string) => {
    setBlocks((prev) =>
      prev.map((b) =>
        b.document_block_id === blockId ? { ...b, text: newText } : b
      )
    );
  };

  const handleApplySurgicalRewrite = (finding: UnifiedFinding) => {
    if (
      !finding.document_block_id ||
      !finding.rewrite_candidate ||
      !finding.rewrite_candidate.backend_revalidation.revalidation_passed
    ) {
      return;
    }

    const updatedBlocks = blocks.map((b) => {
      if (b.document_block_id !== finding.document_block_id) return b;
      return {
        ...b,
        text: finding.rewrite_candidate!.suggested_text,
      };
    });

    const newSyncedHash = computeEditorRevisionHash(updatedBlocks, altText);
    setBlocks(updatedBlocks);
    setAppliedFindingIds((prev) => [...prev, finding.finding_id]);
    setAudit((prev) => ({
      ...prev,
      blocks: updatedBlocks,
      document_revision_hash: newSyncedHash,
    }));
  };

  const handleSaveFindingOverride = (findingId: string, justification: string) => {
    setFindingOverrides((prev) => ({
      ...prev,
      [findingId]: justification,
    }));
    setAudit((prev) => ({
      ...prev,
      overall_status: 'ESCALATED_TO_AUTHORISED_REVIEWER',
      human_review_required: true,
    }));
  };

  const handleAddBlock = () => {
    const formattedNum = String(nextBlockSeq).padStart(2, '0');
    setBlocks((prev) => [
      ...prev,
      { document_block_id: `blk-paragraph-${formattedNum}`, text: '' },
    ]);
    setNextBlockSeq((n) => n + 1);
  };

  const handleRemoveBlock = (blockId: string) => {
    setBlocks((prev) => prev.filter((b) => b.document_block_id !== blockId));
  };

  const handleResetDefaultBlocks = () => {
    const defaultAlt =
      'Enterprise product banner showing compliance dashboard on dark carbon background';
    setBlocks(INITIAL_CONTENT_BLOCKS);
    setAltText(defaultAlt);
    setAppliedFindingIds([]);
    setFindingOverrides({});
    const syncedHash = computeEditorRevisionHash(INITIAL_CONTENT_BLOCKS, defaultAlt);
    setAudit({
      ...INITIAL_MOCK_AUDIT_RESPONSE,
      document_revision_hash: syncedHash,
    });
  };

  const handleRunAudit = async () => {
    setIsLoadingAudit(true);
    try {
      const updatedAudit = await runAuditService(
        {
          campaign_id: campaignId,
          submitted_by_role: currentRole,
          blocks,
          alt_text: altText || null,
        },
        currentRevisionHash
      );
      setAppliedFindingIds([]);
      setAudit(updatedAudit);
    } finally {
      setIsLoadingAudit(false);
    }
  };

  const handleSubmitReviewDecision = async (req: ReviewDecisionRequest) => {
    const updatedAudit = await submitReviewDecisionService(audit, req);
    setAudit(updatedAudit);
    setActiveRoute('records');
  };

  const triggerLoaderPreview = () => {
    setIsLoadingAudit(true);
    setTimeout(() => setIsLoadingAudit(false), 2400);
  };

  return (
    <AppShell
      activeRoute={activeRoute}
      onSelectRoute={setActiveRoute}
      currentRole={currentRole}
      onChangeRole={setCurrentRole}
      overallStatus={audit.overall_status}
      auditId={audit.audit_id}
      orgId={audit.org_id}
      findingsCount={audit.findings.length}
      isStale={isStale}
      isMockMode={FORCE_MOCK_MODE || !isBackendOnline}
      isLoadingAudit={isLoadingAudit}
      onTriggerDemoLoader={triggerLoaderPreview}
    >
      {activeRoute === 'dashboard' && (
        <DashboardView
          audit={audit}
          isStale={isStale}
          onNavigate={setActiveRoute}
        />
      )}

      {activeRoute === 'editor' && (
        <BlockEditorView
          campaignId={campaignId}
          onChangeCampaignId={setCampaignId}
          blocks={blocks}
          onUpdateBlockText={handleUpdateBlockText}
          onAddBlock={handleAddBlock}
          onRemoveBlock={handleRemoveBlock}
          onResetDefaultBlocks={handleResetDefaultBlocks}
          altText={altText}
          onChangeAltText={setAltText}
          currentRole={currentRole}
          currentRevisionHash={currentRevisionHash}
          lastAuditedHash={audit.document_revision_hash}
          isStale={isStale}
          isLoadingAudit={isLoadingAudit}
          findings={audit.findings}
          onRunAudit={handleRunAudit}
          onNavigate={setActiveRoute}
        />
      )}

      {activeRoute === 'findings' && (
        <FindingsView
          audit={audit}
          isStale={isStale}
          appliedFindingIds={appliedFindingIds}
          findingOverrides={findingOverrides}
          onApplyRewrite={handleApplySurgicalRewrite}
          onSaveFindingOverride={handleSaveFindingOverride}
          onRunAudit={handleRunAudit}
          onNavigate={setActiveRoute}
        />
      )}

      {activeRoute === 'review' && (
        <ReviewQueueView
          audit={audit}
          currentRole={currentRole}
          isStale={isStale}
          appliedFindingIds={appliedFindingIds}
          findingOverrides={findingOverrides}
          onSubmitReviewDecision={handleSubmitReviewDecision}
          onRunAudit={handleRunAudit}
          onNavigate={setActiveRoute}
        />
      )}

      {activeRoute === 'records' && (
        <AuditRecordsView
          audit={audit}
          isMockMode={FORCE_MOCK_MODE || !isBackendOnline}
          onNavigate={setActiveRoute}
        />
      )}

      {activeRoute === 'constitution' && <BrandConstitutionView />}
    </AppShell>
  );
}

export default App;