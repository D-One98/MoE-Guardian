

import type {
    ApprovedFact,
    AuditCreateRequest,
    AuditResponse,
    BrandPaletteItem,
    BrandRule,
    ComplianceExportResponse,
    ContentBlock,
    CsvFactsUploadResponse,
    GuidelineConfirmRequest,
    GuidelineUploadPreviewResponse,
    OnDemandRewriteRequest,
    OnDemandRewriteResponse,
    ReviewDecisionRequest,
    SnapshotVerificationResponse,
} from '../types/contracts';

export const INITIAL_CONTENT_BLOCKS: ContentBlock[] = [
    {
        document_block_id: 'blk-paragraph-01',
        text: 'Introducing Inkloom.ai: Unmatched Enterprise Governance at Scale.',
    },
    {
        document_block_id: 'blk-paragraph-02',
        text: 'Experience uninterrupted productivity with 12 hours guaranteed battery on a single charge.',
    },
    {
        document_block_id: 'blk-paragraph-03',
        text: 'Built for distributed teams with #1 globally ranked neural compliance speed.',
    },
];

export const MOCK_BRAND_RULES: BrandRule[] = [
    {
        rule_id: 'RULE-TERM-01',
        category: 'BRAND_CASING',
        title: 'Official Brand Casing ("Inkloom AI")',
        description:
            'Always write "Inkloom AI" with a space and uppercase AI. Never write domain-style "Inkloom.ai" in narrative copy.',
        mandatory_flag: true,
        severity: 'MEDIUM',
        pattern_or_target: 'Inkloom.ai',
        expected_replacement: 'Inkloom AI',
        document_id: 'DOC-BRAND-2026-V1',
        document_name: 'Brand_Guidelines_2026.pdf',
        verified_page_or_row: 2,
        version: '1.0',
        campaign_scope: 'GLOBAL',
    },
    {
        rule_id: 'RULE-BAN-02',
        category: 'BANNED_TERM',
        title: 'Prohibited Unqualified Superlatives & Guarantees',
        description:
            'Banned phrases include "guaranteed", "100% guaranteed", and unverified "#1 globally ranked" superlatives.',
        mandatory_flag: true,
        severity: 'CRITICAL',
        pattern_or_target: 'guaranteed',
        expected_replacement: null,
        document_id: 'DOC-BRAND-2026-V1',
        document_name: 'Brand_Guidelines_2026.pdf',
        verified_page_or_row: 3,
        version: '1.0',
        campaign_scope: 'GLOBAL',
    },
    {
        rule_id: 'RULE-DISC-03',
        category: 'MANDATORY_DISCLAIMER',
        title: 'Laboratory Battery Testing Condition',
        description:
            'Any mention of battery life metrics must state "up to" and "under specified laboratory testing conditions".',
        mandatory_flag: true,
        severity: 'HIGH',
        pattern_or_target: 'under specified laboratory testing conditions',
        expected_replacement: 'up to 12 hours under specified laboratory testing conditions',
        document_id: 'DOC-SPEC-2026-V2',
        document_name: 'Product_Specifications_v2.pdf',
        verified_page_or_row: 4,
        version: '1.0',
        campaign_scope: 'GLOBAL',
    },
];

export const MOCK_APPROVED_FACTS: ApprovedFact[] = [
    {
        fact_id: 'FACT-BAT-02',
        topic_key: 'battery_life',
        subject_keywords: ['battery', 'hours', 'charge'],
        canonical_text:
            'Up to 12 hours under specified laboratory testing conditions.',
        approved_numeric_value: 12,
        numeric_unit: 'hours',
        comparator: 'up_to',
        required_conditions: ['up to', 'under specified laboratory testing conditions'],
        prohibited_overstatements: ['guaranteed', 'minimum 12 hours', 'unlimited'],
        document_id: 'DOC-SPEC-2026-V2',
        document_name: 'Product_Specifications_v2.pdf',
        verified_page_or_row: 4,
        version: '1.0',
    },
    {
        fact_id: 'FACT-LAT-05',
        topic_key: 'audit_latency',
        subject_keywords: ['latency', 'response', 'speed'],
        canonical_text:
            'Evaluates configured deterministic rules and RAG claims across multi-block drafts.',
        approved_numeric_value: 4,
        numeric_unit: 'engines',
        comparator: 'exact',
        required_conditions: ['configured rules', 'approved facts vault'],
        prohibited_overstatements: ['#1 globally ranked', 'zero-latency'],
        document_id: 'DOC-BRAND-2026-V1',
        document_name: 'Brand_Guidelines_2026.pdf',
        verified_page_or_row: 6,
        version: '1.0',
    },
];

