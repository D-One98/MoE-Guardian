import React, { useMemo, useState } from 'react';
import type { AuditResponse, Severity } from '../../types/contracts';
import type { NavRoute } from '../layout/Sidebar';
import {
    SeverityBadge,
    VerificationBadge,
    AuditStatusBadge,
} from '../ui/Badge';
import {
    Shield,
    FileSearch,
    Eye,
    Mic,
    MoreHorizontal,
    Plus,
    ArrowUpRight,
    Lock,
    Download,
    Clock,
    Layers,
    Copy,
    Check,
} from 'lucide-react';

interface DashboardViewProps {
    audit: AuditResponse;
    isStale: boolean;
    onNavigate: (route: NavRoute) => void;
}

const ENGINE_ICONS: Record<string, React.ReactNode> = {
    RuleGuard: <Shield className="w-4 h-4 text-emerald-400" />,
    ClaimGuard: <FileSearch className="w-4 h-4 text-amber-400" />,
    VisualGuard: <Eye className="w-4 h-4 text-sky-400" />,
    VoiceGuard: <Mic className="w-4 h-4 text-purple-400" />,
};

export const DashboardView: React.FC<DashboardViewProps> = ({
    audit,
    isStale,
    onNavigate,
}) => {
    const [copiedHash, setCopiedHash] = useState(false);

    // Compute real severity counts from audit.findings (Zero fabricated numbers!)
    const severityCounts = useMemo(() => {
        const counts: Record<Severity, number> = {
            CRITICAL: 0,
            HIGH: 0,
            MEDIUM: 0,
            LOW: 0,
            INFO: 0,
        };
        audit.findings.forEach((f) => {
            counts[f.severity] = (counts[f.severity] || 0) + 1;
        });
        return counts;
    }, [audit.findings]);

    // Copy SHA-256 hash helper
    const handleCopyHash = () => {
        navigator.clipboard.writeText(audit.document_revision_hash);
        setCopiedHash(true);
        setTimeout(() => setCopiedHash(false), 1800);
    };

    // Export current audit payload as JSON
    const handleExportAuditRecord = () => {
        const blob = new Blob([JSON.stringify(audit, null, 2)], {
            type: 'application/json',
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${audit.audit_id}_governance_record.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="space-y-6">
            {/* Top Action Bar: Clear Entry Point to Submit New Content & Review Drafts */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#121215] border border-zinc-800/90 rounded-xl p-5">
                <div className="space-y-1">
                    <div className="flex items-center gap-2.5">
                        <span className="text-xs font-mono text-zinc-400">
                            Active Campaign: <strong className="text-zinc-200">{audit.campaign_id}</strong>
                        </span>
                        <span className="text-zinc-700">•</span>
                        <span className="text-xs font-mono text-zinc-400">
                            Blocks Audited: <strong className="text-zinc-200">{audit.blocks.length}</strong>
                        </span>
                    </div>
                    <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
                        Specialist Engine Telemetry & Pre-Publication Governance
                    </h2>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                    <button
                        type="button"
                        onClick={() => onNavigate('review')}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700/80 text-xs font-medium text-zinc-200 transition-colors cursor-pointer"
                    >
                        <span>Open Review Queue</span>
                        <ArrowUpRight className="w-3.5 h-3.5 text-zinc-400" />
                    </button>
                    <button
                        type="button"
                        onClick={() => onNavigate('editor')}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
                    >
                        <Plus className="w-4 h-4" />
                        <span>Submit / Edit Content</span>
                    </button>
                </div>
            </div>

            {/* SECTION 1: Specialist Engine Telemetry Cards (With Hover Lift & Action Prompt) */}
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-zinc-200 tracking-tight">
                        Specialist Engine Telemetry Cards
                    </h3>
                    <span className="text-[11px] font-mono text-zinc-500">
                        mandatory_policies_enforced: {String(audit.mandatory_policies_enforced)}
                    </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {audit.engine_executions.map((eng) => {
                        const isOk = eng.execution_state === 'OK';
                        const isWarn =
                            eng.execution_state === 'INSUFFICIENT_DATA' ||
                            eng.execution_state === 'ERROR';

                        return (
                            <div
                                key={eng.expert_engine}
                                onClick={() => onNavigate('findings')}
                                className="group bg-[#121215] border border-zinc-800/90 rounded-xl p-4 flex flex-col justify-between space-y-4 hover:border-emerald-500/50 hover:-translate-y-0.5 hover:bg-zinc-900/40 transition-all duration-150 cursor-pointer"
                            >
                                {/* Card Header */}
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        {ENGINE_ICONS[eng.expert_engine] || (
                                            <Shield className="w-4 h-4 text-zinc-400" />
                                        )}
                                        <span className="text-xs font-semibold text-zinc-200 group-hover:text-white transition-colors">
                                            {eng.expert_engine} —
                                        </span>
                                    </div>
                                    <MoreHorizontal className="w-4 h-4 text-zinc-600 group-hover:text-emerald-400 transition-colors" />
                                </div>

                                {/* Metric & Finding Breakdown */}
                                <div className="flex items-baseline gap-2.5">
                                    <span className="text-3xl font-bold font-mono text-zinc-100">
                                        {eng.findings_count}
                                    </span>
                                    <div className="text-[11px] font-mono leading-tight">
                                        <div className="text-zinc-400 uppercase">
                                            {eng.findings_count === 1 ? 'FINDING FLAGGED' : 'FINDINGS FLAGGED'}
                                        </div>
                                        <div
                                            className={
                                                eng.mandatory_enforced ? 'text-emerald-400/90' : 'text-zinc-500'
                                            }
                                        >
                                            {eng.mandatory_enforced ? '(MANDATORY POLICY)' : '(ADVISORY ENGINE)'}
                                        </div>
                                    </div>
                                </div>

                                {/* Execution Status & Notes */}
                                <div className="space-y-1">
                                    <div className="text-xs font-mono">
                                        <span className="text-zinc-400">Status: </span>
                                        <span
                                            className={
                                                isOk
                                                    ? 'text-emerald-400 font-semibold'
                                                    : isWarn
                                                        ? 'text-amber-400 font-semibold'
                                                        : 'text-zinc-400'
                                            }
                                        >
                                            {eng.execution_state}
                                        </span>
                                    </div>
                                    <p className="text-xs text-zinc-400 line-clamp-2 min-h-[2rem]">
                                        {eng.notes || 'Engine check completed.'}
                                    </p>
                                </div>

                                {/* Execution Health Indicator Bar + Hover Prompt */}
                                <div className="pt-2 border-t border-zinc-800/70 flex items-center justify-between text-[11px]">
                                    <span className="text-zinc-500 group-hover:hidden">Execution state</span>
                                    <span className="hidden group-hover:inline-flex items-center gap-1 text-emerald-400 font-mono text-[10px]">
                                        Click to inspect findings <ArrowUpRight className="w-3 h-3" />
                                    </span>
                                    <div className="flex items-center gap-1">
                                        {[1, 2, 3, 4, 5, 6].map((bar) => (
                                            <span
                                                key={bar}
                                                className={`w-2.5 h-1 rounded-full ${isOk
                                                        ? 'bg-emerald-500/70'
                                                        : isWarn
                                                            ? 'bg-amber-500/70'
                                                            : 'bg-zinc-700'
                                                    }`}
                                            />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* SECTION 2: Recent Findings by Severity Strip */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-xs font-medium text-zinc-300">
                    <Layers className="w-4 h-4 text-emerald-400" />
                    <span>Recent Findings by Severity (Audit {audit.audit_id})</span>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as Severity[]).map(
                        (sev) => (
                            <div
                                key={sev}
                                onClick={() => onNavigate('findings')}
                                className="flex items-center gap-2 px-3 py-1 rounded-lg bg-zinc-900/90 border border-zinc-800 hover:border-zinc-600 transition-colors cursor-pointer"
                            >
                                <SeverityBadge severity={sev} />
                                <span className="text-xs font-mono font-bold text-zinc-100">
                                    {severityCounts[sev]}
                                </span>
                            </div>
                        )
                    )}
                </div>
            </div>

            {/* SECTION 3: Bottom Split Grid — Audit Findings Table (Left) + Audit Record & HMAC Snapshot (Right) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left 8 Columns: Audit Findings Table */}
                <div className="lg:col-span-8 bg-[#121215] border border-zinc-800/90 rounded-xl overflow-hidden flex flex-col">
                    <div className="px-5 py-4 border-b border-zinc-800/80 flex items-center justify-between">
                        <div>
                            <h3 className="text-sm font-semibold text-zinc-100">
                                Audit Findings Table
                            </h3>
                            <p className="text-xs text-zinc-500 mt-0.5">
                                Hover and click any row to inspect PostgreSQL citations and surgical rewrites
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => onNavigate('findings')}
                            className="text-xs font-mono text-emerald-400 hover:text-emerald-300 cursor-pointer"
                        >
                            View All ({audit.findings.length}) →
                        </button>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-zinc-800/80 text-[10px] font-mono uppercase tracking-wider text-zinc-500 bg-zinc-900/40">
                                    <th className="py-3 px-4">Finding ID</th>
                                    <th className="py-3 px-3">Engine</th>
                                    <th className="py-3 px-3">Type</th>
                                    <th className="py-3 px-3">Severity</th>
                                    <th className="py-3 px-3">Status</th>
                                    <th className="py-3 px-4">Matched Text & Explanation</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-zinc-800/60 text-xs">
                                {audit.findings.map((finding) => (
                                    <tr
                                        key={finding.finding_id}
                                        onClick={() => onNavigate('findings')}
                                        className="group hover:bg-zinc-900/80 transition-colors cursor-pointer"
                                    >
                                        <td className="py-3.5 px-4 font-mono text-zinc-200 whitespace-nowrap group-hover:text-emerald-400 transition-colors">
                                            {finding.finding_id}
                                        </td>
                                        <td className="py-3.5 px-3 font-medium text-zinc-300 whitespace-nowrap">
                                            {finding.expert_engine}
                                        </td>
                                        <td className="py-3.5 px-3 font-mono text-[11px] text-zinc-400 whitespace-nowrap">
                                            {finding.finding_type}
                                        </td>
                                        <td className="py-3.5 px-3 whitespace-nowrap">
                                            <SeverityBadge severity={finding.severity} />
                                        </td>
                                        <td className="py-3.5 px-3 whitespace-nowrap">
                                            <VerificationBadge
                                                status={finding.verification_status}
                                                executionState={finding.execution_state}
                                            />
                                        </td>
                                        <td className="py-3.5 px-4 max-w-xs relative">
                                            <div className="flex items-center justify-between gap-2">
                                                <div className="font-semibold text-zinc-100 truncate">
                                                    {finding.matched_text || '[Document / Image Region]'}
                                                </div>
                                                {/* Hover Action Pill (Matches Preview Image!) */}
                                                <span className="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-0.5 rounded bg-emerald-950/90 border border-emerald-700/80 text-emerald-300 font-mono text-[10px] whitespace-nowrap shrink-0">
                                                    Inspect Diff & Citation →
                                                </span>
                                            </div>
                                            <div className="text-zinc-400 text-[11px] line-clamp-2 mt-0.5">
                                                {finding.explanation}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Right 4 Columns: Drafts Awaiting Review & HMAC Audit Record Panel */}
                <div className="lg:col-span-4 space-y-6">
                    {/* Card A: Drafts Awaiting Review */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-zinc-100">
                                Drafts Awaiting Review
                            </h3>
                            <Clock className="w-4 h-4 text-amber-400" />
                        </div>

                        <div className="p-3.5 rounded-lg bg-zinc-900/70 border border-zinc-800 space-y-2.5">
                            <div className="flex items-center justify-between gap-2">
                                <span className="font-mono text-xs font-semibold text-zinc-200">
                                    {audit.campaign_id}
                                </span>
                                <AuditStatusBadge status={audit.overall_status} />
                            </div>
                            <div className="text-xs text-zinc-400 space-y-1 font-mono">
                                <div>Audit ID: {audit.audit_id}</div>
                                <div>Submitted By: {audit.submitted_by_role}</div>
                                <div>
                                    Human Review Required: {String(audit.human_review_required)}
                                </div>
                            </div>
                            {isStale && (
                                <div className="text-[11px] text-amber-300 bg-amber-950/60 border border-amber-800/60 px-2.5 py-1 rounded">
                                    Draft edited since last audit — re-run audit before review.
                                </div>
                            )}
                            <div className="pt-1 flex gap-2">
                                <button
                                    type="button"
                                    onClick={() => onNavigate('review')}
                                    className="w-full py-1.5 px-3 rounded bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-zinc-100 transition-colors cursor-pointer"
                                >
                                    Inspect in Review Queue →
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Card B: Audit Record & HMAC Snapshot */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                        <h3 className="text-sm font-semibold text-zinc-100">
                            Audit Record & HMAC Snapshot
                        </h3>

                        <div className="space-y-2.5 text-xs">
                            <div className="flex justify-between gap-2">
                                <span className="text-zinc-500">Snapshot ID</span>
                                <span className="font-mono text-zinc-200">
                                    {audit.latest_snapshot?.snapshot_id || 'Awaiting Sign-Off'}
                                </span>
                            </div>
                            <div className="flex justify-between gap-2">
                                <span className="text-zinc-500">Created At UTC</span>
                                <span className="font-mono text-zinc-200">
                                    {new Date(audit.created_at_utc).toISOString().replace('T', ' ').slice(0, 19)}
                                </span>
                            </div>
                            <div className="flex items-center justify-between gap-2">
                                <span className="text-zinc-500">Document Hash</span>
                                <button
                                    type="button"
                                    onClick={handleCopyHash}
                                    title="Click to copy full SHA-256 revision hash"
                                    className="inline-flex items-center gap-1.5 font-mono text-zinc-300 hover:text-emerald-400 transition-colors cursor-pointer"
                                >
                                    <span className="truncate max-w-[140px]">
                                        {audit.document_revision_hash}
                                    </span>
                                    {copiedHash ? (
                                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                                    ) : (
                                        <Copy className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                                    )}
                                </button>
                            </div>
                            <div className="flex justify-between gap-2">
                                <span className="text-zinc-500">Metadata</span>
                                <span className="text-right text-zinc-300">
                                    Tenant isolated ({audit.org_id}) • {audit.engine_executions.length} specialist engines run
                                </span>
                            </div>
                        </div>

                        <div className="space-y-1.5 pt-1">
                            <span className="text-xs text-zinc-400 block">
                                Cryptographic Signature
                            </span>
                            <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 font-mono text-[11px] text-emerald-400/90 break-all leading-relaxed">
                                {audit.latest_snapshot ? (
                                    <>
                                        <div>
                                            snapshot_hmac_signature: "{audit.latest_snapshot.snapshot_hmac_signature}"
                                        </div>
                                        <div className="text-zinc-500">
                                            previous_snapshot_hmac: "{audit.latest_snapshot.previous_snapshot_hmac}"
                                        </div>
                                    </>
                                ) : (
                                    <div className="text-zinc-500">
                                        No approval snapshot signed yet. Complete Maker-Checker review to bind HMAC-SHA256 record.
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="space-y-2 pt-2">
                            <button
                                type="button"
                                onClick={() => onNavigate('records')}
                                className="w-full py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-200 flex items-center justify-center gap-2 transition-colors cursor-pointer"
                            >
                                <Lock className="w-3.5 h-3.5 text-zinc-400" />
                                <span>Inspect Snapshot Status</span>
                            </button>
                            <button
                                type="button"
                                onClick={handleExportAuditRecord}
                                className="w-full py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 flex items-center justify-center gap-2 transition-colors cursor-pointer"
                            >
                                <Download className="w-3.5 h-3.5 text-zinc-400" />
                                <span>Export Audit Record (JSON)</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};