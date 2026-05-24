# Feedback-Guided Spec Repair Loop

The repair loop (`src/repair_loop.py`) is the *generative* component of SpecMutate. After diagnosis identifies a spec as broken, the repair loop iteratively improves it using **grounded LLM prompts** — prompts that include specific, machine-discovered evidence about what is wrong.

---

## Design Philosophy

Generic repair prompts ("fix this spec") produce generic, often incorrect repairs. SpecMutate's repair loop is **grounded**: every prompt contains:

1. The exact AST node identified as problematic by the mutation engine
2. The specific mutation operator that revealed the problem (e.g., `RemovePrecondition`)
3. The coverage delta — quantitative evidence of how much the bad constraint restricted testing
4. An actual counterexample input that falsified the spec
5. What the correct implementation returns on that input
6. What a buggy implementation returns on that input (if available)
7. The current diagnostic signal scores (S1, S2, S4)

This means the LLM is not guessing — it is told *exactly which node to fix and why*.

---

## Loop Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                       Repair Loop (max 3 iterations)                   │
│                                                                        │
│  current_spec = planted_spec                                           │
│                                                                        │
│  ┌─── Iteration ──────────────────────────────────────────────────┐   │
│  │                                                                 │   │
│  │  1. Re-compute S1, S2, S4 on current_spec                      │   │
│  │  2. Run mutation engine → identify bad constraint               │   │
│  │  3. Get counterexample from runner                              │   │
│  │  4. Execute correct impl + buggy impl on counterexample input   │   │
│  │  5. Format REPAIR_PROMPT with all evidence                      │   │
│  │  6. Call LLM (temperature=0.2) → repaired_spec                  │   │
│  │  7. Check convergence:                                          │   │
│  │       correct_impl passes repaired_spec?                        │   │
│  │       repaired_spec rejects ≥ 70% of buggy_impls?              │   │
│  │       → CONVERGED                                               │   │
│  │       → else: current_spec = repaired_spec, next iteration      │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  Returns: {converged, iterations, final_spec, history, reason}         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## The Repair Prompt

The central prompt template (`src/templates.py: REPAIR_PROMPT`) structures every repair request identically:

```
You are repairing a Python Hypothesis specification diagnosed as {verdict}.

TASK DESCRIPTION: {task_description}

CURRENT (BROKEN) SPEC:
{current_spec}

DIAGNOSIS:
- Verdict: {verdict}
- S1 Completeness Score: {s1_score:.2f}
- S2 Discrimination Score: {s2_score:.2f}
- S4 Stability Score: {s4_score:.2f}

BAD CONSTRAINT IDENTIFIED BY MUTATION ENGINE:
  AST node: {bad_ast_node}
  Operator: {mutation_operator}
  Coverage delta: {coverage_delta:.4f}

COUNTEREXAMPLE INPUT that revealed the spec failure:
{counterexample}

CORRECT IMPLEMENTATION returns: {correct_output}
BUGGY IMPLEMENTATION returns: {buggy_output}

YOUR TASK:
Return ONLY a corrected Python Hypothesis spec...
```

The LLM has complete, actionable context. It knows exactly which node to fix, why it's wrong (coverage delta), and what behavior the correct implementation exhibits on the failing input.

---

## Convergence Criteria

A repaired spec is considered **converged** if:

1. `run_spec_against_impl(repaired_spec, correct_impl)["passed"] == True`  
   — The correct implementation passes the spec (not overconstrained)
   
2. At least `⌈0.70 × len(buggy_impls)⌉` buggy implementations **fail** the spec  
   — The spec catches bugs (not underconstrained)

The 70% threshold is intentional: some buggy implementations may be so close to correct that no reasonable spec can catch them without adding oracle-level constraints. Requiring 100% catch rate would over-engineer the repair.

If no buggy implementations are available (e.g., overconstrained tasks), criterion 1 alone suffices.

---

## Counterexample Extraction

The repair loop uses counterexample inputs in two ways:

**From the correct implementation** (overconstrained case):
```python
check = run_spec_against_impl(spec=current_spec, impl=correct_impl)
counterexample = check.get("counterexample")  # Hypothesis's Falsifying example output
```

**From buggy implementations** (underconstrained case):
```python
for buggy in buggy_impls:
    buggy_check = run_spec_against_impl(spec=current_spec, impl=buggy)
    if buggy_check["passed"]:
        counterexample = f"Buggy impl passes spec: {buggy[:100]}"
        break
```

