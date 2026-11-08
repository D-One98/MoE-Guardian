import React, { useState, useMemo } from 'react';
import type {
    AuditResponse,
    Severity,
    UnifiedFinding,
} from '../../types/contracts';
import type { NavRoute } from '../layout/Sidebar';
import { SeverityBadge, VerificationBadge } from '../ui/Badge';
import {
    AlertTriangle,
    Database,
    Sparkles,
    Check,
    Filter,
    ArrowUpRight,
    ShieldAlert,
    FileText,
    CornerDownRight,
    CheckCircle2,
} from 'lucide-react';

interface FindingsViewProps {
    audit: AuditResponse;
    isStale: boolean;
    appliedFindingIds: string[];
    findingOverrides: Record<string, string>;
    onApplyRewrite: (finding: UnifiedFinding) => void;
    onSaveFindingOverride: (findingId: string, justification: string) => void;
    onRunAudit: () => void;
    onNavigate: (route: NavRoute) => void;
}

export const FindingsView: React.FC<FindingsViewProps> = ({
    audit,
    isStale,
    appliedFindingIds,
    findingOverrides,
    onApplyRewrite,
    onSaveFindingOverride,
    onRunAudit,
    onNavigate,
}) => {
    const [selectedEngine, setSelectedEngine] = useState<string>('ALL');
    const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL');
    const [draftOverrideText, setDraftOverrideText] = useState<Record<string, string>>({});

    const filteredFindings = useMemo(() => {
        return audit.findings.filter((f) => {
            const matchEngine =
                selectedEngine === 'ALL' || f.expert_engine === selectedEngine;
            const matchSeverity =
                selectedSeverity === 'ALL' || f.severity === selectedSeverity;
            return matchEngine && matchSeverity;
        });
    }, [audit.findings, selectedEngine, selectedSeverity]);

    const handleOverrideSubmit = (findingId: string) => {
        const text = (draftOverrideText[findingId] || '').trim();
        if (text.length < 10) {
            alert(
                'Please enter a clear written justification (at least 10 characters) to record an override request.'
            );
            return;
        }
        onSaveFindingOverride(findingId, text);
    };

    return (
        <div className="space-y-6">
            {/* Stale Findings Guard Banner */}
            {isStale && (
                <div className="bg-amber-950/50 border border-amber-800/80 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                            <div className="text-xs font-semibold text-amber-200 uppercase font-mono">
                                Document Modified Since Audit ({audit.audit_id})
                            </div>
                            <p className="text-xs text-amber-300/90">
                                Applying surgical rewrites is locked while findings are stale. Re-run the audit to synchronize block anchors with your latest edits.
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onRunAudit}
                        className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 text-xs font-semibold font-mono shrink-0 transition-colors cursor-pointer"
                    >
                        Re-Run Audit Now
                    </button>
                </div>
            )}

            {/* Top Filter & Governance Summary Bar */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800/80 pb-4">
                    <div className="space-y-1">
                        <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
                            <span>Audit ID: <strong className="text-zinc-200">{audit.audit_id}</strong></span>
                            <span>•</span>
                            <span>Total Findings: <strong className="text-emerald-400">{audit.findings.length}</strong></span>
                            <span>•</span>
                            <span>Human Review Required: <strong className="text-amber-400">{String(audit.human_review_required)}</strong></span>
                        </div>
                        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
                            Audit Findings, Backend-Resolved Citations & Surgical Rewrites
                        </h2>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                        <button
                            type="button"
                            onClick={() => onNavigate('editor')}
                            className="px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors cursor-pointer"
                        >
                            ← Back to Editor
                        </button>
                        <button
                            type="button"
                            onClick={() => onNavigate('review')}
                            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-colors cursor-pointer"
                        >
                            <span>Proceed to Review Queue</span>
                            <ArrowUpRight className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>

                {/* Filter Controls */}
                <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-1 text-zinc-400 font-medium mr-1">
                            <Filter className="w-3.5 h-3.5 text-emerald-400" />
                            Engine:
                        </span>
                        {['ALL', 'RuleGuard', 'ClaimGuard', 'VisualGuard', 'VoiceGuard'].map(
                            (eng) => (
                                <button
                                    key={eng}
                                    type="button"
                                    onClick={() => setSelectedEngine(eng)}
                                    className={`px-2.5 py-1 rounded-md font-mono text-[11px] transition-colors cursor-pointer border ${selectedEngine === eng
                                            ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700/80'
                                            : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'
                                        }`}
                                >
                                    {eng}
                                </button>
                            )
                        )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        <span className="text-zinc-400 font-medium mr-1">Severity:</span>
                        {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const).map(
                            (sev) => (
                                <button
                                    key={sev}
                                    type="button"
                                    onClick={() => setSelectedSeverity(sev)}
                                    className={`px-2.5 py-1 rounded-md font-mono text-[11px] transition-colors cursor-pointer border ${selectedSeverity === sev
                                            ? 'bg-zinc-800 text-zinc-100 border-zinc-600'
                                            : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'
                                        }`}
                                >
                                    {sev}
                                </button>
                            )
                        )}
                    </div>
                </div>
            </div>

            {/* Findings List */}
            {filteredFindings.length === 0 ? (
                <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-10 text-center space-y-2">
                    <div className="text-sm font-semibold text-zinc-300">
                        No findings match the selected filter criteria.
                    </div>
                    <p className="text-xs text-zinc-500">
                        Try resetting the Engine or Severity filter pills above.
                    </p>
                </div>
            ) : (
                <div className="space-y-4">
                    {filteredFindings.map((finding) => {
                        const isNonCompliantExecution =
                            finding.execution_state === 'ERROR' ||
                            finding.execution_state === 'INSUFFICIENT_DATA';
                        const isRewriteApplied = appliedFindingIds.includes(finding.finding_id);
                        const savedOverride = findingOverrides[finding.finding_id];
                        const rc = finding.rewrite_candidate;
                        const canApplyRewrite =
                            Boolean(rc && rc.backend_revalidation.revalidation_passed) &&
                            !isStale &&
                            !isRewriteApplied;

                        return (
                            <div
                                key={finding.finding_id}
                                className={`bg-[#121215] rounded-xl border transition-all overflow-hidden ${isRewriteApplied
                                        ? 'border-emerald-800/70'
                                        : isNonCompliantExecution
                                            ? 'border-purple-800/80'
                                            : 'border-zinc-800/90'
                                    }`}
                            >
                                {/* Card Header Bar */}
                                <div className="px-5 py-3.5 bg-zinc-900/60 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-3">
                                    <div className="flex flex-wrap items-center gap-2.5">
                                        <span className="font-mono text-xs font-bold text-zinc-100">
                                            {finding.finding_id}
                                        </span>
                                        <span className="px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-200 font-mono text-[11px] font-semibold">
                                            {finding.expert_engine}
                                        </span>
                                        <span className="px-2 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-zinc-400 font-mono text-[11px]">
                                            {finding.finding_type}
                                        </span>
                                        <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1">
                                            <FileText className="w-3 h-3 text-zinc-500" />
                                            Block:{' '}
                                            <strong className="text-zinc-200">
                                                {finding.document_block_id || 'UNANCHORED_SIDEBAR'}
                                            </strong>
                                        </span>
                                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-950 text-zinc-500 border border-zinc-800/80">
                                            {finding.anchor_resolution_status}
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <SeverityBadge severity={finding.severity as Severity} />
                                        <VerificationBadge
                                            status={finding.verification_status}
                                            executionState={finding.execution_state}
                                        />
                                    </div>
                                </div>

                                {/* Card Body */}
                                <div className="p-5 space-y-4">
                                    {/* Section 4E Mandate: Never display ERROR or INSUFFICIENT_DATA as compliant */}
                                    {isNonCompliantExecution && (
                                        <div className="p-3.5 rounded-lg bg-purple-950/40 border border-purple-800/70 flex items-start gap-3 text-xs">
                                            <ShieldAlert className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
                                            <div className="space-y-0.5">
                                                <div className="font-mono font-semibold text-purple-200">
                                                    NON-COMPLIANT EXECUTION STATE: {finding.execution_state}
                                                </div>
                                                <p className="text-purple-300/90">
                                                    This check did not complete with an OK state and cannot be treated as compliant. Mandatory human inspection is required before approval.
                                                </p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Matched Text & Context Span */}
                                    <div className="space-y-1.5">
                                        <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                                            Matched Content Span & Context
                                        </div>
                                        {finding.matched_text ? (
                                            <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/90 font-mono text-xs text-zinc-400 leading-relaxed">
                                                <span>{finding.prefix_context || ''}</span>
                                                <mark className="px-1.5 py-0.5 mx-0.5 rounded bg-red-950/90 text-red-300 border border-red-800/70 font-semibold">
                                                    {finding.matched_text}
                                                </mark>
                                                <span>{finding.suffix_context || ''}</span>
                                            </div>
                                        ) : (
                                            <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 font-mono text-xs text-zinc-500">
                                                No inline substring match (Sidebar / Visual / Document-Level Finding)
                                            </div>
                                        )}
                                    </div>

                                    {/* Explanation */}
                                    <div className="space-y-1">
                                        <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
                                            Diagnostic Explanation
                                        </div>
                                        <p className="text-sm text-zinc-200 leading-relaxed">
                                            {finding.explanation}
                                        </p>
                                    </div>

                                    {/* Evidence / Source Reference from PostgreSQL */}
                                    {finding.evidence_reference ? (
                                        <div className="p-4 rounded-lg bg-zinc-950/90 border border-zinc-800 space-y-2">
                                            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                                                <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                                                    <Database className="w-3.5 h-3.5" />
                                                    <span>
                                                        Backend-Resolved Citation: {finding.evidence_reference.reference_id}
                                                    </span>
                                                    <span className="px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-300 border border-zinc-800 text-[10px]">
                                                        {finding.evidence_reference.source_type}
                                                    </span>
                                                </div>
                                                <span className="text-zinc-400">
                                                    Document: <strong className="text-zinc-200">{finding.evidence_reference.document_name}</strong>{' '}
                                                    (Page/Row {finding.evidence_reference.verified_page_or_row})
                                                </span>
                                            </div>
                                            <blockquote className="pl-3 border-l-2 border-emerald-500/70 text-xs text-zinc-300 italic">
                                                "{finding.evidence_reference.canonical_excerpt_from_db}"
                                            </blockquote>
                                        </div>
                                    ) : (
                                        <div className="p-3 rounded-lg bg-zinc-950/60 border border-zinc-800/70 text-xs font-mono text-zinc-500">
                                            Evidence Reference: None resolved in Approved Facts Vault (Requires Human Verification)
                                        </div>
                                    )}

                                    {/* Suggested Surgical Rewrite & Fail-Closed Backend Re-Validation */}
                                    {rc && (
                                        <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-800/50 space-y-3">
                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-300">
                                                    <Sparkles className="w-4 h-4 text-emerald-400" />
                                                    <span>
                                                        Suggested Surgical Rewrite ({rc.candidate_id})
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-2 font-mono text-[11px]">
                                                    <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300">
                                                        candidate_status: {rc.backend_revalidation.candidate_verification_status}
                                                    </span>
                                                    <span
                                                        className={`px-2 py-0.5 rounded font-semibold border ${rc.backend_revalidation.revalidation_passed
                                                                ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                                                                : 'bg-red-950 text-red-300 border-red-800'
                                                            }`}
                                                    >
                                                        revalidation_passed: {String(rc.backend_revalidation.revalidation_passed)}
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Suggested Text Diff Preview */}
                                            <div className="p-3 rounded bg-zinc-950 border border-zinc-800 space-y-1.5 text-xs font-mono">
                                                {finding.matched_text && (
                                                    <div className="text-red-400/90 line-through">
                                                        - {finding.matched_text}
                                                    </div>
                                                )}
                                                <div className="text-emerald-300 font-medium">
                                                    + {rc.suggested_text}
                                                </div>
                                            </div>

                                            {/* Executed Revalidation Checks Metadata */}
                                            <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                                                <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-zinc-400">
                                                    <span>
                                                        assigned_by: {rc.backend_revalidation.assigned_by}
                                                    </span>
                                                    {Object.entries(
                                                        rc.backend_revalidation.executed_checks
                                                    ).map(([k, v]) => (
                                                        <span
                                                            key={k}
                                                            className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300"
                                                        >
                                                            {k}: {String(v)}
                                                        </span>
                                                    ))}
                                                </div>

                                                <button
                                                    type="button"
                                                    disabled={!canApplyRewrite}
                                                    onClick={() => onApplyRewrite(finding)}
                                                    className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-colors shrink-0 ${isRewriteApplied
                                                            ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700 cursor-default'
                                                            : canApplyRewrite
                                                                ? 'bg-emerald-600 hover:bg-emerald-500 text-white cursor-pointer'
                                                                : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                                                        }`}
                                                >
                                                    {isRewriteApplied ? (
                                                        <>
                                                            <CheckCircle2 className="w-3.5 h-3.5" />
                                                            <span>Rewrite Applied to Block</span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Check className="w-3.5 h-3.5" />
                                                            <span>Apply Surgical Rewrite</span>
                                                        </>
                                                    )}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Creator Exception / Override Justification Bar */}
                                    <div className="pt-2 border-t border-zinc-800/80 space-y-2">
                                        {savedOverride ? (
                                            <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/70 flex items-center justify-between gap-4 text-xs">
                                                <div>
                                                    <span className="font-mono font-semibold text-amber-300 uppercase">
                                                        Override Justification Recorded:{' '}
                                                    </span>
                                                    <span className="text-amber-100 italic">
                                                        "{savedOverride}"
                                                    </span>
                                                </div>
                                                <span className="text-[11px] font-mono text-amber-400 shrink-0">
                                                    Escalated for Reviewer Sign-Off
                                                </span>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                                                <div className="flex items-center gap-1.5 text-xs text-zinc-400 shrink-0">
                                                    <CornerDownRight className="w-3.5 h-3.5 text-zinc-500" />
                                                    <span>Request Override:</span>
                                                </div>
                                                <input
                                                    type="text"
                                                    value={draftOverrideText[finding.finding_id] || ''}
                                                    onChange={(e) =>
                                                        setDraftOverrideText((prev) => ({
                                                            ...prev,
                                                            [finding.finding_id]: e.target.value,
                                                        }))
                                                    }
                                                    placeholder="Enter mandatory written justification to keep original phrasing (escalates to Reviewer)..."
                                                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-amber-500/70"
                                                />
                                                <button
                                                    type="button"
                                                    onClick={() => handleOverrideSubmit(finding.finding_id)}
                                                    className="px-3.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-xs font-medium text-zinc-200 shrink-0 transition-colors cursor-pointer"
                                                >
                                                    Record Override Justification
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};