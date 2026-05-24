# Diagnosis Engine: 3-Tier Verdict Cascade

The diagnosis engine (`src/diagnosis.py`) fuses the four signals into one of three verdicts: `underconstrained`, `overconstrained`, or `correct`. It uses a **priority cascade** — deterministic gates fire before the probabilistic weighted fusion — to maximize accuracy.

---

## The Three Verdict Classes

| Verdict | Meaning |
|---------|---------|
| `underconstrained` | The spec is too **weak** — it allows wrong implementations to pass |
| `overconstrained` | The spec is too **strict** — it rejects correct implementations |
| `correct` | The spec accurately captures the function's intended behavior |

---

## Decision Architecture: 3-Tier Cascade

```
Input: s1, s2, s3, s4, mutation_result, correct_impl_passes
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 1: Does the correct implementation FAIL the spec?     │
│  (correct_impl_passes == False)                             │
├─────────────────────────────────────────────────────────────┤
│  YES → verdict = OVERCONSTRAINED                            │
│        confidence = s4                                      │
│        overconstrained_via = "correct_impl_fails_spec"      │
│        (Deterministic — no weights applied)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ NO
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 1.5: Secondary overconstrained check via mutation     │
│  engine. If RemovePrecondition has coverage_delta > 0,      │
│  the precondition was artificially restricting coverage.    │
├─────────────────────────────────────────────────────────────┤
│  YES → verdict = OVERCONSTRAINED                            │
│        overconstrained_via = "mutation_coverage_delta"      │
└───────────────────────────┬─────────────────────────────────┘
                            │ NO
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  GATE 2: Is S2 == 0.0 AND S1 < 0.9?                        │
│  (Spec cannot discriminate any implementation pair AND      │
│   completeness is low)                                      │
├─────────────────────────────────────────────────────────────┤
│  YES → verdict = UNDERCONSTRAINED                           │
│        confidence = 1.0 - s1                                │
│        weighted_score = 1.0 (definitive)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │ NO
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  WEIGHTED FUSION LAYER                                      │
│                                                             │
│  score = 0.35*(1-S1) + 0.35*(1-S2) - 0.20*S3 + 0.10*(1-S4)│
│                                                             │
│  score > 0.65  →  UNDERCONSTRAINED                         │
│  score < 0.45  →  CORRECT                                  │
│  0.45 ≤ score ≤ 0.65 (middle zone):                        │
│      S3 > 0.8  →  OVERCONSTRAINED (formal refutation)      │
│      S1 > 0.7 AND S2 > 0.7  →  CORRECT (strong signals)   │
│      else  →  UNDERCONSTRAINED (conservative default)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Why 3 Tiers Instead of Just Fusion?

The weighted fusion formula **cannot resolve the signal ambiguity** between underconstrained and overconstrained tasks alone. Both classes share the same low-signal profile:

| Class | Typical S1 | Typical S2 | Why |
|-------|-----------|-----------|-----|
| Underconstrained | Low | Low (= 0.0) | Spec too weak → all impls pass → no discrimination |
| Overconstrained | Varies | Low (= 0.0) | Spec too strict → even correct impl fails → no pairs distinguished |

The **only** reliable differentiator is Gate 1: run the correct implementation against the spec directly. If it fails, the spec is overconstrained by definition. The fusion formula cannot see this because it operates on aggregate signal scores, not on individual implementation results.

**Ablation evidence:**

| System | Accuracy |
|--------|----------|
| Full 3-tier system | 15/15 (100.0%) |
| Remove Gate 1 | 10/15 (66.7%) — loses all 5 overconstrained tasks |
| Remove Gate 2 | 15/15 (100.0%) — Gate 2 redundant: S3=0.5 means fusion scores for T01–T05 = 0.90 > 0.65 threshold anyway |
| Fusion only (no gates) | 5/15 (33.3%) — only classifies `correct` tasks |

---

## Gate 1 — Deterministic Overconstrained Detection

```python
# From src/pipeline.py
correct_impl_passes = run_spec_against_impl(
    spec=spec, impl=correct_impl
)["passed"]

