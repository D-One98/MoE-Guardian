import React, { useEffect, useState } from 'react';
import type {
    ApprovedFact,
    BrandPaletteItem,
    BrandRule,
    CsvFactsUploadResponse,
    GuidelineUploadPreviewResponse,
} from '../../types/contracts';
import {
    confirmGuidelineRulesService,
    listApprovedFactsService,
    listBrandPaletteService,
    listBrandRulesService,
    uploadApprovedFactsCsvService,
    uploadGuidelinePdfService,
} from '../../services/auditService';
import { SeverityBadge } from '../ui/Badge';
import {
    BookOpen,
    ShieldCheck,
    Database,
    Palette,
    Upload,
    CheckCircle2,
    AlertTriangle,
    FileUp,
} from 'lucide-react';

export const BrandConstitutionView: React.FC = () => {
    const [rules, setRules] = useState<BrandRule[]>([]);
    const [facts, setFacts] = useState<ApprovedFact[]>([]);
    const [palette, setPalette] = useState<BrandPaletteItem[]>([]);
    const [statusMessage, setStatusMessage] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    // PDF Guideline Ingestion Preview State (Section 7 of API_CONTRACT.md)
    const [pdfPreview, setPdfPreview] =
        useState<GuidelineUploadPreviewResponse | null>(null);
    const [isUploadingPdf, setIsUploadingPdf] = useState(false);

    // CSV Approved Facts Ingestion Result State (Section 8 of API_CONTRACT.md)
    const [csvResult, setCsvResult] = useState<CsvFactsUploadResponse | null>(
        null
    );
    const [isUploadingCsv, setIsUploadingCsv] = useState(false);

    useEffect(() => {
        void loadConstitutionData();
    }, []);

    const loadConstitutionData = async () => {
        try {
            const [r, f, p] = await Promise.all([
                listBrandRulesService(),
                listApprovedFactsService(),
                listBrandPaletteService(),
            ]);
            setRules(r);
            setFacts(f);
            setPalette(p);
        } catch (err) {
            setErrorMessage(
                err instanceof Error ? err.message : 'Failed to load brand constitution'
            );
        }
    };

    // Handle PDF Upload -> Staged Preview (Do NOT auto-activate until confirmed!)
    const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setIsUploadingPdf(true);
        setErrorMessage(null);
        setStatusMessage(null);
        try {
            const preview = await uploadGuidelinePdfService(file);
            setPdfPreview(preview);
            setStatusMessage(
                `PDF parsed (${preview.page_count} page(s)). Batch ${preview.batch_id} is in ${preview.status} state — review and confirm candidate rules below.`
            );
        } catch (err) {
            setErrorMessage(err instanceof Error ? err.message : 'PDF upload failed');
        } finally {
            setIsUploadingPdf(false);
        }
    };

    // Confirm Staged Guideline Rules (POST /api/brand/guidelines/{batch_id}/confirm)
    const handleConfirmPdfRules = async () => {
        if (!pdfPreview) return;
        setErrorMessage(null);
        try {
            await confirmGuidelineRulesService(pdfPreview.batch_id, {
                brand_constitution_version: '1.1',
                confirmed_rules: pdfPreview.candidate_rules,
            });
            setRules((prev) => [...prev, ...pdfPreview.candidate_rules]);
            setStatusMessage(
                `Confirmed and activated ${pdfPreview.candidate_rules.length} rule(s) from batch ${pdfPreview.batch_id}.`
            );
            setPdfPreview(null);
        } catch (err) {
            setErrorMessage(
                err instanceof Error ? err.message : 'Failed to confirm guideline rules'
            );
        }
    };

    // Handle Approved Facts CSV Upload (POST /api/brand/facts/upload-csv)
    const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setIsUploadingCsv(true);
        setErrorMessage(null);
        setStatusMessage(null);
        try {
            const res = await uploadApprovedFactsCsvService(file);
            setCsvResult(res);
            if (res.saved_facts.length > 0) {
                setFacts((prev) => [...prev, ...res.saved_facts]);
            }
            if (res.row_errors.length > 0) {
                setStatusMessage(
                    `CSV processed with partial row errors: ${res.saved_facts_count} saved, ${res.row_errors.length} failed.`
                );
            } else {
                setStatusMessage(
                    `CSV upload complete: ${res.saved_facts_count} approved fact(s) saved.`
                );
            }
        } catch (err) {
            setErrorMessage(err instanceof Error ? err.message : 'CSV upload failed');
        } finally {
            setIsUploadingCsv(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header & Knowledge Ingestion Upload Controls */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs font-mono text-emerald-400">
                        <BookOpen className="w-4 h-4" />
                        <span>Brand Constitution & Knowledge Ingestion</span>
                    </div>
                    <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
                        Approved Rules, Facts Vault, PDF Guideline Parser & CSV Ingestion
                    </h2>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                    <label className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-xs font-medium text-zinc-200 cursor-pointer transition-colors">
                        <FileUp className="w-3.5 h-3.5 text-emerald-400" />
                        <span>
                            {isUploadingPdf ? 'Parsing PDF...' : 'Upload Guideline PDF'}
                        </span>
                        <input
                            type="file"
                            accept=".pdf,application/pdf"
                            onChange={handlePdfUpload}
                            className="hidden"
                        />
                    </label>

                    <label className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white cursor-pointer transition-colors">
                        <Upload className="w-3.5 h-3.5" />
                        <span>
                            {isUploadingCsv ? 'Uploading CSV...' : 'Upload Approved Facts CSV'}
                        </span>
                        <input
                            type="file"
                            accept=".csv,text/csv"
                            onChange={handleCsvUpload}
                            className="hidden"
                        />
                    </label>
                </div>
            </div>

            {statusMessage && (
                <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/70 text-xs text-emerald-200 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{statusMessage}</span>
                </div>
            )}

            {errorMessage && (
                <div className="p-3.5 rounded-xl bg-red-950/50 border border-red-800/70 text-xs text-red-200 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                    <span>{errorMessage}</span>
                </div>
            )}

            {/* Section 7: Pending PDF Guideline Confirmation Preview */}
            {pdfPreview && (
                <div className="bg-[#121215] border border-amber-700/80 rounded-xl p-5 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 pb-3">
                        <div>
                            <div className="flex items-center gap-2 text-xs font-mono text-amber-300">
                                <span>Batch: {pdfPreview.batch_id}</span>
                                <span>•</span>
                                <span className="px-2 py-0.5 rounded bg-amber-950 border border-amber-700">
                                    {pdfPreview.status}
                                </span>
                                <span>•</span>
                                <span>
                                    prompt_shield_isolated: {String(pdfPreview.prompt_shield_isolated)}
                                </span>
                            </div>
                            <h3 className="text-sm font-semibold text-zinc-100 mt-1">
                                Staged PDF Guideline Preview: {pdfPreview.document_name} (
                                {pdfPreview.page_count} page(s))
                            </h3>
                        </div>

                        <button
                            type="button"
                            onClick={handleConfirmPdfRules}
                            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white cursor-pointer"
                        >
                            Confirm & Activate Candidate Rules ({pdfPreview.candidate_rules.length})
                        </button>
                    </div>

                    <div className="space-y-2">
                        <div className="text-xs font-mono text-zinc-400">
                            Extracted Page Preview:
                        </div>
                        {pdfPreview.pages.map((p) => (
                            <div
                                key={p.page_number}
                                className="p-3 rounded bg-zinc-950 border border-zinc-800 text-xs font-mono text-zinc-300"
                            >
                                <div className="text-[10px] text-zinc-500 mb-1">
                                    Page {p.page_number} ({p.char_count} chars) • injection_detected:{' '}
                                    {String(p.prompt_injection_signals_detected)}
                                </div>
                                {p.extracted_text}
                            </div>
                        ))}
                    </div>

                    <div className="space-y-2">
                        <div className="text-xs font-mono text-zinc-400">
                            Candidate Rules Awaiting Confirmation:
                        </div>
                        {pdfPreview.candidate_rules.map((cr) => (
                            <div
                                key={cr.rule_id}
                                className="p-3 rounded bg-zinc-900 border border-zinc-800 flex items-center justify-between text-xs"
                            >
                                <div>
                                    <span className="font-mono font-bold text-emerald-400">
                                        {cr.rule_id}
                                    </span>{' '}
                                    • <strong className="text-zinc-100">{cr.title}</strong> —{' '}
                                    <span className="text-zinc-400">{cr.description}</span>
                                </div>
                                <SeverityBadge severity={cr.severity} />
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Section 8: CSV Upload Summary & Row-Level Validation Errors */}
            {csvResult && (
                <div className="bg-[#121215] border border-zinc-800 rounded-xl p-5 space-y-3">
                    <div className="flex items-center justify-between text-xs font-mono">
                        <span className="text-zinc-200 font-semibold">
                            CSV Upload Report: {csvResult.document_name}
                        </span>
                        <span className="text-zinc-400">
                            Processed: {csvResult.total_rows_processed} | Saved:{' '}
                            <strong className="text-emerald-400">
                                {csvResult.saved_facts_count}
                            </strong>{' '}
                            | Errors:{' '}
                            <strong className="text-amber-400">
                                {csvResult.row_errors.length}
                            </strong>
                        </span>
                    </div>
                    {csvResult.row_errors.length > 0 && (
                        <div className="space-y-1.5">
                            {csvResult.row_errors.map((err, i) => (
                                <div
                                    key={i}
                                    className="p-2.5 rounded bg-red-950/40 border border-red-800/70 text-xs font-mono text-red-200"
                                >
                                    Row {err.row_number} ({err.fact_id || 'N/A'}) [{err.error_code}]:{' '}
                                    {err.message}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* 1. Active Brand Rules (BrandRule[]) */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl overflow-hidden">
                <div className="px-5 py-3.5 bg-zinc-900/60 border-b border-zinc-800/80 flex items-center gap-2 text-xs font-semibold text-zinc-200">
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                    <span>Active Brand Constitution Rules ({rules.length})</span>
                </div>
                <div className="divide-y divide-zinc-800/70">
                    {rules.map((rule) => (
                        <div
                            key={rule.rule_id}
                            className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                        >
                            <div className="space-y-1">
                                <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                                    <span className="font-bold text-zinc-100">{rule.rule_id}</span>
                                    <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-[10px]">
                                        {rule.category}
                                    </span>
                                    {rule.mandatory_flag && (
                                        <span className="px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800/70 text-emerald-300 text-[10px]">
                                            mandatory_flag: true
                                        </span>
                                    )}
                                    <span className="text-zinc-500 text-[11px]">
                                        target: "{rule.pattern_or_target}"
                                    </span>
                                </div>
                                <div className="text-sm font-semibold text-zinc-200">
                                    {rule.title}
                                </div>
                                <p className="text-xs text-zinc-400">{rule.description}</p>
                            </div>
                            <SeverityBadge severity={rule.severity} />
                        </div>
                    ))}
                </div>
            </div>

            {/* 2. Approved Facts Vault (ApprovedFact[]) */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl overflow-hidden">
                <div className="px-5 py-3.5 bg-zinc-900/60 border-b border-zinc-800/80 flex items-center gap-2 text-xs font-semibold text-zinc-200">
                    <Database className="w-4 h-4 text-amber-400" />
                    <span>Approved Facts Vault ({facts.length})</span>
                </div>
                <div className="divide-y divide-zinc-800/70">
                    {facts.map((fact) => (
                        <div key={fact.fact_id} className="p-4 space-y-2">
                            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                                <div className="flex items-center gap-2">
                                    <span className="font-bold text-emerald-400">{fact.fact_id}</span>
                                    <span className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 text-[10px]">
                                        topic: {fact.topic_key} ({fact.comparator || 'exact'}{' '}
                                        {fact.approved_numeric_value} {fact.numeric_unit})
                                    </span>
                                </div>
                                {fact.document_name && (
                                    <span className="text-zinc-400">
                                        Source: <strong className="text-zinc-200">{fact.document_name}</strong>{' '}
                                        (Page/Row {fact.verified_page_or_row})
                                    </span>
                                )}
                            </div>
                            <blockquote className="p-3 rounded bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 font-mono">
                                "{fact.canonical_text}"
                            </blockquote>
                            {fact.required_conditions && fact.required_conditions.length > 0 && (
                                <div className="text-xs text-amber-300/90 font-mono">
                                    Required Conditions: {fact.required_conditions.join(' • ')}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* 3. Approved Brand Colour Palette (BrandPaletteItem[]) */}
            <div className="bg-[#121215] border border-zinc-800/90 rounded-xl p-5 space-y-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
                    <Palette className="w-4 h-4 text-sky-400" />
                    <span>Approved Brand Hex Palette ({palette.length})</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {palette.map((swatch) => (
                        <div
                            key={swatch.palette_id}
                            className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2"
                        >
                            <div
                                className="h-12 rounded-md border border-zinc-700"
                                style={{ backgroundColor: swatch.hex }}
                            />
                            <div className="text-xs font-semibold text-zinc-100">
                                {swatch.name}
                            </div>
                            <div className="flex items-center justify-between text-xs font-mono">
                                <span className="text-emerald-400">{swatch.hex}</span>
                                {swatch.max_delta_e !== undefined && (
                                    <span className="text-zinc-500">max ΔE: {swatch.max_delta_e}</span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};