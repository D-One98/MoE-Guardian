from typing import List, Optional, Tuple
from app.schemas.contracts import (
    ApprovedFact,
    BackendRevalidationResult,
    BrandRule,
    ContentBlock,
    EngineExecutionRecord,
    ExecutionState,
    FindingType,
    RewriteCandidate,
    UnifiedFinding,
    VerificationStatus,
)
from app.engines.rule_guard import run_rule_guard


def _OrderMandatoryRulesFirst(rules: List[BrandRule]) -> List[BrandRule]:
    mandatory = [r for r in rules if r.mandatory_flag]
    optional = [r for r in rules if not r.mandatory_flag]
    return mandatory + optional


def validate_rewrite_candidate(
    candidate_id: str,
    suggested_text: str,
    rules: List[BrandRule],
    facts: List[ApprovedFact],
    original_finding_type: Optional[FindingType] = None,
    original_matched_text: Optional[str] = None,
) -> RewriteCandidate:
    """
    Backend Fail-Closed Rewrite Validation Coordinator.
    - Enforces mandatory policies first.
    - Runs deterministic RuleGuard on every rewrite candidate.
    - Runs ClaimGuard when the original flagged span contained a factual claim OR
      the candidate introduces or modifies factual/numeric assertions.
    - Never calls VoiceGuard recursively on its own generated output.
    - Assigns revalidation_passed = True ONLY when:
        1. All required engines complete with execution_state == OK.
        2. RuleGuard reports 0 violations.
        3. candidate_verification_status is SUPPORTED (if factual claim exists)
           or NOT_CLAIM_APPLICABLE (if no factual claim exists).
    """
    # Lazy import to avoid circular dependency with claim_guard
    from app.engines.claim_guard import (
        _looks_like_factual_or_promotional_assertion,
        _split_sentences_with_offsets,
        run_claim_guard_baseline,
    )

    ordered_rules = _OrderMandatoryRulesFirst(rules)
    temp_blocks = [
        ContentBlock(
            document_block_id="blk-rewrite-validation",
            text=suggested_text.strip(),
        )
    ]

    # 1. Always run RuleGuard on the candidate rewrite
    rg_findings, rg_exec = run_rule_guard(temp_blocks, ordered_rules)
    rg_state = rg_exec.execution_state
    rg_violations_count = len(rg_findings)

    # 2. Determine whether ClaimGuard is required
    orig_had_claim = (
        original_finding_type == FindingType.FACTUAL_CLAIM
        or (
            original_matched_text is not None
            and any(
                _looks_like_factual_or_promotional_assertion(seg)
                for seg, _ in _split_sentences_with_offsets(original_matched_text)
            )
        )
    )
    cand_has_claim = any(
        _looks_like_factual_or_promotional_assertion(seg)
        for seg, _ in _split_sentences_with_offsets(suggested_text)
    )

    claim_guard_required = orig_had_claim or cand_has_claim

    cg_state = ExecutionState.NOT_APPLICABLE
    candidate_verification_status = VerificationStatus.NOT_CLAIM_APPLICABLE

    if claim_guard_required:
        cg_findings, cg_exec = run_claim_guard_baseline(
            temp_blocks,
            facts,
            ordered_rules,
            generate_rewrites=False,
        )
        cg_state = cg_exec.execution_state

        if cg_state in (ExecutionState.ERROR, ExecutionState.INSUFFICIENT_DATA):
            candidate_verification_status = VerificationStatus.UNVERIFIABLE
        elif not cg_findings:
            # If the original span had a claim, but the candidate stripped all factual assertions,
            # check whether the candidate still contains any factual assertion
            if cand_has_claim:
                candidate_verification_status = VerificationStatus.UNVERIFIABLE
            else:
                candidate_verification_status = VerificationStatus.NOT_CLAIM_APPLICABLE
        else:
            # Aggregate candidate claim statuses conservatively (worst state wins)
            statuses = {f.verification_status for f in cg_findings}
            if VerificationStatus.CONTRADICTED in statuses:
                candidate_verification_status = VerificationStatus.CONTRADICTED
            elif VerificationStatus.UNVERIFIABLE in statuses:
                candidate_verification_status = VerificationStatus.UNVERIFIABLE
            elif VerificationStatus.PARTIAL in statuses:
                candidate_verification_status = VerificationStatus.PARTIAL
            elif VerificationStatus.SUPPORTED in statuses:
                candidate_verification_status = VerificationStatus.SUPPORTED
            else:
                candidate_verification_status = VerificationStatus.UNVERIFIABLE

    # 3. Strict Fail-Closed Evaluation
    required_engines_ok = (
        rg_state == ExecutionState.OK
        and (
            not claim_guard_required
            or cg_state == ExecutionState.OK
        )
    )

    # Note: If the candidate was supposed to fix a FACTUAL_CLAIM, or if the candidate
    # contains a factual claim, it MUST be SUPPORTED (or if it is a pure non-factual
    # rewrite with zero claims in candidate, NOT_CLAIM_APPLICABLE is permitted only when
    # no factual claim exists in the candidate).
    if cand_has_claim:
        claim_status_acceptable = (
            candidate_verification_status == VerificationStatus.SUPPORTED
        )
    elif orig_had_claim:
        # A rewrite for a factual claim that removes the claim altogether is only acceptable
        # if it wasn't required to be a supported fact, OR to be strictly conservative:
        # if a factual claim was in the original span and the candidate still claims something, it must be SUPPORTED.
        # If the candidate is purely non-factual text, NOT_CLAIM_APPLICABLE is valid.
        claim_status_acceptable = (
            candidate_verification_status
            in (VerificationStatus.SUPPORTED, VerificationStatus.NOT_CLAIM_APPLICABLE)
        )
    else:
        claim_status_acceptable = (
            candidate_verification_status == VerificationStatus.NOT_CLAIM_APPLICABLE
        )

    revalidation_passed = bool(
        required_engines_ok
        and rg_violations_count == 0
        and claim_status_acceptable
    )

    return RewriteCandidate(
        candidate_id=candidate_id,
        suggested_text=suggested_text.strip(),
        backend_revalidation=BackendRevalidationResult(
            assigned_by="BACKEND_COORDINATOR",
            executed_checks={
                "mandatory_policies_enforced": True,
                "RuleGuard_execution_state": rg_state.value,
                "RuleGuard_violations_count": rg_violations_count,
                "ClaimGuard_required": claim_guard_required,
                "ClaimGuard_execution_state": cg_state.value,
                "VoiceGuard_recursive_call": "SKIPPED_BY_DESIGN",
            },
            candidate_verification_status=candidate_verification_status,
            revalidation_passed=revalidation_passed,
        ),
    )