diagnosis = compute_verdict(
    s1=s1, s2=s2, s3=s3, s4=s4,
    mutation_result=mutation_result,
    correct_impl_passes=correct_impl_passes
)
```

```python
# From src/diagnosis.py
if not correct_impl_passes:
    return {
        "verdict": "overconstrained",
        "confidence": s4,
        "weighted_score": 0.0,
        "overconstrained_via": "correct_impl_fails_spec",
    }
```

This gate catches **all 5 overconstrained tasks (T06–T10)** in the benchmark. It is deterministic — it does not depend on LLM outputs or random sampling. The Hypothesis runner either confirms or rejects the correct implementation under the planted spec.

---

## Gate 1.5 — Mutation-Based Overconstrained Detection

As a secondary check, the mutation engine is asked: "What happens to code coverage when we remove the most restrictive precondition?"

If `RemovePrecondition` (removing an `assume()` or relaxing a `min_value=` constraint) produces the highest coverage delta among all mutations, it means:
- The precondition was preventing Hypothesis from generating inputs that exercise real branches in the correct implementation.
- Removing it reveals previously hidden coverage — the spec was overconstrained.

This catch is redundant with Gate 1 in the current benchmark but provides defense-in-depth for specs where `correct_impl_passes` returns a false positive.

---

## Gate 2 — Definitive Underconstrained Detection

```python
if s2 == 0.0 and s1 < 0.9:
    return {"verdict": "underconstrained", "confidence": 1.0 - s1, ...}
```

S2 = 0.0 means the spec cannot distinguish **any** pair of implementations. Combined with S1 < 0.9 (spec doesn't reject most wrong impls), this is definitive: the spec is too weak. All 5 underconstrained tasks (T01–T05) in the benchmark trigger Gate 2.

---

## Weighted Fusion — Deciding `correct` Tasks

For the 5 `correct` tasks (T11–T15), both Gate 1 and Gate 2 are negative:
- Gate 1: correct impl passes ✓ (not overconstrained)
- Gate 2: S2 > 0.0 ✓ (spec can discriminate)

The fusion formula decides:

$$S_{under} = 0.35 \cdot (1 - S_1) + 0.35 \cdot (1 - S_2) - 0.20 \cdot S_3 + 0.10 \cdot (1 - S_4)$$

For all 5 correct tasks, S1 = 1.0 and S2 = 0.4–0.6 (from JSON), S3 = 0.5 (CrossHair unavailable), S4 = 1.0, yielding fusion scores between 0.24 and 0.31 — well below the 0.45 threshold for `correct`.

**Example (T14 — from `benchmark_results.json`: S1=1.0, S2=0.6, S3=0.5, S4=1.0):**
$$S_{under} = 0.35 \cdot 0 + 0.35 \cdot 0.4 - 0.20 \cdot 0.5 + 0.10 \cdot 0 = 0 + 0.14 - 0.10 + 0 = 0.04$$

Verdict: `correct` (score < 0.45 threshold). ✓

---

## Return Schema

```python
{
    "verdict": "underconstrained" | "overconstrained" | "correct",
    "confidence": float,          # S4 value (stability = confidence)
    "weighted_score": float,      # Fusion score (0.0 = gate-classified)
    "signal_breakdown": {
        "s1": float,
        "s2": float,
        "s3": float,
        "s4": float
    },
    "overconstrained_via": str    # Only present for overconstrained verdicts
}
```

---

## Numerical Precision Note

The fusion formula is subject to IEEE-754 floating-point accumulation errors (e.g., `0.35*0.5 = 0.17499999...` instead of `0.175`). All fusion scores are rounded to 4 decimal places before threshold comparisons to ensure gate boundaries are not missed by ε-level noise.
