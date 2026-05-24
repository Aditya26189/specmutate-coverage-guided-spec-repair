# Signal Design: The Four Diagnostic Signals

SpecMutate computes four independent signals before making a diagnostic verdict. Each signal captures a fundamentally different observable property of a specification.

---

## Signal 1 (S1) — Completeness Score

**Source:** `src/signal1.py`  
**Question:** *What fraction of wrong implementations does the spec correctly reject?*

### How it works

1. A prompt is sent to the LLM asking it to generate **5 adversarial implementations** — implementations that are deliberately wrong but designed to exploit a weak spec.
2. Each adversarial implementation is run against the spec via the Hypothesis runner (`runner.py`).
3. S1 = `rejected_count / 5`. High S1 means the spec is complete (catches bugs). Low S1 means the spec is too weak to detect bugs.

### What it signals

| S1 Score | Interpretation |
|----------|---------------|
| ≥ 0.8 | Spec is strong — rejects most wrong implementations |
| 0.4–0.8 | Spec has partial coverage |
| < 0.4 | Spec is likely underconstrained — bugs slip through |

### Design rationale

Traditional mutation testing generates mutations of the *implementation* to check spec coverage. S1 inverts this: it generates mutations of the *implementation space* using an LLM that has read the spec. This is more realistic than syntactic AST mutations — the LLM generates semantically wrong-but-plausible implementations that a human programmer might accidentally write.

### API surface

```python
# Returns float only (safe for comparison)
score: float = compute_completeness_score(spec, task_description, function_name)

# Returns both score and counterexample data
result: dict = compute_s1(spec, task_description, function_name)
# result = {"score": float, "counterexamples": [{"impl": str, "counterexample": str}, ...]}
```

---

## Signal 2 (S2) — Discrimination Score

**Source:** `src/signal2.py`  
**Question:** *What fraction of implementation pairs can the spec tell apart?*

### How it works

1. All available implementations are run against the spec. Each implementation gets a `passed: True/False` label.
2. All pairwise combinations are enumerated.
3. A pair is "distinguished" if one passes and the other fails.
4. S2 = `distinguished_pairs / total_pairs`.

### What it signals

| S2 Score | Interpretation |
|----------|---------------|
| ≥ 0.5 | Spec separates correct from buggy implementations |
| ~0.0 | Spec is non-discriminating — either too strict (all fail) or too weak (all pass) |

### The Critical S2 = 0 Ambiguity

S2 = 0.0 is the most informative single data point in the system, but it is **ambiguous by itself**:

- **Underconstrained spec**: Spec is so weak that all implementations (correct + buggy) pass → S2 = 0.
- **Overconstrained spec**: Spec is so strict that even the correct implementation fails → nearly all implementations fail → S2 = 0.

Gate 1 (`correct_impl_passes`) resolves this ambiguity before S2 is ever used as a classification signal. S2 = 0 only triggers Gate 2 (underconstrained verdict) if Gate 1 confirmed the correct implementation passes.

### API surface

```python
score: float = compute_discrimination_score(spec, implementations)
# implementations: list of Python function code strings (including correct impl)
```

---

## Signal 3 (S3) — CrossHair Symbolic Refutation

**Source:** `src/signal3.py`  
**Question:** *Can a symbolic execution engine find a formal counterexample to the spec?*

### How it works

[CrossHair](https://github.com/pschanely/CrossHair) is a static analysis tool that uses symbolic execution (SMT-based concolic checking) to verify Python contracts. SpecMutate runs CrossHair's `--analysis_kind=hypothesis` mode on a combined file containing both the correct implementation and the spec.

1. **Health check**: CrossHair is tested on a trivial function first. If it's unavailable, S3 defaults to 0.5 (neutral).
2. **Analysis**: If CrossHair finds a counterexample or reports `cannot be satisfied`, S3 = 1.0 (spec has a formal issue).
3. Otherwise, S3 = 0.0 (no symbolic issue found).

### What it signals

| S3 Score | Interpretation |
|----------|---------------|
| 1.0 | CrossHair formally proved the spec is inconsistent or has a counterexample |
| 0.5 | CrossHair unavailable (N/A — treated as neutral in fusion) |
| 0.0 | No symbolic issue found within the timeout |

### Limitations

CrossHair's effectiveness depends on the spec's complexity and timeout. In the current benchmark, CrossHair returns S3 = 0.0 for all 15 tasks (the specs are too complex or use string operations that SMT solvers struggle with). S3 is included as a load-bearing component for more algebraic specs.

### API surface

```python
result: dict = compute_crosshair_score(function_code)
# function_code: combined string of impl + spec
# result = {"available": bool, "counterexample": str|None, "score": float}

score: float = compute_s3(spec, correct_impl)
```

---

## Signal 4 (S4) — Stability Score (Epistemic Uncertainty)

**Source:** `src/signal4.py`  
**Question:** *How consistent is the LLM when generating a spec for this task multiple times?*

### How it works

1. The LLM generates 3 independent specs for the same task at `temperature=0.7` (with caching disabled to force fresh generations).
2. Each spec is run against the correct implementation.
3. If all 3 pass or all 3 fail → S4 = 1.0 (consensus, stable).
4. If there's a split (some pass, some fail) → S4 = 0.0 (unstable).

### What it signals

| S4 Score | Interpretation |
|----------|---------------|
| 1.0 | LLM consistently generates the same type of spec — task is well-defined |
| 0.0 | LLM is uncertain — sometimes generates underconstrained specs, sometimes not |

### Design rationale

S4 measures **epistemic uncertainty** in LLM spec generation. A task that LLMs consistently disagree on is inherently ambiguous or at the boundary between specification classes. High instability is itself evidence that the spec under review may be at a class boundary, making the diagnosis less certain.

S4 does not contribute to the *direction* of the verdict (it cannot distinguish underconstrained from overconstrained). It contributes to the **confidence** of the diagnosis and appears in the weighted fusion as `0.10 * (1 - S4)`.

### API surface

```python
score: float = compute_stability_score(
    task_description,
    function_name,
    correct_impl=correct_impl,  # required for meaningful results
    n_generations=3             # default
)
```

---

## Signal Fusion Formula

The four signals are fused into a single scalar via weighted combination:

$$S_{under} = 0.35 \cdot (1 - S_1) + 0.35 \cdot (1 - S_2) + 0.20 \cdot S_3 + 0.10 \cdot (1 - S_4)$$

**Note:** S1 and S2 are inverted because low values indicate underconstrained specs. S3 is used directly (higher = more evidence of spec issue). S4 is inverted because low stability = more uncertainty = evidence of underconstrained boundary.

The fusion formula only activates after Gate 1 and Gate 2 in the 3-tier cascade. See [diagnosis.md](diagnosis.md) for details.

---

## Signal Weights Rationale

| Signal | Weight | Rationale |
|--------|--------|-----------|
| S1 | 0.35 | Strongest signal: directly tests spec completeness against adversarial impls |
| S2 | 0.35 | Equally strong: discrimination is the core purpose of a spec |
| S3 | 0.20 | Formal signal but limited to algebraic specs; strong when available |
| S4 | 0.10 | Epistemic confidence modifier, not a direction signal |
