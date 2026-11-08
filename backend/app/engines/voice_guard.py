import re
from typing import List, Tuple, Optional, Dict, Any
from app.schemas.contracts import (
    ApprovedFact,
    BrandRule,
    ContentBlock,
    EngineExecutionRecord,
    EvidenceReference,
    ExecutionState,
    FindingType,
    RewriteCandidate,
    RuleCategory,
    Severity,
    UnifiedFinding,
    VerificationStatus,
)
from app.services.anchoring import resolve_block_text_anchor
from app.services.rewrite_coordinator import validate_rewrite_candidate

# Baseline Brand Voice & Tone Alignment Patterns (Deterministic Linguistic Rules)
DEFAULT_TONE_PATTERNS: List[Dict[str, Any]] = [
    {
        "rule_id": "RULE-VOICE-001",
        "title": "Prohibit coercive urgency or fear-based phrasing",
        "description": "Brand voice must remain confident and professional; avoid coercive urgency such as 'buy now or regret' or 'last chance forever'.",
        "pattern": re.compile(r"\b(?:buy\s+now\s+or\s+regret|last\s+chance\s+forever|act\s+now\s+before\s+it's\s+too\s+late)\b", re.IGNORECASE),
        "replacement": "explore our latest release at your convenience",
        "severity": Severity.MEDIUM,
    },
    {
        "rule_id": "RULE-VOICE-002",
        "title": "Prohibit aggressive competitor disparagement",
        "description": "Never use hostile or disparaging language toward competitors (e.g., 'crush the competition', 'competitors are garbage', 'destroy the market').",
        "pattern": re.compile(r"\b(?:crush\s+the\s+competition|competitors\s+are\s+(?:garbage|trash|useless)|destroy\s+the\s+competition)\b", re.IGNORECASE),
        "replacement": "deliver reliable engineering performance",
        "severity": Severity.HIGH,
    },
    {
        "rule_id": "RULE-VOICE-003",
        "title": "Avoid excessive exclamation hype punctuation",
        "description": "Maintain a measured, trustworthy tone; avoid multiple consecutive exclamation marks ('!!' or '!!!').",
        "pattern": re.compile(r"!{2,}"),
        "replacement": ".",
        "severity": Severity.LOW,
    },
    {
        "rule_id": "RULE-VOICE-004",
        "title": "Avoid informal hype slang in enterprise communications",
        "description": "Prefer clear professional phrasing over informal hype slang ('insane deal', 'mind-blowing', 'crazy cheap').",
        "pattern": re.compile(r"\b(?:insane\s+deal|mind-blowing|crazy\s+cheap)\b", re.IGNORECASE),
        "replacement": "high-value offering",
        "severity": Severity.LOW,
    },
]

# Telemetry counter used by tests to verify VoiceGuard is never invoked recursively
VOICE_GUARD_INVOCATION_LOG: List[str] = []


def _build_voice_evidence(rule_id: str, description: str) -> EvidenceReference:
    return EvidenceReference(
        source_type="BRAND_VOICE_CONSTITUTION",
        reference_id=rule_id,
        document_id="DOC-BRAND-CONSTITUTION-V1",
        document_name="Sample_Brand_Guidelines_v1.pdf",
        verified_page_or_row=3,
        canonical_excerpt_from_db=description,
    )


def run_voice_guard_baseline(
    blocks: List[ContentBlock],
    rules: Optional[List[BrandRule]] = None,
) -> Tuple[List[UnifiedFinding], EngineExecutionRecord]:
    """
    Analyses tone and messaging alignment across content blocks.
    Does NOT automatically rewrite or overwrite creator content during audit execution;
    rewrites are generated strictly on demand via generate_on_demand_rewrite_candidates().
    """
    VOICE_GUARD_INVOCATION_LOG.append("run_voice_guard_baseline")
    findings: List[UnifiedFinding] = []
    finding_counter = 1

    try:
        for block in blocks:
            text = block.text
            for tone_rule in DEFAULT_TONE_PATTERNS:
                for match in tone_rule["pattern"].finditer(text):
                    matched_str = match.group(0)
                    prefix, suffix, anchor_status = resolve_block_text_anchor(
                        text, matched_str, occ_start=match.start()
                    )
                    findings.append(
                        UnifiedFinding(
                            finding_id=f"FND-VG-TONE-{finding_counter:04d}",
                            expert_engine="VoiceGuard",
                            execution_state=ExecutionState.OK,
                            finding_type=FindingType.TONE_MESSAGING,
                            severity=tone_rule["severity"],
                            verification_status=VerificationStatus.NOT_CLAIM_APPLICABLE,
                            document_block_id=block.document_block_id,
                            matched_text=matched_str,
                            prefix_context=prefix,
                            suffix_context=suffix,
                            anchor_resolution_status=anchor_status,
                            explanation=(
                                f"Tone/messaging misalignment ('{matched_str}'): {tone_rule['description']}"
                            ),
                            evidence_reference=_build_voice_evidence(
                                tone_rule["rule_id"], tone_rule["description"]
                            ),
                            # Do not auto-generate rewrites unless explicitly requested on demand
                            rewrite_candidate=None,
                            human_review_required=tone_rule["severity"] in (Severity.HIGH, Severity.CRITICAL),
                        )
                    )
                    finding_counter += 1

        return findings, EngineExecutionRecord(
            expert_engine="VoiceGuard",
            mandatory_enforced=True,
            execution_state=ExecutionState.OK,
            findings_count=len(findings),
            notes="Deterministic tone and messaging alignment analysis completed (on-demand rewrites deferred until requested).",
        )
    except Exception as exc:
        return [], EngineExecutionRecord(
            expert_engine="VoiceGuard",
            mandatory_enforced=False,
            execution_state=ExecutionState.ERROR,
            findings_count=0,
            notes=f"VoiceGuard execution error: {type(exc).__name__}",
        )


