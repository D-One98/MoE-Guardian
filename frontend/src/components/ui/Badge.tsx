import React from 'react';
import type {
    AuditStatus,
    ExecutionState,
    Severity,
    VerificationStatus,
} from '../../types/contracts';
import { AlertTriangle, CheckCircle2, HelpCircle, Info, XCircle } from 'lucide-react';

export const SeverityBadge: React.FC<{ severity: Severity }> = ({ severity }) => {
    const styles: Record<Severity, string> = {
        CRITICAL: 'bg-red-950/70 text-red-400 border-red-800/60',
        HIGH: 'bg-amber-950/70 text-amber-400 border-amber-800/60',
        MEDIUM: 'bg-yellow-950/60 text-yellow-300 border-yellow-800/50',
        LOW: 'bg-zinc-800/80 text-zinc-300 border-zinc-700',
        INFO: 'bg-sky-950/70 text-sky-400 border-sky-800/60',
    };

    return (
        <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${styles[severity]}`}
        >
            {severity}
        </span>
    );
};

export const VerificationBadge: React.FC<{
    status: VerificationStatus;
    executionState: ExecutionState;
}> = ({ status, executionState }) => {
    // Section 4E Mandate: Never display an item as compliant if execution_state is ERROR or INSUFFICIENT_DATA
    if (executionState === 'ERROR' || executionState === 'INSUFFICIENT_DATA') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-purple-950/70 text-purple-300 border border-purple-800/60">
                <AlertTriangle className="w-3 h-3 text-purple-400 shrink-0" />
                {executionState}
            </span>
        );
    }

    const map: Record<VerificationStatus, { cls: string; icon: React.ReactNode }> = {
        SUPPORTED: {
            cls: 'bg-emerald-950/70 text-emerald-400 border-emerald-800/60',
            icon: <CheckCircle2 className="w-3 h-3" />,
        },
        PARTIAL: {
            cls: 'bg-amber-950/70 text-amber-300 border-amber-800/60',
            icon: <AlertTriangle className="w-3 h-3" />,
        },
        CONTRADICTED: {
            cls: 'bg-red-950/70 text-red-400 border-red-800/60',
            icon: <XCircle className="w-3 h-3" />,
        },
        UNVERIFIABLE: {
            cls: 'bg-rose-950/70 text-rose-400 border-rose-800/60',
            icon: <HelpCircle className="w-3 h-3" />,
        },
        NOT_CLAIM_APPLICABLE: {
            cls: 'bg-zinc-800/80 text-zinc-400 border-zinc-700/80',
            icon: <Info className="w-3 h-3" />,
        },
    };

    const item = map[status];
    return (
        <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${item.cls}`}
        >
            {item.icon}
            {status}
        </span>
    );
};

export const AuditStatusBadge: React.FC<{ status: AuditStatus }> = ({ status }) => {
    const styles: Record<AuditStatus, string> = {
        PENDING_REVIEW: 'bg-zinc-800 text-zinc-300 border-zinc-700',
        READY_FOR_MANAGER_APPROVAL: 'bg-sky-950/70 text-sky-400 border-sky-800/60',
        ESCALATED_TO_AUTHORISED_REVIEWER: 'bg-amber-950/70 text-amber-400 border-amber-800/60',
        APPROVED: 'bg-emerald-950/70 text-emerald-400 border-emerald-800/60',
        CHANGES_REQUESTED: 'bg-red-950/70 text-red-400 border-red-800/60',
    };

    return (
        <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold border ${styles[status]}`}
        >
            {status}
        </span>
    );
};