import { useState, useEffect } from 'react';
import { AppShell } from './components/layout/AppShell';
import type { NavRoute } from './components/layout/Sidebar';
import type {
  AuditResponse,
  ContentBlock,
  DemoRole,
  ReviewDecisionRequest,
  UnifiedFinding,
} from './types/contracts';

import { INITIAL_CONTENT_BLOCKS } from './services/mockAdapter';

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

async function computeEditorRevisionHash(
  blocks: ContentBlock[],
  altText: string
): Promise<string> {
  const canonical = {
    alt_text: altText.trim(),
    blocks: blocks.map((block) => ({
      document_block_id: block.document_block_id,
      text: block.text.trim(),
    })),
  };

  const json = JSON.stringify(canonical).replace(
    /[\u007f-\uffff]/g,
    (char) =>
      `\\u${char.charCodeAt(0).toString(16).padStart(4, '0')}`
  );

  const digest = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(json)
  );

  const hex = Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');

  return `sha256:${hex}`;
}

export function App() {
  const [activeRoute, setActiveRoute] = useState<NavRoute>('dashboard');
  const [currentRole, setCurrentRole] = useState<DemoRole>('CREATOR');

  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(false);

  const [audit, setAudit] = useState<AuditResponse | null>(null);

  // Check backend availability.
  useEffect(() => {
    let cancelled = false;

    checkBackendHealthService()
      .then((res) => {
        if (!cancelled) {
          setIsBackendOnline(res.online);
        }
      })
      .catch((error) => {
        console.error('Backend health check failed:', error);

        if (!cancelled) {
          setIsBackendOnline(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Canonical editor state.
  const [campaignId, setCampaignId] = useState<string>(
    'CAMP-LAUNCH-2026'
  );

  const [blocks, setBlocks] = useState<ContentBlock[]>(
    INITIAL_CONTENT_BLOCKS
  );

  const [altText, setAltText] = useState<string>(
    'Enterprise product banner showing compliance dashboard on dark carbon background'
  );

  const [nextBlockSeq, setNextBlockSeq] = useState<number>(4);

  const [appliedFindingIds, setAppliedFindingIds] = useState<string[]>([]);

  const [findingOverrides, setFindingOverrides] = useState<
    Record<string, string>
  >({});

  // Asynchronous canonical SHA-256 revision hash.
  const [currentRevisionHash, setCurrentRevisionHash] = useState<string>('');

  useEffect(() => {
    let cancelled = false;

    const updateHash = async () => {
      try {
        const hash = await computeEditorRevisionHash(blocks, altText);

        if (!cancelled) {
          setCurrentRevisionHash(hash);
        }
      } catch (error) {
        console.error('Failed to compute document revision hash:', error);

        if (!cancelled) {
          setCurrentRevisionHash('');
        }
      }
    };

    void updateHash();

    return () => {
      cancelled = true;
    };
  }, [blocks, altText]);

  // No fabricated initial audit.
  const isStale = audit
    ? !currentRevisionHash ||
      currentRevisionHash !== audit.document_revision_hash
    : false;

  // Update editor block text.
  const handleUpdateBlockText = (
    blockId: string,
    newText: string
  ) => {
    setBlocks((prev) =>
      prev.map((block) =>
        block.document_block_id === blockId
          ? { ...block, text: newText }
          : block
      )
    );
  };

  // Apply a backend-revalidated surgical rewrite.
  const handleApplySurgicalRewrite = async (
    finding: UnifiedFinding
  ) => {
    if (
      !finding.document_block_id ||
      !finding.rewrite_candidate ||
      !finding.rewrite_candidate.backend_revalidation.revalidation_passed
    ) {
      return;
    }

    const updatedBlocks = blocks.map((block) => {
      if (block.document_block_id !== finding.document_block_id) {
        return block;
      }

      return {
        ...block,
        text: finding.rewrite_candidate!.suggested_text,
      };
    });

    try {
      const newSyncedHash = await computeEditorRevisionHash(
        updatedBlocks,
        altText
      );

      setBlocks(updatedBlocks);
      setCurrentRevisionHash(newSyncedHash);

      setAppliedFindingIds((prev) =>
        prev.includes(finding.finding_id)
          ? prev
          : [...prev, finding.finding_id]
      );

      setAudit((prev) =>
        prev
          ? {
              ...prev,
              blocks: updatedBlocks,
              document_revision_hash: newSyncedHash,
            }
          : null
      );
    } catch (error) {
      console.error('Failed to apply surgical rewrite:', error);

      window.alert(
        'Unable to apply rewrite. Please try again.'
      );
    }
  };

  // Save reviewer override justification locally.
  const handleSaveFindingOverride = (
    findingId: string,
    justification: string
  ) => {
    setFindingOverrides((prev) => ({
      ...prev,
      [findingId]: justification,
    }));

    setAudit((prev) =>
      prev
        ? {
            ...prev,
            overall_status: 'ESCALATED_TO_AUTHORISED_REVIEWER',
            human_review_required: true,
          }
        : null
    );
  };

  // Add a canonical content block.
  const handleAddBlock = () => {
    const formattedNum = String(nextBlockSeq).padStart(2, '0');

    setBlocks((prev) => [
      ...prev,
      {
        document_block_id: `blk-paragraph-${formattedNum}`,
        text: '',
      },
    ]);

    setNextBlockSeq((num) => num + 1);
  };

  // Remove a canonical content block.
  const handleRemoveBlock = (blockId: string) => {
    setBlocks((prev) =>
      prev.filter(
        (block) => block.document_block_id !== blockId
      )
    );
  };

  // Reset editor sample content without creating a fake audit.
  const handleResetDefaultBlocks = async () => {
    const defaultAlt =
      'Enterprise product banner showing compliance dashboard on dark carbon background';

    try {
      const syncedHash = await computeEditorRevisionHash(
        INITIAL_CONTENT_BLOCKS,
        defaultAlt
      );

      setBlocks(INITIAL_CONTENT_BLOCKS);
      setAltText(defaultAlt);
      setCurrentRevisionHash(syncedHash);

      setAppliedFindingIds([]);
      setFindingOverrides({});

      // Resetting sample content must not fabricate an audit.
      setAudit(null);
    } catch (error) {
      console.error('Failed to reset editor:', error);

      window.alert(
        'Unable to reset editor content. Please try again.'
      );
    }
  };

  // Run a real backend audit.
  const handleRunAudit = async () => {
    if (FORCE_MOCK_MODE) {
      window.alert(
        'Mock mode is enabled. Disable VITE_USE_MOCK_ADAPTER before running a live audit.'
      );
      return;
    }

    if (!isBackendOnline) {
      window.alert(
        'Backend is offline. Start the FastAPI server and try again.'
      );
      return;
    }

    if (blocks.length === 0) {
      window.alert(
        'Add at least one content block before running an audit.'
      );
      return;
    }

    setIsLoadingAudit(true);

    try {
      const freshRevisionHash = await computeEditorRevisionHash(
        blocks,
        altText
      );

      setCurrentRevisionHash(freshRevisionHash);

      const updatedAudit = await runAuditService(
        {
          campaign_id: campaignId,
          submitted_by_role: currentRole,
          blocks,
          alt_text: altText || null,
        },
        freshRevisionHash
      );

      setAppliedFindingIds([]);
      setFindingOverrides({});

      setAudit(updatedAudit);
      setActiveRoute('dashboard');
    } catch (error) {
      console.error('Audit execution failed:', error);

      window.alert(
        error instanceof Error
          ? `Audit failed: ${error.message}`
          : 'Audit failed. Please check the backend connection.'
      );
    } finally {
      setIsLoadingAudit(false);
    }
  };

  // Submit a real backend review decision.
  const handleSubmitReviewDecision = async (
    req: ReviewDecisionRequest
  ) => {
    if (!audit) {
      window.alert(
        'No audit available. Run an audit before submitting a review decision.'
      );
      return;
    }

    try {
      const updatedAudit = await submitReviewDecisionService(
        audit,
        req
      );

      setAudit(updatedAudit);
      setActiveRoute('records');
    } catch (error) {
      console.error('Review decision failed:', error);

      window.alert(
        error instanceof Error
          ? `Review failed: ${error.message}`
          : 'Review decision failed. Please check the backend.'
      );
    }
  };

  // Demo loader preview only; does not create an audit.
  const triggerLoaderPreview = () => {
    setIsLoadingAudit(true);

    setTimeout(() => {
      setIsLoadingAudit(false);
    }, 2400);
  };

  return (
    <AppShell
      activeRoute={activeRoute}
      onSelectRoute={setActiveRoute}
      currentRole={currentRole}
      onChangeRole={setCurrentRole}
      overallStatus={audit?.overall_status ?? 'PENDING_REVIEW'}
      auditId={audit?.audit_id ?? 'NO-AUDIT'}
      orgId={audit?.org_id ?? ''}
      findingsCount={audit?.findings.length ?? 0}
      isStale={isStale}
      isMockMode={FORCE_MOCK_MODE || !isBackendOnline}
      isLoadingAudit={isLoadingAudit}
      onTriggerDemoLoader={triggerLoaderPreview}
    >
      {activeRoute === 'dashboard' && (
        audit ? (
          <DashboardView
            audit={audit}
            isStale={isStale}
            onNavigate={setActiveRoute}
          />
        ) : (
          <div className="rounded-xl border border-zinc-800 p-8 text-center">
            <h2 className="text-lg font-semibold">
              No audit available
            </h2>

            <p className="mt-2 text-sm text-zinc-400">
              Submit your campaign content to run the first live audit.
            </p>

            <button
              onClick={() => setActiveRoute('editor')}
              className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold"
            >
              Open Content Editor
            </button>
          </div>
        )
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
          lastAuditedHash={audit?.document_revision_hash ?? ''}
          isStale={isStale}
          isLoadingAudit={isLoadingAudit}
          findings={audit?.findings ?? []}
          onRunAudit={handleRunAudit}
          onNavigate={setActiveRoute}
        />
      )}

      {activeRoute === 'findings' && (
        audit ? (
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
        ) : (
          <div className="rounded-xl border border-zinc-800 p-8 text-center text-zinc-400">
            No findings available. Run a live audit first.
          </div>
        )
      )}

      {activeRoute === 'review' && (
        audit ? (
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
        ) : (
          <div className="rounded-xl border border-zinc-800 p-8 text-center text-zinc-400">
            No review available. Run a live audit first.
          </div>
        )
      )}

      {activeRoute === 'records' && (
        audit ? (
          <AuditRecordsView
            audit={audit}
            isMockMode={FORCE_MOCK_MODE || !isBackendOnline}
            onNavigate={setActiveRoute}
          />
        ) : (
          <div className="rounded-xl border border-zinc-800 p-8 text-center text-zinc-400">
            No audit records available yet.
          </div>
        )
      )}

      {activeRoute === 'constitution' && (
        <BrandConstitutionView />
      )}
    </AppShell>
  );
}

export default App;