def _synthesise_intent_preserving_text(
    block_text: str,
    finding: UnifiedFinding,
    rules: List[BrandRule],
    facts: List[ApprovedFact],
) -> str:
    """
    Produces an intent-preserving surgical rewrite of the flagged span/block
    while preserving factual qualifiers and applying deterministic rule/tone repairs.
    """
    revised = block_text

    # 1. If the finding is a factual claim linked to an approved fact, preserve canonical qualifiers
    if finding.finding_type == FindingType.FACTUAL_CLAIM and finding.evidence_reference is not None:
        ref_id = finding.evidence_reference.reference_id
        matched_fact = next((f for f in facts if f.fact_id == ref_id), None)
        if matched_fact is not None and finding.matched_text and finding.matched_text in revised:
            revised = revised.replace(finding.matched_text, matched_fact.canonical_text, 1)
        elif matched_fact is not None:
            revised = matched_fact.canonical_text

    # 2. Apply surgical repairs for active brand rules (casing, banned terms, disclaimers)
    for rule in rules:
        if rule.category == RuleCategory.BRAND_CASING:
            pattern = re.compile(r"\b" + re.escape(rule.pattern_or_target) + r"\b", re.IGNORECASE)
            revised = pattern.sub(rule.expected_replacement or rule.pattern_or_target, revised)
        elif rule.category == RuleCategory.BANNED_TERM:
            pattern = re.compile(re.escape(rule.pattern_or_target), re.IGNORECASE)
            replacement = rule.expected_replacement if rule.expected_replacement else ""
            revised = pattern.sub(replacement, revised)
            revised = re.sub(r"\s{2,}", " ", revised).strip()

    # 3. Apply tone repairs
    for tone_rule in DEFAULT_TONE_PATTERNS:
        revised = tone_rule["pattern"].sub(tone_rule["replacement"], revised)

    # Clean up punctuation spacing
    revised = re.sub(r"\s+([.,!?])", r"\1", revised)
    revised = re.sub(r"\s{2,}", " ", revised).strip()
    return revised


def generate_on_demand_rewrite_candidates(
    block_text: str,
    finding: UnifiedFinding,
    rules: List[BrandRule],
    facts: List[ApprovedFact],
    custom_candidate_text: Optional[str] = None,
) -> List[RewriteCandidate]:
    """
    Generates intent-preserving rewrite candidates ONLY when explicitly requested on demand,
    and validates each candidate through the fail-closed Rewrite Validation Coordinator.
    Does NOT recursively invoke VoiceGuard on the generated candidates.
    """
    VOICE_GUARD_INVOCATION_LOG.append("generate_on_demand_rewrite_candidates")
    candidates_raw: List[str] = []

    if custom_candidate_text is not None and custom_candidate_text.strip():
        candidates_raw.append(custom_candidate_text.strip())
    else:
        synthesised = _synthesise_intent_preserving_text(
            block_text=block_text,
            finding=finding,
            rules=rules,
            facts=facts,
        )
        candidates_raw.append(synthesised)

    validated_candidates: List[RewriteCandidate] = []
    for idx, cand_text in enumerate(candidates_raw, start=1):
        cand_id = f"RW-OD-{finding.finding_id}-{idx:02d}"
        validated = validate_rewrite_candidate(
            candidate_id=cand_id,
            suggested_text=cand_text,
            rules=rules,
            facts=facts,
            original_finding_type=finding.finding_type,
            original_matched_text=finding.matched_text,
        )
        validated_candidates.append(validated)

    return validated_candidates