export const MOCK_BRAND_PALETTE: BrandPaletteItem[] = [
    {
        palette_id: 'PAL-01',
        name: 'Carbon Zinc 950',
        hex: '#09090B',
        max_delta_e: 4.0,
        document_name: 'Brand_Guidelines_2026.pdf',
        verified_page_or_row: 8,
        version: '1.0',
    },
    {
        palette_id: 'PAL-02',
        name: 'Elevated Surface',
        hex: '#121215',
        max_delta_e: 4.0,
        document_name: 'Brand_Guidelines_2026.pdf',
        verified_page_or_row: 8,
        version: '1.0',
    },
    {
        palette_id: 'PAL-03',
        name: 'Verity Emerald',
        hex: '#10B981',
        max_delta_e: 5.0,
        document_name: 'Brand_Guidelines_2026.pdf',
        verified_page_or_row: 9,
        version: '1.0',
    },
    {
        palette_id: 'PAL-04',
        name: 'Escalation Amber',
        hex: '#F59E0B',
        max_delta_e: 5.0,
        document_name: 'Brand_Guidelines_2026.pdf',
        verified_page_or_row: 9,
        version: '1.0',
    },
];

export const INITIAL_MOCK_AUDIT_RESPONSE: AuditResponse = {
    audit_id: 'AUD-2026-0042',
    org_id: 'ORG-SAMPLE-DEMO-01',
    campaign_id: 'CAMP-LAUNCH-2026',
    submitted_by_role: 'CREATOR',
    document_revision_hash:
        'sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    overall_status: 'ESCALATED_TO_AUTHORISED_REVIEWER',
    human_review_required: true,
    mandatory_policies_enforced: true,
    blocks: INITIAL_CONTENT_BLOCKS,
    engine_executions: [
        {
            expert_engine: 'RuleGuard',
            mandatory_enforced: true,
            execution_state: 'OK',
            findings_count: 1,
            notes: 'Deterministic regex and terminology bounds evaluated.',
        },
        {
            expert_engine: 'ClaimGuard',
            mandatory_enforced: true,
            execution_state: 'OK',
            findings_count: 2,
            notes: 'Evaluated factual claims against Approved Facts Vault.',
        },
        {
            expert_engine: 'VisualGuard',
            mandatory_enforced: true,
            execution_state: 'INSUFFICIENT_DATA',
            findings_count: 1,
            notes: 'Complex background gradient detected; escalated for human check.',
        },
        {
            expert_engine: 'VoiceGuard',
            mandatory_enforced: false,
            execution_state: 'OK',
            findings_count: 0,
            notes: 'On-demand surgical rewrite candidates generated and revalidated.',
        },
    ],
    findings: [
        {
            finding_id: 'FND-2026-01',
            expert_engine: 'RuleGuard',
            execution_state: 'OK',
            finding_type: 'DETERMINISTIC_VIOLATION',
            severity: 'MEDIUM',
            verification_status: 'NOT_CLAIM_APPLICABLE',
            document_block_id: 'blk-paragraph-01',
            matched_text: 'Inkloom.ai',
            prefix_context: 'Introducing ',
            suffix_context: ': Unmatched Enterprise',
            anchor_resolution_status: 'RESOLVED_UNIQUE',
            explanation:
                'Violates official brand casing rule. Always write "Inkloom AI" with a space and uppercase AI.',
            evidence_reference: {
                source_type: 'BRAND_RULE',
                reference_id: 'RULE-TERM-01',
                document_id: 'DOC-BRAND-2026-V1',
                document_name: 'Brand_Guidelines_2026.pdf',
                verified_page_or_row: 2,
                canonical_excerpt_from_db:
                    'Official brand name is "Inkloom AI". Do not use domain-style "Inkloom.ai" in prose.',
            },
            rewrite_candidate: {
                candidate_id: 'RW-01',
                suggested_text: 'Introducing Inkloom AI: Enterprise Governance at Scale.',
                backend_revalidation: {
                    assigned_by: 'BACKEND_COORDINATOR',
                    executed_checks: {
                        RuleGuard_execution_state: 'OK',
                        RuleGuard_violations_count: 0,
                        VoiceGuard_recursive_call: 'SKIPPED_BY_DESIGN',
                    },
                    candidate_verification_status: 'NOT_CLAIM_APPLICABLE',
                    revalidation_passed: true,
                },
            },
            human_review_required: false,
        },
        {
            finding_id: 'FND-2026-02',
            expert_engine: 'ClaimGuard',
            execution_state: 'OK',
            finding_type: 'FACTUAL_CLAIM',
            severity: 'HIGH',
            verification_status: 'PARTIAL',
            document_block_id: 'blk-paragraph-02',
            matched_text: '12 hours guaranteed battery',
            prefix_context: 'Experience uninterrupted productivity with ',
            suffix_context: ' on a single charge.',
            anchor_resolution_status: 'RESOLVED_UNIQUE',
            explanation:
                'The core numeric value (12 hours) aligns with FACT-BAT-02, but the required condition ("up to" under "specified laboratory testing conditions") is omitted and replaced with an unsupported "guaranteed" claim.',
            evidence_reference: {
                source_type: 'APPROVED_FACT',
                reference_id: 'FACT-BAT-02',
                document_id: 'DOC-SPEC-2026-V2',
                document_name: 'Product_Specifications_v2.pdf',
                verified_page_or_row: 4,
                canonical_excerpt_from_db:
                    'Up to 12 hours under specified laboratory testing conditions.',
            },
            rewrite_candidate: {
                candidate_id: 'RW-02',
                suggested_text:
                    'Experience uninterrupted productivity with up to 12 hours of battery life under specified laboratory testing conditions on a single charge.',
                backend_revalidation: {
                    assigned_by: 'BACKEND_COORDINATOR',
                    executed_checks: {
                        RuleGuard_execution_state: 'OK',
                        RuleGuard_violations_count: 0,
                        ClaimGuard_execution_state: 'OK',
                        VoiceGuard_recursive_call: 'SKIPPED_BY_DESIGN',
                    },
                    candidate_verification_status: 'SUPPORTED',
                    revalidation_passed: true,
                },
            },
            human_review_required: true,
        },
        {
            finding_id: 'FND-2026-03',
            expert_engine: 'ClaimGuard',
            execution_state: 'OK',
            finding_type: 'FACTUAL_CLAIM',
            severity: 'CRITICAL',
            verification_status: 'UNVERIFIABLE',
            document_block_id: 'blk-paragraph-03',
            matched_text: '#1 globally ranked neural compliance speed',
            prefix_context: 'Built for distributed teams with ',
            suffix_context: '.',
            anchor_resolution_status: 'RESOLVED_UNIQUE',
            explanation:
                'No supporting record exists in the Approved Facts Vault for "#1 globally ranked". Unverifiable superlative claims require removal or Authorised Reviewer sign-off.',
            evidence_reference: null,
            rewrite_candidate: null,
            human_review_required: true,
        },
        {
            finding_id: 'FND-2026-04',
            expert_engine: 'VisualGuard',
            execution_state: 'INSUFFICIENT_DATA',
            finding_type: 'VISUAL_A11Y_SUBSET',
            severity: 'LOW',
            verification_status: 'NOT_CLAIM_APPLICABLE',
            document_block_id: null,
            matched_text: null,
            prefix_context: null,
            suffix_context: null,
            anchor_resolution_status: 'UNRESOLVED_SIDEBAR_ONLY',
            explanation:
                'Foreground/background luminance contrast over non-uniform image gradient returned INSUFFICIENT_DATA. Requires human visual inspection.',
            evidence_reference: null,
            rewrite_candidate: null,
            human_review_required: true,
        },
    ],
    ai_disclosure_log: {
        adapter_mode: 'FALLBACK_MOCK_ADAPTER',
        mandatory_router_enforced: true,
        specialist_engines_invoked: ['RuleGuard', 'ClaimGuard', 'VisualGuard', 'VoiceGuard'],
    },
    latest_snapshot: null,
    created_at_utc: '2026-11-08T00:30:00Z',
};

