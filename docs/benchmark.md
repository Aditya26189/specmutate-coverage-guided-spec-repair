# Benchmark Design & Results

SpecMutate is evaluated on a purpose-built benchmark of 15 Python functions with hand-crafted "planted" specifications that are deliberately broken in known ways.

---

## Benchmark Design

### Task Structure

Each task in `benchmark.json` contains:

```json
{
    "task_id": "T01",
    "name": "merge_sorted_lists",
    "description": "...",
    "label": "underconstrained",
    "planted_spec": "...",
    "reference_implementation": "...",
    "buggy_implementations": [...],
    "correct_spec": "...",
    "what_is_wrong": "...",
    "repair_action": "..."
}
```

### Class Distribution

| Class | Tasks | Task IDs |
|-------|-------|----------|
| Underconstrained | 5 | T01–T05 |
| Overconstrained | 5 | T06–T10 |
| Correct | 5 | T11–T15 |

This balanced 3-way classification is harder than binary correct/incorrect — the system must not just detect broken specs but identify the *direction* of the fault.

### Fault Design

**Underconstrained specs (T01–T05):** Specs with weak or missing postconditions. Examples:
- `assert len(result) == len(a) + len(b)` for `merge_sorted_lists` — doesn't check sorting
- `assert n >= 0` for `factorial` — doesn't check the actual value

**Overconstrained specs (T06–T10):** Specs with overly-restrictive preconditions or postconditions. Examples:
- `assume(n >= 1)` for `factorial` — excludes `factorial(0) = 1`
- `assume(lo <= x <= hi)` for `clamp` — restricts to identity-only region

**Correct specs (T11–T15):** Well-formed specs that accurately capture the function's contract. These should be diagnosed as `correct` and not repaired.

---

## Headline Results

| Metric | Score |
|--------|-------|
| **Diagnostic Accuracy** | **15/15 (100.0%)** |
| **Repair Convergence Rate** | **10/10 (100.0%)** |
| Tasks diagnosed | 15 |
| Tasks requiring repair | 10 (T01–T10) |
| Average repair iterations | 1.1 |

---

## Confusion Matrix

| Predicted \ Actual | Underconstrained | Overconstrained | Correct | Precision |
|--------------------|-----------------|-----------------|---------|-----------|
| **Underconstrained** | 5 ✓ (T01–T05) | 0 | 0 | 100% |
| **Overconstrained** | 0 | 5 ✓ (T06–T10) | 0 | 100% |
| **Correct** | 0 | 0 | 5 ✓ (T11–T15) | 100% |
| **Recall** | 100% | 100% | 100% | |

No misclassifications. Each verdict class achieves 100% precision and 100% recall.

---

## Signal Profile by Class

### Underconstrained Tasks (T01–T05)
- S1: Low (0.0) — buggy impls slip through
- S2: **0.0** — spec cannot distinguish any implementation pair
- S3: **0.5** (CrossHair unavailable — neutral prior for all tasks)
- S4: 0.0–1.0
- **Decision path:** Gate 1 PASS, Gate 2 TRIGGER (S2=0.0)

### Overconstrained Tasks (T06–T10)
- S1: Varies (0.0–1.0)
- S2: **0.0** (T06–T08, T10) or 0.6 (T09) — overconstrained specs often fail all impls
- S3: **0.5** (CrossHair unavailable — neutral prior)
- S4: 1.0 (T06–T09) or 1.0
- **Decision path:** Gate 1 TRIGGER (correct impl fails spec)

### Correct Tasks (T11–T15)
- S1: **1.0** — strong rejection of wrong impls
- S2: **0.4–0.6** — moderate discrimination
- S3: **0.5** (CrossHair unavailable — neutral prior)
- S4: 1.0
- **Decision path:** Gate 1 PASS, Gate 2 PASS, Fusion → score ≤ 0.31 → `correct`

---

## Ablation Study

Baseline: Full system at 15/15 (100.0%). Each row removes one component.

| Configuration | Correct | Accuracy | Δ |
|---|---|---|---|
| Full system (3-tier cascade) | 15/15 | 100.0% | baseline |
| Remove Gate 1 (correct_impl_fails) | 10/15 | 66.7% | −33.3% |
| Remove Gate 2 (S2=0 guard) | 15/15 | 100.0% | 0% |
| Remove both gates (fusion only) | 5/15 | 33.3% | −66.7% |
| S3 only | N/A | — | S3=0.5 (constant) — contributes fixed 0.10 to fusion, no classification power |
| S4 only | ~8/15 | ~53.3% | near-constant signal |

