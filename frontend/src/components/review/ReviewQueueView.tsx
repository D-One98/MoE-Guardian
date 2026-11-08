import React, { useState, useMemo } from 'react';
import type {
    AuditResponse,
    DemoRole,
    ReviewDecisionRequest,
    Severity,
} from '../../types/contracts';
import type { NavRoute } from '../layout/Sidebar';
import {
    AuditStatusBadge,
    SeverityBadge,
    VerificationBadge,
} from '../ui/Badge';
import {
    Lock,
    Check,
    X,
    AlertTriangle,
    ShieldAlert,
    FileText,
    UserCheck,
    ArrowRight,
} from 'lucide-react';

interface ReviewQueueViewProps {
    audit: AuditResponse;
    currentRole: DemoRole;
    isStale: boolean;
    appliedFindingIds: string[];
    findingOverrides: Record<string, string>;
    onSubmitReviewDecision: (req: ReviewDecisionRequest) => void;
    onRunAudit: () => void;
    onNavigate: (route: NavRoute) => void;
}

export const ReviewQueueView: React.FC<ReviewQueueViewProps> = ({
    audit,
    currentRole,
    isStale,
    appliedFindingIds,
    findingOverrides,
    onSubmitReviewDecision,
    onRunAudit,
    onNavigate,
}) => {
    const [reviewerNotes, setReviewerNotes] = useState<string>('');
    const [validationError, setValidationError] = useState<string | null>(null);

    const isCreatorRole = currentRole === 'CREATOR';

    // Calculate unresolved findings & high-risk counts
    const unresolvedFindings = useMemo(
        () =>
            audit.findings.filter((f) => !appliedFindingIds.includes(f.finding_id)),
        [audit.findings, appliedFindingIds]
    );

    const highRiskCount = useMemo(
        () =>
            unresolvedFindings.filter(
                (f) =>
                    f.severity === 'CRITICAL' ||
                    f.severity === 'HIGH' ||
                    f.verification_status === 'UNVERIFIABLE' ||
                    f.verification_status === 'CONTRADICTED' ||
                    f.execution_state === 'INSUFFICIENT_DATA' ||
                    f.execution_state === 'ERROR'
            ).length,
        [unresolvedFindings]
    );

    const requiresOverrideJustification = unresolvedFindings.length > 0;

    const handleDecision = (decision: 'APPROVE' | 'REQUEST_CHANGES') => {
        setValidationError(null);

        if (isCreatorRole) {
            setValidationError(
                'Maker-Checker Restriction: Content Creators cannot approve or reject their own submissions. Switch role to BRAND_MANAGER or AUTHORISED_REVIEWER.'
            );
            return;
        }

        if (isStale) {
            setValidationError(
                'Draft has been modified since the last audit. Re-run the VERITY MoE audit before recording a review decision.'
            );
            return;
        }

        if (
            decision === 'APPROVE' &&
            requiresOverrideJustification &&
            reviewerNotes.trim().length < 12
        ) {
            setValidationError(
                'Mandatory Override Justification Required: Because unresolved findings remain on this draft, you must provide a written justification (minimum 12 characters) to approve.'
            );
            return;
        }

        if (decision === 'REQUEST_CHANGES' && reviewerNotes.trim().length < 5) {
            setValidationError(
                'Please provide brief review notes (minimum 5 characters) explaining the requested changes.'
            );
            return;
        }

        onSubmitReviewDecision({
            actor_role: currentRole,
            decision,
            override_justification: reviewerNotes.trim() || null,
        });
    };

    return (
        <div className="space-y-6">
            {/* Stale Audit Guard */}
            {isStale && (
                <div className="bg-amber-950/50 border border-amber-800/80 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                            <div className="text-xs font-semibold text-amber-200 uppercase font-mono">
                                Review Sign-Off Locked — Audit Findings Are Stale
                            </div>
                            <p className="text-xs text-amber-300/90">
                                The draft content was edited after audit {audit.audit_id}. Re-run the audit so the review decision binds to the current revision hash.
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onRunAudit}
                        className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 text-xs font-semibold font-mono shrink-0 cursor-pointer"
                    >
                        Re-Run Audit Now
                    </button>
                </div>
            )}

            {/* Top Maker-Checker Header Card */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-zinc-400">
                        <span>Review Queue</span>
                        <span>•</span>
                        <span>Audit ID: <strong className="text-zinc-100">{audit.audit_id}</strong></span>
                        <span>•</span>
                        <span>Submitted By: <strong className="text-zinc-200">{audit.submitted_by_role}</strong></span>
                    </div>
                    <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
                        Human-in-the-Loop Governance Review & Maker-Checker Sign-Off
                    </h2>
                </div>

                <div className="flex items-center gap-3">
                    <AuditStatusBadge status={audit.overall_status} />
                    <div className="px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-mono flex items-center gap-2">
                        <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-zinc-400">Actor:</span>
                        <strong className="text-emerald-300">{currentRole}</strong>
                    </div>
                </div>
            </div>

            {/* Main 12-Column Split Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left 7 Columns: Draft Summary & Findings Summary */}
                <div className="lg:col-span-7 space-y-6">
                    {/* Draft Content Summary Card */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl overflow-hidden">
                        <div className="px-5 py-3.5 bg-zinc-900/60 border-b border-zinc-800/80 flex items-center justify-between">
                            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
                                <FileText className="w-4 h-4 text-emerald-400" />
                                <span>Submitted Draft Summary ({audit.blocks.length} Canonical Blocks)</span>
                            </div>
                            <span className="font-mono text-[11px] text-zinc-500 truncate max-w-[220px]">
                                {audit.document_revision_hash}
                            </span>
                        </div>

                        <div className="p-5 space-y-3">
                            {audit.blocks.map((block) => (
                                <div
                                    key={block.document_block_id}
                                    className="p-3.5 rounded-lg bg-zinc-950/90 border border-zinc-800/80 space-y-1.5"
                                >
                                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500">
                                        <span>{block.document_block_id}</span>
                                        <span>{block.text.length} chars</span>
                                    </div>
                                    <p className="text-sm text-zinc-200 leading-relaxed">
                                        {block.text}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Findings & Creator Overrides Summary */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl overflow-hidden">
                        <div className="px-5 py-3.5 bg-zinc-900/60 border-b border-zinc-800/80 flex items-center justify-between">
                            <span className="text-xs font-semibold text-zinc-200">
                                Findings & Exception Summary ({unresolvedFindings.length} Unresolved / {appliedFindingIds.length} Rewritten)
                            </span>
                            <button
                                type="button"
                                onClick={() => onNavigate('findings')}
                                className="text-xs font-mono text-emerald-400 hover:underline cursor-pointer"
                            >
                                Inspect Full Evidence →
                            </button>
                        </div>

                        <div className="divide-y divide-zinc-800/70">
                            {audit.findings.map((f) => {
                                const isResolvedByRewrite = appliedFindingIds.includes(f.finding_id);
                                const creatorOverride = findingOverrides[f.finding_id];

                                return (
                                    <div key={f.finding_id} className="p-4 space-y-2 text-xs">
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <div className="flex items-center gap-2 font-mono">
                                                <span className="font-bold text-zinc-200">{f.finding_id}</span>
                                                <span className="text-zinc-400">[{f.expert_engine}]</span>
                                                <span className="text-zinc-500">
                                                    {f.document_block_id || 'SIDEBAR'}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {isResolvedByRewrite && (
                                                    <span className="px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800 text-[10px] font-mono">
                                                        REWRITE_APPLIED
                                                    </span>
                                                )}
                                                <SeverityBadge severity={f.severity as Severity} />
                                                <VerificationBadge
                                                    status={f.verification_status}
                                                    executionState={f.execution_state}
                                                />
                                            </div>
                                        </div>

                                        <p className="text-zinc-300">{f.explanation}</p>

                                        {creatorOverride && (
                                            <div className="p-2.5 rounded bg-amber-950/40 border border-amber-800/70 text-amber-200 font-mono text-[11px]">
                                                Creator Override Request: "{creatorOverride}"
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Right 5 Columns: Risk Escalation & Maker-Checker Decision Console */}
                <div className="lg:col-span-5 space-y-6">
                    {/* Risk Assessment Card */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                        <div className="flex items-center gap-2">
                            <ShieldAlert className="w-4 h-4 text-amber-400" />
                            <h3 className="text-sm font-semibold text-zinc-100">
                                Risk & Escalation Telemetry
                            </h3>
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                            <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                                <div className="text-zinc-500 text-[10px] uppercase">
                                    Unresolved Findings
                                </div>
                                <div className="text-xl font-bold text-zinc-100 mt-0.5">
                                    {unresolvedFindings.length}
                                </div>
                            </div>
                            <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800">
                                <div className="text-zinc-500 text-[10px] uppercase">
                                    High / Critical / Unverified
                                </div>
                                <div className="text-xl font-bold text-red-400 mt-0.5">
                                    {highRiskCount}
                                </div>
                            </div>
                        </div>

                        <div className="p-3 rounded-lg bg-zinc-900/70 border border-zinc-800 text-xs space-y-1">
                            <div className="font-mono text-zinc-300">
                                Routing Status: <strong className="text-amber-300">{audit.overall_status}</strong>
                            </div>
                            <p className="text-zinc-400 text-[11px] leading-relaxed">
                                Drafts with high-risk promotional claims, UNVERIFIABLE facts, or INSUFFICIENT_DATA visual checks require human reviewer sign-off.
                            </p>
                        </div>
                    </div>

                    {/* Maker-Checker Action Console */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-zinc-100">
                                Review Decision Console
                            </h3>
                            <Lock className="w-4 h-4 text-zinc-500" />
                        </div>

                        {/* Self-Approval Guard Notice (Section 4F Mandatory Rule) */}
                        {isCreatorRole && (
                            <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-800/70 text-xs space-y-1.5">
                                <div className="font-mono font-semibold text-red-300 flex items-center gap-1.5">
                                    <Lock className="w-3.5 h-3.5 shrink-0" />
                                    <span>Maker-Checker Enforcement: Creator Self-Approval Blocked</span>
                                </div>
                                <p className="text-red-200/80 leading-relaxed text-[11px]">
                                    Creators cannot approve or reject their own submissions. Note: The FastAPI backend is the authoritative enforcement layer for role permissions; switch the active role selector in the top header to <code className="font-mono">AUTHORISED_REVIEWER</code> or <code className="font-mono">BRAND_MANAGER</code> to test reviewer sign-off.
                                </p>
                            </div>
                        )}

                        {validationError && (
                            <div className="p-3 rounded-lg bg-amber-950/60 border border-amber-700 text-amber-200 text-xs">
                                {validationError}
                            </div>
                        )}

                        {/* Mandatory Override Justification / Review Notes Input */}
                        <div className="space-y-1.5 text-xs">
                            <label className="block font-medium text-zinc-300">
                                Reviewer Notes / Mandatory Override Justification (
                                <code className="font-mono text-zinc-400">override_justification</code>)
                            </label>
                            <textarea
                                value={reviewerNotes}
                                onChange={(e) => setReviewerNotes(e.target.value)}
                                rows={4}
                                disabled={isCreatorRole}
                                placeholder={
                                    requiresOverrideJustification
                                        ? 'Mandatory written justification required to approve with unresolved findings, or explain requested changes...'
                                        : 'Enter optional review sign-off notes...'
                                }
                                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/70 disabled:opacity-50"
                            />
                            {requiresOverrideJustification && (
                                <p className="text-[11px] text-amber-400/90 font-mono">
                                    * {unresolvedFindings.length} finding(s) remain unresolved — approval requires written override justification.
                                </p>
                            )}
                        </div>

                        {/* Approve & Reject / Request Changes Buttons */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                            <button
                                type="button"
                                disabled={isCreatorRole || isStale}
                                onClick={() => handleDecision('REQUEST_CHANGES')}
                                className="py-2.5 px-4 rounded-lg bg-red-950/60 hover:bg-red-900/70 border border-red-800/80 text-red-200 text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                            >
                                <X className="w-4 h-4" />
                                <span>Reject / Request Changes</span>
                            </button>

                            <button
                                type="button"
                                disabled={isCreatorRole || isStale}
                                onClick={() => handleDecision('APPROVE')}
                                className="py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                            >
                                <Check className="w-4 h-4" />
                                <span>Approve & Record Snapshot</span>
                            </button>
                        </div>

                        {audit.latest_snapshot && (
                            <button
                                type="button"
                                onClick={() => onNavigate('records')}
                                className="w-full py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-mono text-emerald-400 flex items-center justify-center gap-1.5 cursor-pointer"
                            >
                                <span>View Recorded Snapshot ({audit.latest_snapshot.snapshot_id})</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};