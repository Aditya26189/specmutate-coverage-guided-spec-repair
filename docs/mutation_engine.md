# Coverage-Guided Mutation Engine

The mutation engine (`src/mutator.py`) performs **AST-level spec mutation** scored by **coverage delta** — a rigorous, deterministic measure of which spec constraint is responsible for under-testing the correct implementation.

---

## Core Idea

A spec that is too restrictive (overconstrained) narrows the input space that Hypothesis explores. When Hypothesis only generates inputs satisfying a tight precondition, many branches in the correct implementation are never executed. The key insight:

> **If removing a constraint causes significantly more branches of the correct implementation to be covered, that constraint is the bad one.**

This is not about whether the spec "passes" or "fails" — it is about what the spec *forces Hypothesis to explore*.

---

## The Three Mutation Operators

### 1. `FlipComparison` — Comparison Boundary Inversion

Flips a comparison operator to its boundary-adjacent equivalent:

| Original | Mutated |
|----------|---------|
| `==` | `!=` |
| `!=` | `==` |
| `<` | `<=` |
| `<=` | `<` |
| `>` | `>=` |
| `>=` | `>` |

**Implemented via:** `FlipComparisonTransformer(ast.NodeTransformer)` — visits every `ast.Compare` node in the spec's AST and flips the operator type.

**Example:**
```python
# Original spec
assert len(result) == len(a) + len(b)

# Mutated spec (FlipComparison on ==)
assert len(result) != len(a) + len(b)
```

**What it finds:** Misspecified boundary conditions in postconditions. If flipping `<` to `<=` causes a large coverage delta, the original threshold was excluding valid edge cases.

---

### 2. `RemovePrecondition` — Constraint Relaxation

Removes or relaxes precondition constraints in two ways:

**a) `assume()` removal** — replaces `assume(condition)` with `pass`:
```python
# Original
assume(len(a) > 0)

# Mutated
pass
```

**b) Strategy constraint relaxation** — sets `min_value` or `min_size` to 0:
```python
# Original
st.integers(min_value=1)

# Mutated
st.integers(min_value=0)
```

**What it finds:** Overconstrained preconditions that artificially restrict the input domain, hiding edge cases from coverage.

---

### 3. `RemovePostcondition` — Assertion Elimination

Replaces an `assert` statement with `pass`:
```python
# Original
assert result == sorted(a + b)

# Mutated
pass
```

**What it finds:** Which postcondition is the most load-bearing. High coverage delta from removing a postcondition means removing it allowed branches to be reached that were previously blocked by the assertion failure.

---

## Coverage Delta Scoring

Each mutation is scored by running coverage measurement before and after:

```python
baseline_coverage = _measure_coverage(impl=correct_impl, spec=original_spec)

for mutation in all_mutations:
    mutated_coverage = _measure_coverage(impl=correct_impl, spec=mutation["mutated_spec"])
    new_branches = mutated_coverage - baseline_coverage
    mutation["coverage_delta"] = len(new_branches)
```

**Coverage delta** = number of lines in the correct implementation newly covered by the mutated spec that were not covered by the original spec.

The mutation with the **highest coverage delta** is returned as the `identify_bad_constraint()` result.

---

## Subprocess Coverage Measurement

Coverage is measured by running a self-contained Python script in a subprocess using `coverage.py`:

```python
_COVERAGE_TEMPLATE = '''
import coverage, json, sys

cov = coverage.Coverage(branch=True)
cov.start()

###IMPL_CODE###

from hypothesis import given, settings, strategies as st, assume
###SPEC_CODE###

if __name__ == "__main__":
    try:
        # Auto-discover and run test function
        test_fn = [v for k,v in globals().items() if k.startswith("test_")][0]
        test_fn()
    except Exception:
        pass
    finally:
        cov.stop()
        covered = set()
        for f in cov.get_data().measured_files():
            lines = cov.get_data().lines(f)
            if lines:
                covered.update(lines)
        print(json.dumps(list(covered)))
'''
```

**Why subprocess?** Because `coverage.py` and Hypothesis both maintain global state. Running them in-process would cause interference between successive measurements. Each measurement gets a clean process.

**Why `###PLACEHOLDER###`?** See [architecture.md](architecture.md#placeholder-substitution-not-f-strings) — Python source code contains `{curly braces}` that would corrupt f-string or `.format()` substitution.

---

## Identifying the Bad Constraint

```python
def identify_bad_constraint(spec: str, impl: str) -> dict | None:
    mutations = apply_mutations(spec=spec, impl=impl)
    if mutations and mutations[0]["coverage_delta"] > 0:
        return mutations[0]
    return None
```

Returns `None` if no mutation increases coverage (the spec is not restricting coverage — a good sign for `correct` specs).

The returned dict contains:
```python
{
    "operator": "RemovePrecondition",     # which operator
    "original": "assume(n >= 1)",         # original AST node as string
    "mutated": "pass",                    # what it was replaced with
    "mutated_spec": "...",                # full mutated spec text
    "coverage_delta": 3,                  # lines newly covered
    "newly_covered_lines": [14, 17, 22]   # which lines
}
```

This result is passed to:
1. `diagnosis.py` — to identify overconstrained specs via `RemovePrecondition` + positive delta
2. `repair_loop.py` — to ground the repair prompt: "Fix this specific AST node: `assume(n >= 1)`"

---

## Example: T09 (clamp)

**Role of the mutation engine in T09 — two separate steps:**
1. **Diagnosis (Gate 1):** T09 is classified as `overconstrained` because the correct implementation fails the spec — this is deterministic and requires no mutation analysis.
2. **Repair loop:** The mutation engine runs *inside* the repair loop to identify which constraint to fix. Here it scored `result == x` (FlipComparison, delta=5) as the highest-delta mutation — not `assume(lo <= x <= hi)`.

**Planted spec:**
```python
@given(st.integers(), st.integers(), st.integers())
def test_clamp(x, lo, hi):
    assume(lo <= x <= hi)  # ← BAD: restricts to only identity region
    assert clamp(x, lo, hi) == x
```

**Mutation analysis during repair loop (from `benchmark_results.json`):**
- `FlipComparison` on `result == x` → **delta = 5** (exposes 5 branches: clamp-down, clamp-up, and boundary lines)
- `RemovePrecondition` on `assume(lo <= x <= hi)` → delta not highest in this run
- `RemovePostcondition` → delta = 0

**Result:** `FlipComparison` on `result == x` wins → repair prompt says "Fix: `result == x` is wrong outside the identity region." The LLM correctly inferred this means the postcondition needs to be generalized, and relaxed the assume accordingly.

**Actual repaired spec (from JSON):**
```python
@given(st.integers(), st.integers(), st.integers())
def test_clamp(x, lo, hi):
    assume(lo <= hi)  # relaxed: allow any x
    result = clamp(x, lo, hi)
    expected = max(lo, min(x, hi))
    assert result == expected
```
