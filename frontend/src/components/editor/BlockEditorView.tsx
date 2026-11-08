import React from 'react';
import type {
    ContentBlock,
    DemoRole,
    UnifiedFinding,
} from '../../types/contracts';
import type { NavRoute } from '../layout/Sidebar';
import { SeverityBadge, VerificationBadge } from '../ui/Badge';
import {
    Play,
    Plus,
    Trash2,
    AlertTriangle,
    CheckCircle2,
    FileCode2,
    Image,
    Sparkles,
    RotateCcw,
    ArrowUpRight,
} from 'lucide-react';

interface BlockEditorViewProps {
    campaignId: string;
    onChangeCampaignId: (val: string) => void;
    blocks: ContentBlock[];
    onUpdateBlockText: (blockId: string, newText: string) => void;
    onAddBlock: () => void;
    onRemoveBlock: (blockId: string) => void;
    onResetDefaultBlocks: () => void;
    altText: string;
    onChangeAltText: (val: string) => void;
    currentRole: DemoRole;
    currentRevisionHash: string;
    lastAuditedHash: string;
    isStale: boolean;
    isLoadingAudit: boolean;
    findings: UnifiedFinding[];
    onRunAudit: () => void;
    onNavigate: (route: NavRoute) => void;
}

export const BlockEditorView: React.FC<BlockEditorViewProps> = ({
    campaignId,
    onChangeCampaignId,
    blocks,
    onUpdateBlockText,
    onAddBlock,
    onRemoveBlock,
    onResetDefaultBlocks,
    altText,
    onChangeAltText,
    currentRole,
    currentRevisionHash,
    lastAuditedHash,
    isStale,
    isLoadingAudit,
    findings,
    onRunAudit,
    onNavigate,
}) => {
    return (
        <div className="space-y-6">
            {/* STALE FINDINGS GUARD BANNER (Section 4D Mandatory Requirement) */}
            {isStale && (
                <div className="bg-amber-950/50 border border-amber-800/80 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                            <div className="text-xs font-semibold text-amber-200 uppercase tracking-wide font-mono">
                                Stale Findings Invalidated (Document Modified After Audit)
                            </div>
                            <p className="text-xs text-amber-300/90 leading-relaxed">
                                Editor revision (<code className="font-mono">{currentRevisionHash.slice(0, 18)}...</code>)
                                no longer matches the audited revision (<code className="font-mono">{lastAuditedHash.slice(0, 18)}...</code>).
                                Previous inline findings are suppressed until you re-run the audit.
                            </p>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={onRunAudit}
                        disabled={isLoadingAudit}
                        className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 text-xs font-semibold font-mono shrink-0 transition-colors cursor-pointer"
                    >
                        Re-Run Audit Now
                    </button>
                </div>
            )}

            {/* Top Editor Action Bar */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
                        <span>Canonical Block Editor</span>
                        <span>•</span>
                        <span>Submitted By Role: <strong className="text-emerald-400">{currentRole}</strong></span>
                    </div>
                    <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
                        Pre-Publication Draft Authoring & Block Anchoring
                    </h2>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <button
                        type="button"
                        onClick={onResetDefaultBlocks}
                        title="Reset to sample launch draft"
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-medium text-zinc-300 transition-colors cursor-pointer"
                    >
                        <RotateCcw className="w-3.5 h-3.5 text-zinc-400" />
                        <span>Reset Sample</span>
                    </button>

                    <button
                        type="button"
                        onClick={onRunAudit}
                        disabled={isLoadingAudit || blocks.length === 0}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-xs font-semibold text-white shadow-xs transition-colors cursor-pointer"
                    >
                        <Play className="w-3.5 h-3.5 fill-current" />
                        <span>{isLoadingAudit ? 'Running VERITY MoE...' : 'Run VERITY MoE Audit'}</span>
                    </button>
                </div>
            </div>

            {/* Main 12-Column Split Workspace */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left 8 Columns: Canonical ContentBlock[] List */}
                <div className="lg:col-span-8 space-y-4">
                    {blocks.map((block, index) => {
                        // Only attach findings if the audit is NOT stale
                        const blockFindings = isStale
                            ? []
                            : findings.filter((f) => f.document_block_id === block.document_block_id);

                        const hasFindings = blockFindings.length > 0;

                        return (
                            <div
                                key={block.document_block_id}
                                className={`bg-[#121215] rounded-xl border transition-colors overflow-hidden ${hasFindings
                                        ? 'border-amber-700/70'
                                        : 'border-zinc-800/90 hover:border-zinc-700/80'
                                    }`}
                            >
                                {/* Block Header Bar — Shows Immutable document_block_id */}
                                <div className="px-4 py-2.5 bg-zinc-900/70 border-b border-zinc-800/80 flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-2.5">
                                        <span className="px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 font-mono text-[11px] font-semibold border border-zinc-700">
                                            {block.document_block_id}
                                        </span>
                                        <span className="text-[11px] font-mono text-zinc-500">
                                            Block #{index + 1} • {block.text.length} chars
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        {!isStale && hasFindings && (
                                            <button
                                                type="button"
                                                onClick={() => onNavigate('findings')}
                                                className="inline-flex items-center gap-1 text-[11px] font-mono text-amber-400 hover:underline cursor-pointer"
                                            >
                                                <span>{blockFindings.length} finding(s) anchored</span>
                                                <ArrowUpRight className="w-3 h-3" />
                                            </button>
                                        )}

                                        {!isStale && !hasFindings && (
                                            <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400/90">
                                                <CheckCircle2 className="w-3 h-3" />
                                                CLEAN
                                            </span>
                                        )}

                                        {blocks.length > 1 && (
                                            <button
                                                type="button"
                                                onClick={() => onRemoveBlock(block.document_block_id)}
                                                title="Remove block"
                                                className="p-1 rounded text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-colors cursor-pointer"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Block Textarea Input */}
                                <div className="p-4 space-y-3">
                                    <textarea
                                        value={block.text}
                                        onChange={(e) =>
                                            onUpdateBlockText(block.document_block_id, e.target.value)
                                        }
                                        rows={3}
                                        placeholder="Enter promotional copy, product claims, or disclaimers for this block..."
                                        className="w-full bg-zinc-950/70 border border-zinc-800 rounded-lg p-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500/70 leading-relaxed resize-y"
                                    />

                                    {/* Inline Preview of Active Findings Anchored to This Block (Hidden when stale) */}
                                    {!isStale && blockFindings.length > 0 && (
                                        <div className="space-y-2 pt-1">
                                            {blockFindings.map((f) => (
                                                <div
                                                    key={f.finding_id}
                                                    className="p-3 rounded-lg bg-zinc-950/90 border border-zinc-800/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                                                >
                                                    <div className="space-y-1">
                                                        <div className="flex flex-wrap items-center gap-2">
                                                            <span className="font-mono font-semibold text-zinc-300">
                                                                {f.finding_id}
                                                            </span>
                                                            <span className="font-mono text-[11px] text-zinc-400">
                                                                [{f.expert_engine}]
                                                            </span>
                                                            <SeverityBadge severity={f.severity} />
                                                            <VerificationBadge
                                                                status={f.verification_status}
                                                                executionState={f.execution_state}
                                                            />
                                                            <span className="font-mono text-[10px] text-zinc-500">
                                                                anchor: {f.anchor_resolution_status}
                                                            </span>
                                                        </div>
                                                        {f.matched_text && (
                                                            <div className="text-zinc-400">
                                                                Matched span:{' '}
                                                                <code className="px-1.5 py-0.5 rounded bg-red-950/60 text-red-300 border border-red-800/50 font-mono">
                                                                    "{f.matched_text}"
                                                                </code>
                                                            </div>
                                                        )}
                                                    </div>

                                                    <button
                                                        type="button"
                                                        onClick={() => onNavigate('findings')}
                                                        className="px-3 py-1.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium text-xs shrink-0 transition-colors cursor-pointer"
                                                    >
                                                        Inspect / Rewrite →
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}

                    {/* Add New Block Button */}
                    <button
                        type="button"
                        onClick={onAddBlock}
                        className="w-full py-3 rounded-xl border border-dashed border-zinc-800 hover:border-zinc-700 bg-[#121215]/60 hover:bg-[#121215] text-xs font-medium text-zinc-400 hover:text-zinc-200 flex items-center justify-center gap-2 transition-colors cursor-pointer"
                    >
                        <Plus className="w-4 h-4 text-emerald-400" />
                        <span>Add Canonical Content Block (Preserves Stable Block IDs)</span>
                    </button>
                </div>

                {/* Right 4 Columns: AuditCreateRequest Metadata & Contract Inspector */}
                <div className="lg:col-span-4 space-y-6">
                    {/* Card 1: Campaign & Alt-Text Metadata (AuditCreateRequest fields) */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                        <div className="flex items-center gap-2">
                            <Image className="w-4 h-4 text-emerald-400" />
                            <h3 className="text-sm font-semibold text-zinc-100">
                                Submission Metadata
                            </h3>
                        </div>

                        <div className="space-y-3 text-xs">
                            <div>
                                <label className="block text-zinc-400 font-medium mb-1">
                                    Campaign ID (<code className="font-mono">campaign_id</code>)
                                </label>
                                <input
                                    type="text"
                                    value={campaignId}
                                    onChange={(e) => onChangeCampaignId(e.target.value)}
                                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-emerald-500/70"
                                    placeholder="e.g., camp-q4-launch"
                                />
                            </div>

                            <div>
                                <label className="block text-zinc-400 font-medium mb-1">
                                    Static Image Alt-Text (<code className="font-mono">alt_text</code>)
                                </label>
                                <textarea
                                    value={altText}
                                    onChange={(e) => onChangeAltText(e.target.value)}
                                    rows={3}
                                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-xs text-zinc-100 focus:outline-none focus:border-emerald-500/70"
                                    placeholder="Optional alt_text metadata validated by VisualGuard..."
                                />
                                <p className="text-[11px] text-zinc-500 mt-1">
                                    Checked by <code className="font-mono text-zinc-400">VisualGuard</code> for presence and non-empty accessibility description.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Card 2: Canonical Revision & Block ID Contract Preview */}
                    <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <FileCode2 className="w-4 h-4 text-sky-400" />
                                <h3 className="text-sm font-semibold text-zinc-100">
                                    Block ID & Revision State
                                </h3>
                            </div>
                            <span
                                className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${isStale
                                        ? 'bg-amber-950/70 text-amber-300 border-amber-800/70'
                                        : 'bg-emerald-950/70 text-emerald-400 border-emerald-800/70'
                                    }`}
                            >
                                {isStale ? 'STALE_REVISION' : 'IN_SYNC'}
                            </span>
                        </div>

                        <div className="space-y-2 text-xs font-mono">
                            <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800/80 space-y-1">
                                <div className="text-[10px] text-zinc-500 uppercase">
                                    Live Editor Revision Hash
                                </div>
                                <div className="text-zinc-200 truncate">{currentRevisionHash}</div>
                            </div>
                            <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800/80 space-y-1">
                                <div className="text-[10px] text-zinc-500 uppercase">
                                    Last Audited Revision Hash
                                </div>
                                <div className="text-zinc-400 truncate">{lastAuditedHash}</div>
                            </div>
                        </div>

                        <div className="space-y-1.5 pt-1">
                            <div className="text-[11px] font-medium text-zinc-400">
                                Active Canonical Blocks ({blocks.length}):
                            </div>
                            <div className="max-h-40 overflow-y-auto space-y-1 pr-1">
                                {blocks.map((b) => (
                                    <div
                                        key={b.document_block_id}
                                        className="px-2.5 py-1.5 rounded bg-zinc-900/80 border border-zinc-800/80 flex items-center justify-between text-[11px] font-mono"
                                    >
                                        <span className="text-zinc-300">{b.document_block_id}</span>
                                        <span className="text-zinc-500">{b.text.length} chars</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/70 flex items-start gap-2 text-[11px] text-zinc-400">
                            <Sparkles className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            <span>
                                Block IDs remain immutable across text edits so backend findings anchor deterministically to the intended paragraph.
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};