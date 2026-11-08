import React, { useState } from 'react';
import type {
    AuditResponse,
    ComplianceExportResponse,
    SnapshotVerificationResponse,
} from '../../types/contracts';
import type { NavRoute } from '../layout/Sidebar';
import {
    exportAuditComplianceService,
    verifySnapshotService,
} from '../../services/auditService';
import { AuditStatusBadge } from '../ui/Badge';
import {
    FileCheck2,
    Download,
    ShieldCheck,
    ShieldAlert,
    Lock,
    Cpu,
    ArrowLeft,
    CheckCircle2,
} from 'lucide-react';

interface AuditRecordsViewProps {
    audit: AuditResponse;
    isMockMode: boolean;
    onNavigate: (route: NavRoute) => void;
}

export const AuditRecordsView: React.FC<AuditRecordsViewProps> = ({
    audit,
    onNavigate,
}) => {
    const snap = audit.latest_snapshot;
    const [verificationResult, setVerificationResult] =
        useState<SnapshotVerificationResponse | null>(null);
    const [exportData, setExportData] =
        useState<ComplianceExportResponse | null>(null);
    const [isVerifying, setIsVerifying] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    // Section 13.1: Call GET /api/audits/{audit_id}/verify-snapshot
    const handleVerifySnapshot = async () => {
        setIsVerifying(true);
        try {
            const res = await verifySnapshotService(audit);
            setVerificationResult(res);
        } finally {
            setIsVerifying(false);
        }
    };

    // Section 14.1: Call GET /api/audits/{audit_id}/export
    const handleExportRecord = async () => {
        setIsExporting(true);
        try {
            const exported = await exportAuditComplianceService(audit);
            setExportData(exported);
            const blob = new Blob([JSON.stringify(exported, null, 2)], {
                type: 'application/json',
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${audit.audit_id}_compliance_export.json`;
            a.click();
            URL.revokeObjectURL(url);
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Top Header Card */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
                        <span>Tamper-Evident Audit Record</span>
                        <span>•</span>
                        <span>
                            Audit ID: <strong className="text-zinc-100">{audit.audit_id}</strong>
                        </span>
                    </div>
                    <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
                        Audit Snapshot Verification, Simulated CMS Export & AI Disclosure Log
                    </h2>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <button
                        type="button"
                        onClick={() => onNavigate('review')}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 cursor-pointer"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" />
                        <span>Back to Review Queue</span>
                    </button>

                    <button
                        type="button"
                        onClick={handleVerifySnapshot}
                        disabled={isVerifying}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-xs font-semibold text-emerald-300 cursor-pointer"
                    >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>
                            {isVerifying ? 'Verifying HMAC...' : 'Verify Snapshot Integrity'}
                        </span>
                    </button>

                    <button
                        type="button"
                        onClick={handleExportRecord}
                        disabled={isExporting}
                        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white cursor-pointer"
                    >
                        <Download className="w-3.5 h-3.5" />
                        <span>
                            {isExporting ? 'Exporting...' : 'Compliance & CMS Export'}
                        </span>
                    </button>
                </div>
            </div>

            {/* Live SnapshotVerificationResponse Banner (Section 13) */}
            {verificationResult && (
                <div
                    className={`p-4 rounded-xl border flex items-start gap-3 text-xs ${verificationResult.is_valid
                            ? 'bg-emerald-950/40 border-emerald-800/70 text-emerald-200'
                            : 'bg-amber-950/40 border-amber-800/70 text-amber-200'
                        }`}
                >
                    {verificationResult.is_valid ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    ) : (
                        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-1 font-mono">
                        <div className="font-semibold">
                            status_code: {verificationResult.status_code} • is_valid:{' '}
                            {String(verificationResult.is_valid)} • chain_integrity_verified:{' '}
                            {String(verificationResult.chain_integrity_verified)}
                        </div>
                        <p className="font-sans text-zinc-200">{verificationResult.message}</p>
                    </div>
                </div>
            )}

            {/* Simulated CMS Payload Preview (Section 14.1) */}
            {exportData && (
                <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5 space-y-3">
                    <div className="flex items-center justify-between text-xs font-mono">
                        <span className="font-semibold text-emerald-400">
                            Simulated CMS Export Payload ({exportData.simulated_cms_payload.cms_export_mode})
                        </span>
                        <span>
                            export_ready_for_cms:{' '}
                            <strong>
                                {String(exportData.simulated_cms_payload.export_ready_for_cms)}
                            </strong>
                        </span>
                    </div>
                    <p className="text-xs text-zinc-300">
                        {exportData.simulated_cms_payload.notice}
                    </p>
                    <div className="text-[11px] font-mono text-zinc-400">
                        Populated approved_blocks count:{' '}
                        {exportData.simulated_cms_payload.approved_blocks.length}
                    </div>
                </div>
            )}

            {/* Snapshot Record Card */}
            {!snap ? (
                <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-10 text-center space-y-3">
                    <Lock className="w-8 h-8 text-zinc-600 mx-auto" />
                    <div className="text-sm font-semibold text-zinc-200">
                        No Approval or Rejection Snapshot Recorded Yet
                    </div>
                    <p className="text-xs text-zinc-500 max-w-md mx-auto">
                        This draft is currently in{' '}
                        <code className="font-mono text-zinc-300">{audit.overall_status}</code>{' '}
                        state. Complete a review decision in the Review Queue to generate an
                        AuditSnapshotRecord.
                    </p>
                </div>
            ) : (
                <div className="bg-[#121215] border border-zinc-800/90 rounded-xl overflow-hidden">
                    <div className="px-5 py-4 bg-zinc-900/60 border-b border-zinc-800/80 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2.5">
                            <FileCheck2 className="w-4 h-4 text-emerald-400" />
                            <span className="font-mono text-xs font-bold text-zinc-100">
                                Snapshot ID: {snap.snapshot_id}
                            </span>
                            <span className="text-zinc-600">•</span>
                            <span className="font-mono text-xs text-zinc-400">
                                Audit ID: {snap.audit_id}
                            </span>
                        </div>
                        <AuditStatusBadge status={snap.approval_state} />
                    </div>

                    <div className="p-5 space-y-5">
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                            <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800/90 space-y-1">
                                <span className="text-zinc-500 block">Approval State</span>
                                <span className="font-mono font-semibold text-zinc-100">
                                    {snap.approval_state}
                                </span>
                            </div>
                            <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800/90 space-y-1">
                                <span className="text-zinc-500 block">Approver Role</span>
                                <span className="font-mono font-semibold text-emerald-400">
                                    {snap.approver_role}
                                </span>
                            </div>
                            <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800/90 space-y-1">
                                <span className="text-zinc-500 block">Timestamp (UTC)</span>
                                <span className="font-mono text-zinc-200">
                                    {snap.approved_at_utc}
                                </span>
                            </div>
                            <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800/90 space-y-1">
                                <span className="text-zinc-500 block">HMAC Key ID</span>
                                <span className="font-mono text-zinc-200">
                                    {snap.hmac_key_id}
                                </span>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                            <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800/90 space-y-1.5">
                                <div className="text-zinc-500 text-[10px] uppercase">
                                    Cryptographic Digests & Chaining
                                </div>
                                <div className="truncate text-zinc-300">
                                    content_sha256_hash: {snap.content_sha256_hash}
                                </div>
                                <div className="truncate text-zinc-400">
                                    audit_output_sha256_hash: {snap.audit_output_sha256_hash}
                                </div>
                                <div className="truncate text-zinc-400">
                                    previous_snapshot_hmac: {snap.previous_snapshot_hmac}
                                </div>
                                <div className="truncate text-emerald-400">
                                    snapshot_hmac_signature: {snap.snapshot_hmac_signature}
                                </div>
                            </div>

                            <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800/90 space-y-1.5">
                                <div className="text-zinc-500 text-[10px] uppercase">
                                    Bound Policy & Engine Versions
                                </div>
                                <div className="text-zinc-300">
                                    brand_constitution_version: {snap.brand_constitution_version}
                                </div>
                                <div className="text-zinc-300">
                                    facts_vault_version: {snap.facts_vault_version}
                                </div>
                                <div className="text-zinc-400">
                                    rule_engine_version: {snap.rule_engine_version} • router:{' '}
                                    {snap.router_config_version}
                                </div>
                                <div className="text-zinc-400">
                                    retrieved_evidence_ids: [
                                    {snap.retrieved_evidence_ids.join(', ')}]
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* AI Disclosure Log Inspector */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
                    <Cpu className="w-4 h-4 text-emerald-400" />
                    <span>
                        Per-Audit AI & Engine Disclosure Log (
                        <code className="font-mono">ai_disclosure_log</code>)
                    </span>
                </div>
                <pre className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300 overflow-x-auto">
                    {JSON.stringify(audit.ai_disclosure_log, null, 2)}
                </pre>
            </div>
        </div>
    );
};