export function createMockAudit(req: AuditCreateRequest, hash: string): AuditResponse {
    return {
        ...INITIAL_MOCK_AUDIT_RESPONSE,
        audit_id: `AUD-2026-${Math.floor(1000 + Math.random() * 9000)}`,
        campaign_id: req.campaign_id || 'CAMP-LAUNCH-2026',
        submitted_by_role: req.submitted_by_role || 'CREATOR',
        document_revision_hash: hash,
        blocks: req.blocks,
        created_at_utc: new Date().toISOString(),
    };
}

export function submitMockReviewDecision(
    currentAudit: AuditResponse,
    req: ReviewDecisionRequest
): AuditResponse {
    const newStatus = req.decision === 'APPROVE' ? 'APPROVED' : 'CHANGES_REQUESTED';
    return {
        ...currentAudit,
        overall_status: newStatus,
        latest_snapshot: {
            snapshot_id: `SNAP-2026-${Math.floor(1000 + Math.random() * 9000)}`,
            audit_id: currentAudit.audit_id,
            org_id: currentAudit.org_id,
            campaign_id: currentAudit.campaign_id,
            content_sha256_hash: currentAudit.document_revision_hash,
            brand_constitution_version: '1.0',
            facts_vault_version: '1.0',
            rule_engine_version: '1.0',
            router_config_version: '1.0',
            retrieved_evidence_ids: ['RULE-TERM-01', 'FACT-BAT-02'],
            audit_output_sha256_hash: 'sha256:mock-audit-output-digest-pending-backend',
            approval_state: newStatus,
            approver_role: req.actor_role,
            review_notes: req.override_justification || null,
            approved_at_utc: new Date().toISOString(),
            hmac_key_id: 'mock-key-unverified',
            previous_snapshot_hmac: 'GENESIS_SNAPSHOT',
            snapshot_hmac_signature: 'MOCK_SIGNATURE_NOT_CRYPTOGRAPHICALLY_VERIFIED',
        },
    };
}

