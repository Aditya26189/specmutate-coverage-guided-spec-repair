# SpecMutate Architecture

SpecMutate is a **coverage-guided, LLM-assisted specification repair system**. Given a Python function and a Hypothesis property-based test specification, it automatically determines whether the spec is correct, underconstrained (too weak), or overconstrained (too strict) — and then repairs it.

---

## High-Level Pipeline

```
         ┌─────────────────────────────────────────────────────────────────┐
         │                    SpecMutate Pipeline                          │
         │                                                                 │
  Input  │   planted_spec + correct_impl + buggy_impls + description       │
    ─────┼──────────────────────────────────────────────────────────────►  │
         │                         │                                       │
         │              ┌──────────▼──────────┐                           │
         │              │    SIGNAL LAYER      │                           │
         │              │  S1  S2  S3  S4      │                           │
         │              └──────────┬──────────┘                           │
         │                         │                                       │
         │              ┌──────────▼──────────┐                           │
         │              │  MUTATION ENGINE     │                           │
         │              │  FlipComparison      │                           │
         │              │  RemovePrecondition  │                           │
         │              │  RemovePostcondition │                           │
         │              └──────────┬──────────┘                           │
         │                         │                                       │
         │              ┌──────────▼──────────┐                           │
         │              │   DIAGNOSIS ENGINE   │                           │
         │              │  3-Tier Cascade      │                           │
         │              │  Gate1 → Gate2       │                           │
         │              │  → Weighted Fusion   │                           │
         │              └──────────┬──────────┘                           │
         │                         │                                       │
         │              ┌──────────▼──────────┐                           │
         │              │   REPAIR LOOP        │                           │
         │              │  Feedback-guided LLM │                           │
         │              │  Max 3 iterations    │                           │
         │              └──────────┬──────────┘                           │
         │                         │                                       │
  Output │            verdict + repaired_spec + signals                    │
    ◄────┼──────────────────────────────────────────────────────────────── │
         └─────────────────────────────────────────────────────────────────┘
```

---

## Module Map

```
src/
├── pipeline.py       ← Top-level orchestrator — calls everything in order
├── llm.py            ← LLM gateway with key rotation, caching, rate limiting
├── runner.py         ← Subprocess Hypothesis runner (safe, isolated)
├── signal1.py        ← S1: Completeness score (adversarial LLM harnesses)
├── signal2.py        ← S2: Discrimination score (pairwise oracle)
├── signal3.py        ← S3: CrossHair symbolic refutation
├── signal4.py        ← S4: Stability score (epistemic uncertainty)
├── mutator.py        ← Coverage-guided mutation engine (3 AST operators)
├── diagnosis.py      ← 3-tier verdict cascade
├── repair_loop.py    ← Feedback-guided spec repair loop
├── spec_gen.py       ← LLM spec generation from description
├── impl_gen.py       ← LLM implementation generation
└── templates.py      ← All LLM prompt templates (centralized)
```

---

## Data Flow

### Step 1 — Load Spec
The pipeline loads either the `planted_spec` from `benchmark.json` (default) or generates one fresh via `spec_gen.py`. The planted spec is deliberately broken (underconstrained or overconstrained) — that is the artifact under diagnosis.

### Step 2 — Compute Signals (Parallel Conceptually)
Four independent signals are computed:

| Signal | Source | What it measures |
|--------|--------|-----------------|
| S1 | `signal1.py` | What fraction of LLM-generated wrong impls does the spec reject? |
| S2 | `signal2.py` | What fraction of implementation pairs does the spec distinguish? |
| S3 | `signal3.py` | Does CrossHair find a symbolic counterexample? |
| S4 | `signal4.py` | How stable is LLM spec generation (epistemic uncertainty)? |

### Step 3 — Mutation Engine
`mutator.py` applies AST-level mutations to the spec and measures **coverage delta** — how many more lines of the correct implementation become covered after each mutation. The mutation with the highest delta is the "bad constraint."

### Step 4 — Diagnosis
`diagnosis.py` fuses signals via a 3-tier cascade:
1. **Gate 1**: If the correct implementation fails the spec → `overconstrained` (deterministic)
2. **Gate 2**: If S2 == 0.0 and S1 < 0.9 → `underconstrained` (definitive signal)
3. **Weighted Fusion**: `0.35*(1-S1) + 0.35*(1-S2) + 0.20*S3 + 0.10*(1-S4)` decides `correct` vs others

### Step 5 — Repair Loop
`repair_loop.py` runs up to 3 LLM-guided repair iterations. Each iteration:
- Re-evaluates signals on the current spec
- Identifies the bad constraint via mutation engine
- Extracts a counterexample input
- Formats a grounded repair prompt with all this context
- Asks the LLM to fix exactly the identified node
- Checks convergence: repaired spec passes correct impl AND rejects ≥70% of buggy impls

---

## Key Design Decisions

### Subprocess Isolation
The `runner.py` and `mutator.py` modules run Hypothesis tests in **separate subprocesses**, not in-process. This prevents:
- Hypothesis's internal state from leaking between test runs
- Spec or impl syntax errors from crashing the main process
- Any `assume()` calls from interfering with the parent process's random state

### Placeholder Substitution (Not f-strings)
All code is injected into templates via `###PLACEHOLDER###.replace()`, never with Python's `.format()` or f-strings. This is critical because Python source code routinely contains `{curly braces}` (dicts, sets, f-strings, comprehensions) which would corrupt any f-string substitution.

### Key Rotation
`llm.py` maintains a pool of up to 10 Gemini API keys loaded directly from `.env` at call time (not from environment variables, which can be stale after `.env` edits). On each 429 quota error, it rotates to the next key. When all keys hit quota on the active model, it escalates to the next model in `MODEL_ROTATION_LIST`.

### LLM Caching
All LLM calls are cached via MD5 hash of `(prompt, temperature)` in `.llm_cache.json`. This means the benchmark can be re-run partially without re-spending quota. The cache is intentionally committed to the repo as a reproducibility artifact.

---

## Entry Points

| Script | Purpose |
|--------|---------|
| `python run_benchmark.py` | Run the full 15-task benchmark |
| `python check_api_keys.py` | Validate which API keys are active |
| `streamlit run app.py` | Launch the interactive Streamlit dashboard |
| `pytest tests/` | Run the unit test suite |