When a counterexample input is found, the repair loop also executes both the correct and buggy implementations on that input to provide concrete output values for the LLM:

```python
correct_output = get_output_on_counterexample(correct_impl, function_name, counterexample)
buggy_output   = get_output_on_counterexample(buggy_impl,   function_name, counterexample)
```

The LLM then knows: "On input `n=0`, correct returns `1`, buggy returns `0`. Your spec must detect this difference."

---

## Case Study: T08 — is_palindrome (2-Iteration Repair)

**Task:** A function that returns `True` if a string is a palindrome (ignoring case and non-alphanumeric characters).

**Planted spec (broken — from benchmark.json):**
```python
@given(st.text(min_size=1, max_size=20))
def test_is_palindrome(s):
    assume(s.isalpha() and s.islower())
    result = is_palindrome(s)
    assert result is True  # ← wrong: requires ALL strings to be palindromes
```

**Iteration 1** (from `benchmark_results.json`):
- Bad constraint: `assume(s.isalpha() and s.islower())`, operator = `RemovePrecondition`, delta = 2
- Counterexample: `Falsifying example: test_is_palindrome(s='aab')`
- Repair attempt: `assert result == (s == s[::-1])`
- Convergence check: FAILED — still incorrect for case-insensitive palindromes (`s='0:'` fails)

**Iteration 2** (from `benchmark_results.json`):
- Counterexample: `Falsifying example: test_is_palindrome(s='0:')`
- Bad constraint: `null` (mutation engine found no improving mutation on the iteration-1 spec)
- Repair attempt:
```python
@given(st.text(max_size=20))
def test_is_palindrome(s):
    cleaned = "".join(c.lower() for c in s if c.isalnum())
    assert is_palindrome(s) == (cleaned == cleaned[::-1])
```
- Convergence check: PASSED ✓ — correct impl passes, repaired spec catches wrong impls

**Result:** `converged=True, iterations=2`

---

## Case Study: T09 — clamp (1-Iteration Repair)

**Important distinction for T09:** Gate 1 fires during *diagnosis* and classifies T09 as overconstrained (the correct implementation fails the spec `assume(lo <= x <= hi)` when `x < lo`). The mutation engine runs separately inside the *repair loop* to identify which constraint to fix. In T09's repair iteration, the mutation engine identified `result == x` (FlipComparison, delta=5) as the bad constraint — not `assume(lo <= x <= hi)`. The counterexample was `None` (the repair prompt used the Gate 1 falsifying example from diagnosis). The LLM correctly inferred to relax the assume and broaden the postcondition.

**Planted spec (broken):**
```python
@given(st.integers(), st.integers(), st.integers())
def test_clamp(x, lo, hi):
    assume(lo <= x <= hi)  # ← forces identity-only testing
    assert clamp(x, lo, hi) == x
```

**Iteration 1** (from `benchmark_results.json`):
- Bad constraint: `result == x`, operator = `FlipComparison`, delta = 5 (exposes 5 new lines)
- Counterexample: `None` (repair uses Gate 1 diagnosis context)
- Repair:
```python
@given(st.integers(), st.integers(), st.integers())
def test_clamp(x, lo, hi):
    assume(lo <= hi)
    result = clamp(x, lo, hi)
    expected = max(lo, min(x, hi))
    assert result == expected
```
- Convergence: PASSED ✓

**Result:** `converged=True, iterations=1`

---

## Return Schema

```python
{
    "converged": bool,
    "iterations": int,            # 0 if initial spec was already correct
    "final_spec": str,            # best spec found (whether converged or not)
    "history": [
        {
            "iteration": int,
            "s1_score": float,
            "s2_score": float,
            "s4_score": float,
            "bad_constraint": dict | None,
            "counterexample": str,
            "repaired_spec": str,
            "converged": bool
        },
        ...
    ],
    "convergence_reason": str     # human-readable explanation
}
```

---

## Benchmark Results

| Metric | Score |
|--------|-------|
| Tasks requiring repair | 10 (T01–T10: all underconstrained + overconstrained) |
| Repair convergence | 10/10 (100.0%) |
| Average iterations to convergence | 1.1 |
| 1-iteration repairs | 9 tasks |
| 2-iteration repairs | 1 task (T08) |

The high 1-iteration rate reflects the grounded prompt design: the LLM is given enough specific information that it fixes the right node on the first attempt in most cases.