export function generateMockOnDemandRewrite(
    audit: AuditResponse,
    findingId: string,
    req: OnDemandRewriteRequest
): OnDemandRewriteResponse {
    const finding = audit.findings.find((f) => f.finding_id === findingId);
    const customText =
        req.custom_candidate_text?.trim() ||
        'Experience uninterrupted productivity with up to 12 hours of battery life under specified laboratory testing conditions.';
    const hasBannedGuaranteed = customText.toLowerCase().includes('guaranteed');

    const candidate = {
        candidate_id: `RW-${Math.floor(100 + Math.random() * 900)}`,
        suggested_text: customText,
        backend_revalidation: {
            assigned_by: 'BACKEND_COORDINATOR',
            executed_checks: {
                RuleGuard_execution_state: 'OK',
                RuleGuard_violations_count: hasBannedGuaranteed ? 1 : 0,
                ClaimGuard_execution_state: 'OK',
                VoiceGuard_recursive_call: 'SKIPPED_BY_DESIGN',
            },
            candidate_verification_status: hasBannedGuaranteed
                ? ('PARTIAL' as const)
                : ('SUPPORTED' as const),
            revalidation_passed: !hasBannedGuaranteed,
        },
    };

    return {
        audit_id: audit.audit_id,
        org_id: audit.org_id,
        finding_id: findingId,
        original_matched_text: finding?.matched_text || '',
        original_finding_type: finding?.finding_type || 'FACTUAL_CLAIM',
        original_verification_status: finding?.verification_status || 'PARTIAL',
        rewrite_candidates: [candidate],
        selected_primary_candidate: candidate.backend_revalidation.revalidation_passed
            ? candidate
            : null,
    };
}

export function verifyMockSnapshot(audit: AuditResponse): SnapshotVerificationResponse {
    if (!audit.latest_snapshot) {
        return {
            audit_id: audit.audit_id,
            org_id: audit.org_id,
            snapshot_id: null,
            hmac_key_id: null,
            is_valid: false,
            status_code: 'NO_SNAPSHOT_FOUND',
            chain_integrity_verified: false,
            message: 'No review snapshot exists for this audit yet.',
        };
    }
    return {
        audit_id: audit.audit_id,
        org_id: audit.org_id,
        snapshot_id: audit.latest_snapshot.snapshot_id,
        hmac_key_id: audit.latest_snapshot.hmac_key_id,
        is_valid: false,
        status_code: 'INVALID_SIGNATURE',
        chain_integrity_verified: false,
        message:
            'Mock Adapter Notice: Cryptographic HMAC-SHA256 verification requires live FastAPI backend secret key.',
    };
}

