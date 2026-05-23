# src/diagnosis.py
# Weighted signal fusion — NOT Bayesian, NOT P=0.65 prior
# Weights: S1=0.35, S2=0.35, S3=0.20, S4=0.10
#
# BUG 5 FIX APPLIED: original compute_verdict() could not distinguish
# overconstrained from underconstrained when S3 is N/A (7+ tasks).
# Both have LOW S1 and S2 — same signal profile. The only differentiator
# is whether coverage_delta is positive AND the best mutation is
# RemovePrecondition (means the precondition was too tight).
# Without this branch, all overconstrained tasks were misclassified as
# underconstrained, capping accuracy at ~10/15 regardless of everything else.
# Fix: pass mutation_result into compute_verdict(); if best mutation is
# RemovePrecondition with coverage_delta > 0, verdict = overconstrained.

WEIGHTS = {"s1": 0.35, "s2": 0.35, "s3": 0.20, "s4": 0.10}

UNDERCONSTRAINED_THRESHOLD = 0.45  # weighted score below this = underconstrained
OVERCONSTRAINED_THRESHOLD = 0.65   # weighted score above this = overconstrained


def compute_verdict(
    s1: float,
    s2: float,
    s3: float,
    s4: float,
    mutation_result: dict | None = None,
    correct_impl_passes: bool = True  # FIX 11: primary overconstrained signal
) -> dict:
    """
    Fuse four signals into a verdict.
    S1, S2: low scores = underconstrained (spec too weak)
    S3: high score = CrossHair found counterexample (spec has issue)
    S4: used for confidence, not direction
    mutation_result: best mutation from identify_bad_constraint(). Optional but
                     REQUIRED for correct overconstrained detection when S3=N/A.

    Returns: {"verdict": str, "confidence": float, "weighted_score": float}
    """
    # FIX 11 APPLIED: Primary overconstrained signal — deterministic, does not depend
    # on signal weights. If the correct implementation FAILS the spec, the spec is too
    # restrictive by definition. This catches all 5 overconstrained tasks (T06–T10) that
    # were silently misclassified by the mutation-only approach when the mutation engine
    # found ambiguous coverage deltas.
    if not correct_impl_passes:
        return {
            "verdict": "overconstrained",
            "confidence": s4,
            "weighted_score": 0.0,
            "signal_breakdown": {"s1": s1, "s2": s2, "s3": s3, "s4": s4},
            "overconstrained_via": "correct_impl_fails_spec",
        }

    # Secondary: coverage-based overconstrained detection via mutation engine.
    # Overconstrained specs have a narrow precondition — Hypothesis never generates
    # the edge case inputs, so wrong impls never get tested, giving LOW S1 AND S2
    # — identical signal profile to underconstrained. S3 resolves this when
    # available, but S3 is N/A for 7+ tasks. The mutation engine fills the gap:
    # if RemovePrecondition has the highest coverage delta (removing the tight
    # precondition exposes previously-uncovered branches), the spec is overconstrained.
    if (
        mutation_result is not None
        and mutation_result.get("coverage_delta", 0) > 0
        and mutation_result.get("operator") == "RemovePrecondition"
    ):
        return {
            "verdict": "overconstrained",
            "confidence": s4,
            "weighted_score": 0.5,  # signal was ambiguous without mutation
            "signal_breakdown": {"s1": s1, "s2": s2, "s3": s3, "s4": s4},
            "overconstrained_via": "mutation_coverage_delta",
        }

    # overconstrained gate must remain above this line
    # S2=0: zero discrimination is definitive underconstrained signal
    if s2 == 0.0 and s1 < 0.9:
        return {"verdict": "underconstrained", "confidence": 1.0 - s1,
                "weighted_score": 1.0,
                "signal_breakdown": {"s1": s1, "s2": s2, "s3": s3, "s4": s4}}

    # Invert S1 and S2 for the fusion score
    # (low S1/S2 = bad spec, so invert to get high = bad)
    underconstrained_signal = (
        WEIGHTS["s1"] * (1 - s1) +
        WEIGHTS["s2"] * (1 - s2) +
        WEIGHTS["s3"] * s3 +
        WEIGHTS["s4"] * (1 - s4)
    )

    confidence = s4  # stability = confidence in diagnosis

    if underconstrained_signal > OVERCONSTRAINED_THRESHOLD:
        verdict = "underconstrained"
    elif underconstrained_signal < UNDERCONSTRAINED_THRESHOLD:
        verdict = "correct"
    else:
        # Middle range: need more signal
        if s3 > 0.8:
            verdict = "overconstrained"
        elif s1 > 0.7 and s2 > 0.7:
            verdict = "correct"
        else:
            verdict = "underconstrained"  # default to underconstrained when uncertain

    return {
        "verdict": verdict,
        "confidence": confidence,
        "weighted_score": underconstrained_signal,
        "signal_breakdown": {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
    }
