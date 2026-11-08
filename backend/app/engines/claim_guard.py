import re
from typing import List, Tuple, Optional
from app.schemas.contracts import (
    ApprovedFact,
    BrandRule,
    ContentBlock,
    UnifiedFinding,
    ExecutionState,
    FindingType,
    VerificationStatus,
    Severity,
    EvidenceReference,
    EngineExecutionRecord,
    RewriteCandidate,
)
from app.services.anchoring import resolve_block_text_anchor
from app.services.rewrite_coordinator import validate_rewrite_candidate


def _build_fact_evidence(fact: ApprovedFact) -> EvidenceReference:
    return EvidenceReference(
        source_type="APPROVED_FACT",
        reference_id=fact.fact_id,
        document_id=fact.document_id,
        document_name=fact.document_name,
        verified_page_or_row=fact.verified_page_or_row,
        canonical_excerpt_from_db=fact.canonical_text,
    )


def _split_sentences_with_offsets(text: str) -> List[Tuple[str, int]]:
    results: List[Tuple[str, int]] = []
    for match in re.finditer(r"[^.!?]+[.!?]?", text):
        seg = match.group(0).strip()
        if seg:
            idx = text.find(seg, match.start())
            results.append((seg, idx))
    return results


def _looks_like_factual_or_promotional_assertion(sentence: str) -> bool:
    s_lower = sentence.lower()
    if re.search(r"\b\d+(?:\.\d+)?\b", s_lower):
        return True
    claim_triggers = [
        "certified",
        "guaranteed",
        "proven",
        "tested to",
        "survive",
        "waterproof",
        "fastest",
        "battery life",
    ]
    return any(trigger in s_lower for trigger in claim_triggers)


def _match_fact_for_sentence(sentence: str, facts: List[ApprovedFact]) -> Optional[ApprovedFact]:
    s_lower = sentence.lower()
    for fact in facts:
        if any(kw.lower() in s_lower for kw in fact.subject_keywords):
            return fact
    return None


def _evaluate_sentence_against_fact(
    sentence: str,
    fact: ApprovedFact,
) -> Tuple[VerificationStatus, Severity, str]:
    s_lower = sentence.lower()

    unit_pattern = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:-|\s)*" + re.escape(fact.numeric_unit), re.IGNORECASE)
    unit_match = unit_pattern.search(sentence)
    if unit_match:
        claimed_val = float(unit_match.group(1))
    else:
        num_match = re.search(r"\b(\d+(?:\.\d+)?)\b", sentence)
        claimed_val = float(num_match.group(1)) if num_match else None

    if claimed_val is None:
        return (
            VerificationStatus.UNVERIFIABLE,
            Severity.HIGH,
            f"Claim mentions {fact.topic_key} keywords but lacks a verifiable specification matching {fact.fact_id}.",
        )

    if fact.comparator == "up_to" and claimed_val > fact.approved_numeric_value:
        return (
            VerificationStatus.CONTRADICTED,
            Severity.CRITICAL,
            (
                f"Submitted claim value ({claimed_val:g} {fact.numeric_unit}) exceeds the maximum approved "
                f"specification ({fact.approved_numeric_value:g} {fact.numeric_unit}) in {fact.fact_id}."
            ),
        )

    missing_conditions = [
        cond for cond in fact.required_conditions if cond.lower() not in s_lower
    ]
    used_overstatements = [
        over for over in fact.prohibited_overstatements if over.lower() in s_lower
    ]

    if missing_conditions or used_overstatements:
        reasons = []
        if missing_conditions:
            reasons.append(f"omits required condition(s): {missing_conditions}")
        if used_overstatements:
            reasons.append(f"uses unsupported overstatement(s): {used_overstatements}")
        reason_str = " and ".join(reasons)
        return (
            VerificationStatus.PARTIAL,
            Severity.HIGH,
            f"Numeric value ({claimed_val:g} {fact.numeric_unit}) aligns with {fact.fact_id}, but the claim {reason_str}.",
        )

    return (
        VerificationStatus.SUPPORTED,
        Severity.INFO,
        f"Claim aligns with approved specification {fact.fact_id} including required conditions.",
    )