export function buildMockComplianceExport(
    audit: AuditResponse
): ComplianceExportResponse {
    const verification = verifyMockSnapshot(audit);
    const readyForCms =
        audit.overall_status === 'APPROVED' && verification.is_valid;

    return {
        export_version: '1.0',
        generated_at_utc: new Date().toISOString(),
        audit_id: audit.audit_id,
        org_id: audit.org_id,
        campaign_id: audit.campaign_id,
        created_at_utc: audit.created_at_utc,
        submitted_by_role: audit.submitted_by_role,
        document_revision_hash: audit.document_revision_hash,
        overall_status: audit.overall_status,
        human_review_required: audit.human_review_required,
        mandatory_policies_enforced: audit.mandatory_policies_enforced,
        machine_governance_summary: {
            total_findings: audit.findings.length,
            engines_run: audit.engine_executions.length,
        },
        engine_executions: audit.engine_executions,
        machine_findings: audit.findings,
        human_review_decision: audit.latest_snapshot
            ? {
                approval_state: audit.latest_snapshot.approval_state,
                approver_role: audit.latest_snapshot.approver_role,
                approved_at_utc: audit.latest_snapshot.approved_at_utc,
            }
            : null,
        snapshot_integrity: verification,
        ai_disclosure_log: audit.ai_disclosure_log,
        simulated_cms_payload: {
            cms_export_mode: 'SIMULATED_PRE_PUBLICATION_PAYLOAD',
            external_cms_published: false,
            export_ready_for_cms: readyForCms,
            approval_status: audit.overall_status,
            audit_reference_id: audit.audit_id,
            document_revision_hash: audit.document_revision_hash,
            snapshot_id: audit.latest_snapshot?.snapshot_id || null,
            snapshot_hmac_signature:
                audit.latest_snapshot?.snapshot_hmac_signature || null,
            // Section 14.1 CMS Approval Safeguard: Only populate approved_blocks when APPROVED & is_valid
            approved_blocks: readyForCms ? audit.blocks : [],
            approved_alt_text: null,
            notice: readyForCms
                ? 'Approved and verified for simulated CMS payload.'
                : 'CMS blocks withheld: Requires APPROVED status and VALID snapshot signature.',
        },
    };
}

export function buildMockPdfPreview(fileName: string): GuidelineUploadPreviewResponse {
    return {
        batch_id: `BATCH-${Math.floor(1000 + Math.random() * 9000)}`,
        org_id: 'ORG-SAMPLE-DEMO-01',
        document_id: 'DOC-PDF-PREVIEW',
        document_name: fileName,
        status: 'PENDING_CONFIRMATION',
        page_count: 1,
        extraction_status: 'OK',
        prompt_shield_isolated: true,
        pages: [
            {
                page_number: 1,
                char_count: 132,
                extracted_text:
                    'Extracted preview (Mock Mode): Never use "guaranteed" in marketing copy. Always write brand name as Inkloom AI.',
                prompt_injection_signals_detected: false,
            },
        ],
        candidate_rules: [
            {
                rule_id: `RULE-PDF-${Math.floor(100 + Math.random() * 900)}`,
                category: 'BANNED_TERM',
                title: 'Extracted Banned Term: "guaranteed"',
                description: 'Never use "guaranteed" in marketing copy.',
                mandatory_flag: true,
                severity: 'HIGH',
                pattern_or_target: 'guaranteed',
                expected_replacement: null,
                document_id: 'DOC-PDF-PREVIEW',
                document_name: fileName,
                verified_page_or_row: 1,
                version: '1.1',
                campaign_scope: 'GLOBAL',
            },
        ],
        warnings: [],
    };
}

export function buildMockCsvUploadResponse(fileName: string): CsvFactsUploadResponse {
    return {
        org_id: 'ORG-SAMPLE-DEMO-01',
        document_name: fileName,
        total_rows_processed: 2,
        saved_facts_count: 1,
        saved_facts: [MOCK_APPROVED_FACTS[0]],
        row_errors: [
            {
                row_number: 2,
                fact_id: 'FACT-ERR-99',
                error_code: 'INVALID_NUMERIC_VALUE',
                message: 'Sample row error demonstration: approved_numeric_value must be numeric.',
            },
        ],
    };
}

export function confirmMockGuidelines(req: GuidelineConfirmRequest): BrandRule[] {
    return [...MOCK_BRAND_RULES, ...req.confirmed_rules];
}