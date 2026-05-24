**Diagnostic Accuracy and Repair Convergence:** See [results/benchmark_results.json](results/benchmark_results.json)

# SpecMutate

> **Coverage-guided specification diagnosis and feedback-guided LLM repair for Python/Hypothesis property-based tests.**

SpecMutate automatically diagnoses whether a Hypothesis specification is *underconstrained*, *overconstrained*, or *correct* — then repairs broken specs using a feedback-guided repair loop grounded in AST-level mutation and coverage delta analysis.

---

## Benchmark Results

```
Diagnostic Accuracy:  15/15 (100.0%)
Repair Convergence:   10/10 (100%) — all non-correct tasks repaired
S3 (CrossHair):       Non-functional in evaluation environment (S3=0.0 for all 15 tasks)
S4 (Stability):       Near-constant signal (0.5 or 1.0) — low discriminative value
```

| Metric | Score |
|--------|-------|
| Diagnostic Accuracy | 15/15 (100.0%) |
| Repair Convergence Rate | 10/10 (100%) |
| Average Iterations to Convergence | 1.1 |
| Benchmark Size | 15 tasks (5 underconstrained / 5 overconstrained / 5 correct) |
| LLM Backend | Gemini (model rotation list: 2.5-flash, 3-flash-preview, 3.5-flash; default 3.5-flash) |

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
 │     S2 (Discrimination, w=0.35) — impl pair testing  │
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
     │ LLM Repair Loop    │  → repaired spec (max 3 iters)
     └────────────────────┘
```

---

## Differentiator vs SOTA

| Dimension | VeriAct (arXiv:2604.00280) | SpecRL [2604.05820] | VeriSpecGen [2604.10392] | **SpecMutate** |
|-----------|----------------------------|---------------------|--------------------------|----------------|
| Target Language | Java/JML | Dafny | Lean 4 | **Python/Hypothesis** |
| Infrastructure | JVM + JML toolchain | RL training pipeline | Lean ITP | **Standard Python subprocesses** |
| Fault localization | ❌ Black-box | ❌ Black-box | ❌ Black-box | ✅ **AST node + coverage delta** |
| Repair | ❌ None | ❌ None | ❌ None | ✅ **feedback-guided LLM** |
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
│   ├── llm.py          # Gemini client · model rotation · key rotation · circuit breaker
│   ├── spec_gen.py     # Spec generation from task description
│   ├── impl_gen.py     # Buggy implementation generation (S1 harness)
│   ├── runner.py       # Isolated Hypothesis subprocess runner
│   ├── signal1.py      # S1: Completeness — fraction of buggy impls rejected
│   ├── signal2.py      # S2: Discrimination — correct/buggy pair separation
│   ├── signal3.py      # S3: CrossHair symbolic refutation (health-check gated)
│   ├── signal4.py      # S4: Stability — spec variance at temperature=0.7
│   ├── mutator.py      # Coverage-guided AST mutation engine
│   ├── repair_loop.py  # feedback-guided repair loop (max 3 iterations, no fallback)
│   ├── diagnosis.py    # Weighted signal fusion + verdict (Gates 1 & 2 + fusion)
│   └── pipeline.py     # End-to-end orchestration
├── tests/              # Full pytest suite (32 tests)
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

## Architecture — Deterministic Cascade with LLM-Augmented Disambiguation

SpecMutate classifies specs using a 3-tier cascade. Earlier tiers are deterministic
and computationally cheap; the fusion tier activates only for ambiguous cases.

Tier 1 — Deterministic Overconstrained Gate
  Run the correct reference implementation against the spec.
  If the reference implementation fails the spec → classify as OVERCONSTRAINED.
  Cost: zero API calls. Handles 5/15 benchmark tasks (T06–T10).

Tier 2 — Zero-Discrimination Underconstrained Guard
  If S2 = 0.0 AND S1 < 0.9 (no buggy impl fails, no pair distinguishable)
  → classify as UNDERCONSTRAINED.
  Handles 5/15 benchmark tasks (T01–T05).

> **Transparency note:** In this 15-task benchmark, Gates 1 and 2 resolve 10/15 tasks.
> The weighted fusion formula is only active for the remaining 5 `correct` tasks (T11–T15).
> See RESULTS.md for full ablation analysis.

Tier 3 — Weighted Signal Fusion (ambiguous cases only)
  Combines four signals for cases not resolved by Tiers 1–2.
  Active for 5/15 benchmark tasks (T11–T15).
  
  Fusion Score = 0.35 * (1 - S1) + 0.35 * (1 - S2) + 0.20 * S3 + 0.10 * (1 - S4)
  Where:
    - Score > 0.65 -> underconstrained
    - Score < 0.45 -> correct
    - Middle band: use S3 + heuristics

Signal definitions:
  S1 (weight 0.35): Fraction of 5 LLM-generated buggy implementations rejected by spec
  S2 (weight 0.35): Fraction of divergent implementation pairs distinguished by spec  
  S3 (weight 0.20): CrossHair symbolic execution — counterexample found (1.0) or not (0.0)
  S4 (weight 0.10): Stability — agreement across 3 LLM spec regenerations at temp=0.7

---

## API Key & Model Configuration

SpecMutate supports up to 10 API keys with round-robin rotation. Models are tried in this order (see `src/llm.py` for the active index):

```python
MODEL_ROTATION_LIST = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
]
```

Configure in `.env`:
```
GOOGLE_API_KEY=...
GOOGLE_API_KEY_1=...
# ... up to GOOGLE_API_KEY_9
```

Responses are cached in `.llm_cache.json` to avoid redundant API calls across runs. Repair calls are run without cache for audit clarity.

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
