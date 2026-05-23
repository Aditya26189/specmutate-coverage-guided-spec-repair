**Diagnostic Accuracy: 13/15 (86.7%) | Repair Convergence Rate: 8/8 (100.0%)**

# SpecMutate

> **Coverage-guided specification diagnosis and CEGIS repair for Python/Hypothesis property-based tests.**

SpecMutate automatically diagnoses whether a Hypothesis specification is *underconstrained*, *overconstrained*, or *correct* — then repairs broken specs using a counterexample-guided synthesis loop grounded in AST-level mutation and coverage delta analysis.

---

## Benchmark Results

| Metric | Score |
|--------|-------|
| Diagnostic Accuracy | **13 / 15 (86.7%)** |
| Repair Convergence Rate | **8 / 8 (100.0%)** |
| Benchmark Size | 15 tasks (5 underconstrained / 5 overconstrained / 5 correct) |
| Model | `gemini-2.5-flash` |

Full per-task results and ablation tables: [RESULTS.md](RESULTS.md)

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
     ┌─────────▼──────────┐
     │  correct_impl gate  │  ← primary overconstrained signal
     └─────────┬──────────┘
               │
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
     │  CEGIS Repair Loop  │  → repaired spec (max 3 iterations)
     └────────────────────┘
```

---

## Differentiator vs VeriAct

| | VeriAct | **SpecMutate** |
|--|---------|----------------|
| Language | Java/JML | Python/Hypothesis |
| Mutation target | Impl outputs | **Spec AST nodes** |
| Fault localization | ❌ Black-box | ✅ **AST node + coverage delta** |
| Repair | ❌ None | ✅ **CEGIS with grounded LLM context** |
| Overconstrained detection | ❌ No | ✅ **Deterministic gate** |

---

## Quickstart

```bash
# 1. Install dependencies
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Set your API keys in .env
echo "GOOGLE_API_KEY=your_key_here" > .env

# 3. Run the full benchmark
python run_benchmark.py

# 4. Launch the Streamlit dashboard
streamlit run app.py

# 5. Run the test suite
pytest
```

---

## Project Structure

```
specmutate/
├── src/
│   ├── llm.py          # Gemini 2.5 Flash client + key rotation + circuit breaker
│   ├── spec_gen.py     # Spec generation
│   ├── impl_gen.py     # Implementation generation
│   ├── runner.py       # Isolated Hypothesis subprocess runner
│   ├── signal1.py      # S1: Completeness
│   ├── signal2.py      # S2: Discrimination
│   ├── signal3.py      # S3: CrossHair symbolic refutation
│   ├── signal4.py      # S4: Stability
│   ├── mutator.py      # Coverage-guided mutation engine
│   ├── repair_loop.py  # CEGIS repair loop
│   ├── diagnosis.py    # Weighted signal fusion + verdict
│   └── pipeline.py     # End-to-end orchestration
├── tests/              # Full pytest suite (23 tests)
├── results/            # Benchmark results JSON
├── benchmark.json      # 15-task benchmark definition
├── templates.py        # LLM prompt templates
├── app.py              # Streamlit dashboard (Phase 13)
├── run_benchmark.py    # Benchmark runner script
├── RESULTS.md          # Full results + ablation
└── requirements.txt
```

---

## Requirements

- Python 3.12+
- Google Gemini API key (`gemini-2.5-flash`)
- See `requirements.txt` for full dependency list