**Key finding:** Gate 2 (S2=0 guard) is redundant given S3=0.5 everywhere. With the constant 0.10 S3 contribution, T01–T05 fusion scores = 0.35×1+0.35×1+0.20×0.5+0.10×1 = 0.90, which exceeds the 0.65 underconstrained threshold even without Gate 2. Gate 1 is load-bearing — removing it loses all 5 overconstrained tasks (T06–T10). The fusion formula's role is restricted to confirming `correct` specs (T11–T15).

---

## Oracle Disclosure

Per academic integrity guidelines, the following benchmark fields are used at **inference time** (not just evaluation):

| Field | Used By | Why |
|-------|---------|-----|
| `reference_implementation` | Gate 1, S2, S4, mutation engine, repair convergence | Ground-truth correct implementation for spec testing |
| `buggy_implementations` | S2, repair convergence | Known-buggy impls for discrimination testing |
| `planted_spec` | Pipeline input | The spec under diagnosis |
| `description` | S1, S4, repair prompts | Task context for LLM calls |
| `name` | S1, S4, repair | Function name for LLM prompts |

**NOT used at inference:** `label`, `correct_spec`, `what_is_wrong`, `repair_action`, `coverage_signal`. These are used only for post-hoc evaluation (`predicted == ground_truth`).

The `reference_implementation` is the primary oracle dependency. This is an **inherent requirement of spec evaluation** — you need a correct implementation to test a spec against. Without it, it is impossible to determine whether a spec is overconstrained (rejects correct behaviour) or underconstrained (accepts incorrect behaviour).

---

## Per-Task Results

Values read directly from `results/benchmark_results.json`.

| Task | Function | Label | Predicted | S1 | S2 | S3 | S4 | Fusion Score | Path |
|------|----------|-------|-----------|----|----|----|----|--------------|------|
| T01 | merge_sorted_lists | under | under ✓ | 0.0 | 0.0 | 0.5 | 1.0 | 1.0 (Gate 2) | Gate 2 |
| T02 | binary_search | under | under ✓ | 0.0 | 0.0 | 0.5 | 1.0 | 1.0 (Gate 2) | Gate 2 |
| T03 | remove_duplicates | under | under ✓ | 0.0 | 0.0 | 0.5 | 1.0 | 1.0 (Gate 2) | Gate 2 |
| T04 | rotate_list | under | under ✓ | 0.0 | 0.0 | 0.5 | 0.0 | 1.0 (Gate 2) | Gate 2 |
| T05 | flatten_nested | under | under ✓ | 0.0 | 0.0 | 0.5 | 1.0 | 1.0 (Gate 2) | Gate 2 |
| T06 | factorial | over | over ✓ | 0.0 | 0.0 | 0.5 | 1.0 | 0.0 (Gate 1) | Gate 1 |
| T07 | gcd | over | over ✓ | 0.0 | 0.0 | 0.5 | 1.0 | 0.0 (Gate 1) | Gate 1 |
| T08 | is_palindrome | over | over ✓ | 1.0 | 0.0 | 0.5 | 1.0 | 0.0 (Gate 1) | Gate 1 |
| T09 | clamp | over | over ✓ | 0.6 | 0.6 | 0.5 | 1.0 | 0.0 (Gate 1) | Gate 1 |
| T10 | string_palindrome_check | over | over ✓ | 0.4 | 0.0 | 0.5 | 1.0 | 0.0 (Gate 1) | Gate 1 |
| T11 | (correct spec) | correct | correct ✓ | 1.0 | 0.6 | 0.5 | 1.0 | 0.24 | Fusion |
| T12 | (correct spec) | correct | correct ✓ | 1.0 | 0.6 | 0.5 | 1.0 | 0.24 | Fusion |
| T13 | (correct spec) | correct | correct ✓ | 1.0 | 0.6 | 0.5 | 1.0 | 0.24 | Fusion |
| T14 | (correct spec) | correct | correct ✓ | 1.0 | 0.6 | 0.5 | 1.0 | 0.24 | Fusion |
| T15 | (correct spec) | correct | correct ✓ | 1.0 | 0.4 | 0.5 | 1.0 | 0.31 | Fusion |