def build_revalidated_rewrite_candidate(
    candidate_id: str,
    suggested_text: str,
    fact: ApprovedFact,
    rules: List[BrandRule],
    facts: List[ApprovedFact],
) -> RewriteCandidate:
    return validate_rewrite_candidate(
        candidate_id=candidate_id,
        suggested_text=suggested_text,
        rules=rules,
        facts=facts,
        original_finding_type=FindingType.FACTUAL_CLAIM,
        original_matched_text=fact.canonical_text,
    )


def run_claim_guard_baseline(
    blocks: List[ContentBlock],
    facts: List[ApprovedFact],
    rules: List[BrandRule],
    generate_rewrites: bool = True,
) -> Tuple[List[UnifiedFinding], EngineExecutionRecord]:
    findings: List[UnifiedFinding] = []
    finding_counter = 1

    try:
        for block in blocks:
            sentences = _split_sentences_with_offsets(block.text)
            for sentence, occ_start in sentences:
                if not _looks_like_factual_or_promotional_assertion(sentence):
                    continue

                matched_fact = _match_fact_for_sentence(sentence, facts)
                prefix, suffix, anchor_status = resolve_block_text_anchor(
                    block.text, sentence, occ_start=occ_start
                )

                if matched_fact is None:
                    findings.append(
                        UnifiedFinding(
                            finding_id=f"FND-CG-{finding_counter:04d}",
                            expert_engine="ClaimGuard",
                            execution_state=ExecutionState.OK,
                            finding_type=FindingType.FACTUAL_CLAIM,
                            severity=Severity.HIGH,
                            verification_status=VerificationStatus.UNVERIFIABLE,
                            document_block_id=block.document_block_id,
                            matched_text=sentence,
                            prefix_context=prefix,
                            suffix_context=suffix,
                            anchor_resolution_status=anchor_status,
                            explanation=(
                                "Factual or promotional assertion detected, but no backing specification "
                                "exists in the Approved Facts Vault. Escalated for mandatory human review."
                            ),
                            evidence_reference=None,
                            rewrite_candidate=None,
                            human_review_required=True,
                        )
                    )
                    finding_counter += 1
                    continue

                v_status, sev, explanation = _evaluate_sentence_against_fact(sentence, matched_fact)
                rewrite_cand: Optional[RewriteCandidate] = None
                human_req = v_status != VerificationStatus.SUPPORTED

                if generate_rewrites and v_status in (VerificationStatus.PARTIAL, VerificationStatus.CONTRADICTED):
                    rewrite_cand = build_revalidated_rewrite_candidate(
                        candidate_id=f"RW-CG-{finding_counter:04d}",
                        suggested_text=matched_fact.canonical_text,
                        fact=matched_fact,
                        rules=rules,
                        facts=facts,
                    )

                findings.append(
                    UnifiedFinding(
                        finding_id=f"FND-CG-{finding_counter:04d}",
                        expert_engine="ClaimGuard",
                        execution_state=ExecutionState.OK,
                        finding_type=FindingType.FACTUAL_CLAIM,
                        severity=sev,
                        verification_status=v_status,
                        document_block_id=block.document_block_id,
                        matched_text=sentence,
                        prefix_context=prefix,
                        suffix_context=suffix,
                        anchor_resolution_status=anchor_status,
                        explanation=explanation,
                        evidence_reference=_build_fact_evidence(matched_fact),
                        rewrite_candidate=rewrite_cand,
                        human_review_required=human_req,
                    )
                )
                finding_counter += 1

        exec_record = EngineExecutionRecord(
            expert_engine="ClaimGuard",
            mandatory_enforced=True,
            execution_state=ExecutionState.OK,
            findings_count=len(findings),
            notes="Baseline approved-fact and required-condition verification completed.",
        )
        return findings, exec_record

    except Exception as exc:
        return [], EngineExecutionRecord(
            expert_engine="ClaimGuard",
            mandatory_enforced=False,
            execution_state=ExecutionState.ERROR,
            findings_count=0,
            notes=f"ClaimGuard execution error: {type(exc).__name__}",
        )