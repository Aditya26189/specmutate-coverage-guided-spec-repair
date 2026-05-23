**Diagnostic Accuracy: 15/15 (100.0%) | Repair Convergence Rate: 10/10 (100.0%)**

# SpecMutate

> **Coverage-guided specification diagnosis and CEGIS repair for Python/Hypothesis property-based tests.**

SpecMutate automatically diagnoses whether a Hypothesis specification is *underconstrained*, *overconstrained*, or *correct* — then repairs broken specs using a counterexample-guided synthesis loop grounded in AST-level mutation and coverage delta analysis.

---

## Benchmark Results

| Metric | Score |
|--------|-------|
| Diagnostic Accuracy | **15 / 15 (100.0%)** |
| Repair Convergence Rate | **10 / 10 (100.0%)** |
| Average Iterations to Convergence | **1.2** |
| Benchmark Size | 15 tasks (5 underconstrained / 5 overconstrained / 5 correct) |
| LLM Backend | Gemini (model-rotation: 3.5-flash → 3-flash-preview → 2.5-flash) |

Full per-task results, signal breakdowns, ablation, and repair samples: [RESULTS.md](RESULTS.md)

---

## How It Works

```
Planted Spec
     │
     ▼
 ┌─────────────────────────────────────────────────────┐
 │  1. Signal Analysis                                  │
 │     S1 (Completeness, w=0.35)  — LLM buggy impls    │
 │     S2 (Discrimination, w=0.35) — impl pair scoring  │
 │     S3 (CrossHair, w=0.20)     — symbolic refutation │
 │     S4 (Stability, w=0.10)     — temp=0.7 variance   │
 └─────────────┬───────────────────────────────────────┘
               │
     ┌─────────▼────────────────┐
     │  Gate 1: correct_impl    │  ← primary overconstrained signal
     │  passes spec?            │    NO → overconstrained (T06–T10)
     └─────────┬────────────────┘
               │ YES
     ┌─────────▼────────────────┐
     │  Gate 2: S2 == 0.0?      │  ← zero discrimination = underconstrained
     └─────────┬────────────────┘    YES → underconstrained (T01–T05)
               │ NO
     ┌─────────▼──────────────┐
     │  Mutation Engine        │  ← AST mutation + coverage delta
     │  FlipComparison         │
     │  RemovePrecondition     │
     │  RemovePostcondition    │
     └─────────┬──────────────┘
               │
     ┌─────────▼──────────┐
     │  Weighted Fusion    │  → verdict (under/over/correct)
     └─────────┬──────────┘
               │
     ┌─────────▼──────────┐
     │  CEGIS Repair Loop  │  → repaired spec (max 3 iters, avg 1.2)
     └────────────────────┘
```

---

## Differentiator vs SOTA

| Dimension | VeriAct (arXiv:2604.00280) | SpecRL [2604.05820] | VeriSpecGen [2604.10392] | **SpecMutate** |
|-----------|----------------------------|---------------------|--------------------------|----------------|
| Target Language | Java/JML | Dafny | Lean 4 | **Python/Hypothesis** |
| Infrastructure | JVM + JML toolchain | RL training pipeline | Lean ITP | **Standard Python subprocesses** |
| Fault localization | ❌ Black-box | ❌ Black-box | ❌ Black-box | ✅ **AST node + coverage delta** |
| Repair | ❌ None | ❌ None | ❌ None | ✅ **CEGIS with grounded LLM** |
| Overconstrained detection | ❌ No | ❌ No | ❌ No | ✅ **Deterministic gate** |

---

## Quickstart

```bash
# 1. Install dependencies
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Set your API keys in .env
echo "GOOGLE_API_KEY=your_key_here" > .env
# Optional: GOOGLE_API_KEY_1 ... GOOGLE_API_KEY_9 for key rotation

# 3. Run the full benchmark
python run_benchmark.py

# 4. Launch the Streamlit dashboard
streamlit run app.py

# 5. Run the test suite
pytest tests/ -v
```

---

## Project Structure

```
specmutate/
├── src/
│   ├── llm.py          # Gemini client · multi-model rotation · key rotation · circuit breaker
│   ├── spec_gen.py     # Spec generation from task description
│   ├── impl_gen.py     # Buggy implementation generation (S1 harness)
│   ├── runner.py       # Isolated Hypothesis subprocess runner
│   ├── signal1.py      # S1: Completeness — fraction of buggy impls rejected
│   ├── signal2.py      # S2: Discrimination — correct/buggy pair separation
│   ├── signal3.py      # S3: CrossHair symbolic refutation (health-check gated)
│   ├── signal4.py      # S4: Stability — spec variance at temperature=0.7
│   ├── mutator.py      # Coverage-guided AST mutation engine
│   ├── repair_loop.py  # CEGIS repair loop (max 3 iterations, no fallback)
│   ├── diagnosis.py    # Weighted signal fusion + verdict (Gates 1 & 2 + fusion)
│   └── pipeline.py     # End-to-end orchestration
├── tests/              # Full pytest suite (23 tests)
├── results/            # Benchmark results JSON
│   └── benchmark_results.json
├── benchmark.json      # 15-task benchmark (5/5/5 distribution)
├── templates.py        # LLM prompt templates (REPAIR_PROMPT, SPEC_GEN_PROMPT, etc.)
├── app.py              # Streamlit dashboard
├── run_benchmark.py    # Benchmark runner entry point
├── RESULTS.md          # Full results, ablation, repair samples
├── AGENTS.md           # Architectural constraints and locked decisions
└── requirements.txt
```

---

## Architecture: Diagnosis Logic

```python
# Gate 1 — primary overconstrained signal (deterministic)
if not correct_impl_passes:
    return verdict = "overconstrained"

# Gate 2 — zero discrimination = definitively underconstrained
if s2 == 0.0 and s1 < 0.9:
    return verdict = "underconstrained"

# Weighted fusion
score = 0.35*(1-S1) + 0.35*(1-S2) + 0.20*S3 + 0.10*(1-S4)
# score > 0.65 → underconstrained
# score < 0.45 → correct
# middle band → use S3 + S1/S2 heuristics
```

---

## API Key & Model Configuration

SpecMutate supports up to 10 API keys with round-robin rotation. When all keys hit quota on a model, it automatically escalates to the next model:

```python
MODEL_ROTATION_LIST = [
    "gemini-3.5-flash",       # primary
    "gemini-3-flash-preview", # fallback 1
    "gemini-2.5-flash",       # fallback 2
]
```

Configure in `.env`:
```
GOOGLE_API_KEY=...
GOOGLE_API_KEY_1=...
# ... up to GOOGLE_API_KEY_9
```

Responses are cached in `.llm_cache.json` to avoid redundant API calls across runs.

---

## Requirements

- Python 3.12+
- Google Gemini API key
- `crosshair-tool` (for S3; gracefully disabled if health-check fails)
- See `requirements.txt` for full dependency list

---

## Future Work

1. **Scale to 100+ Benchmark Tasks** — Widen from 15 core tasks to a comprehensive suite covering broader algorithmic domains.
2. **6-Operator Mutation Set** — Add `AddPrecondition`, `FlipLogic` (AND↔OR), and `WidenStrategies` for finer-grained localization.
3. **Multi-Language Porting** — Extend the AST mutation engine to Dafny and JML.
4. **GitHub Action Integration** — Package as a GitHub Action to automatically diagnose Hypothesis specs in PRs.
