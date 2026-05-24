<div align="center">

# SpecMutate

### Coverage-Guided Specification Repair for Property-Based Tests

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Hypothesis](https://img.shields.io/badge/Hypothesis-PBT-red?style=for-the-badge)](https://hypothesis.readthedocs.io/)
[![Accuracy](https://img.shields.io/badge/Diagnostic%20Accuracy-15%2F15%20%28100%25%29-brightgreen?style=for-the-badge)](docs/benchmark.md)
[![Repair](https://img.shields.io/badge/Repair%20Convergence-10%2F10%20%28100%25%29-brightgreen?style=for-the-badge)](docs/repair_loop.md)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

**SpecMutate** automatically diagnoses broken Hypothesis specs and repairs them — without knowing the answer in advance. Given a Python function and a property-based test that might be too weak or too strict, SpecMutate tells you *exactly* what is wrong and produces a corrected spec.

[Benchmark Results](#results) · [Architecture](#architecture) · [Quick Start](#quick-start) · [Documentation](docs/) · [Interactive Dashboard](#streamlit-dashboard)

</div>

---

## The Problem

Property-based testing with [Hypothesis](https://hypothesis.readthedocs.io/) requires writing specifications — `@given` decorators with strategies and `assert` statements. Getting these right is hard:

- **Underconstrained specs** are too weak: they pass wrong implementations, giving false confidence.
- **Overconstrained specs** are too strict: they reject correct implementations, making the test suite useless.

Debugging a broken spec manually means staring at failing tests and guessing what the spec *should* say. SpecMutate automates this diagnosis and repair.

---

## What SpecMutate Does

```
Input:  a Python function + a Hypothesis spec that might be broken

Output: ┌───────────────────────────────────────────────────────┐
        │  Verdict:    UNDERCONSTRAINED                         │
        │  Confidence: 0.80                                     │
        │  Reason:     S2=0.0 — spec cannot distinguish any     │
        │              implementation pair                      │
        │                                                       │
        │  Bad constraint: assert len(result) == len(a) + len(b)│
        │  Mutation:       RemovePostcondition (delta=3)        │
        │                                                       │
        │  Repaired spec:                                       │
        │    @given(lists, lists)                               │
        │    def test_merge(a, b):                              │
        │        result = merge_sorted_lists(a, b)              │
        │        assert result == sorted(a + b)  ← fixed        │
        └───────────────────────────────────────────────────────┘
```

---

## Results

| Metric | Score |
|--------|-------|
| **Diagnostic Accuracy** | **15 / 15 (100%)** |
| **Repair Convergence Rate** | **10 / 10 (100%)** |
| Benchmark size | 15 tasks: 5 underconstrained · 5 overconstrained · 5 correct |
| Average repair iterations | **1.1** |

### Confusion Matrix

| Predicted \ Actual | Underconstrained | Overconstrained | Correct |
|--------------------|:---------------:|:---------------:|:-------:|
| **Underconstrained** | ✅ 5 (T01–T05) | 0 | 0 |
| **Overconstrained** | 0 | ✅ 5 (T06–T10) | 0 |
| **Correct** | 0 | 0 | ✅ 5 (T11–T15) |

Zero misclassifications. See [docs/benchmark.md](docs/benchmark.md) for per-task breakdown and ablation study.

---

## Architecture

SpecMutate is a multi-component pipeline with four distinct analytical layers:

```
planted_spec + correct_impl + buggy_impls + description
        │
        ▼
┌───────────────────────┐    ┌───────────────────────┐
│     SIGNAL LAYER      │    │    MUTATION ENGINE     │
│                       │    │                       │
│  S1  Completeness     │    │  FlipComparison       │
│  S2  Discrimination   │    │  RemovePrecondition   │
│  S3  CrossHair (SMT)  │    │  RemovePostcondition  │
│  S4  Stability        │    │  Coverage-delta scored │
└──────────┬────────────┘    └──────────┬────────────┘
           │                            │
           └──────────┬─────────────────┘
                      ▼
        ┌─────────────────────────┐
        │    DIAGNOSIS ENGINE     │
        │   3-Tier Cascade        │
        │  Gate 1: impl fails?    │──→ overconstrained
        │  Gate 2: S2 == 0.0?    │──→ underconstrained
        │  Fusion: weighted score │──→ correct / under / over
        └─────────────┬───────────┘
                      ▼
        ┌─────────────────────────┐
        │     REPAIR LOOP         │
        │  Grounded LLM prompt    │
        │  Bad AST node + delta   │
        │  + counterexample       │
        │  + correct/buggy output │
        │  Max 3 iterations       │
        └─────────────────────────┘
```

### The Four Signals

| Signal | Measures | Weight |
|--------|----------|--------|
| **S1 Completeness** | Fraction of adversarial wrong implementations that the spec rejects | 0.35 |
| **S2 Discrimination** | Fraction of implementation pairs the spec can tell apart | 0.35 |
| **S3 CrossHair** | Whether symbolic execution finds a formal counterexample | 0.20 |
| **S4 Stability** | How consistently LLM re-generates the spec across 3 independent runs | 0.10 |

**Fusion formula:**
$$S_{under} = 0.35(1 - S_1) + 0.35(1 - S_2) + 0.20 \cdot S_3 + 0.10(1 - S_4)$$

### The 3-Tier Cascade

Rather than relying solely on the weighted fusion, SpecMutate uses deterministic gates that resolve ambiguous signal profiles:

1. **Gate 1** — Does the correct implementation *fail* the spec? → `overconstrained` (no weighting needed)
2. **Gate 2** — Is S2 = 0 (spec cannot discriminate anything)? → `underconstrained`
3. **Weighted Fusion** — For specs that pass both gates, the fusion decides `correct` vs others

Without the gates, fusion-only accuracy drops to 33.3%. Each gate independently recovers 5 tasks.

---

## Quick Start

### Prerequisites

- Python 3.11+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### Installation

```bash
# Clone the repo
git clone https://github.com/your-org/specmutate.git
cd specmutate

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Configure API Keys

```bash
# Copy the template
cp .env.example .env

# Edit .env and add your key(s)
GOOGLE_API_KEY=your_gemini_api_key_here
```

Multiple keys are supported for automatic rotation — see `.env.example` for the full format.

### Verify Your Setup

```bash
python check_api_keys.py
```

Expected output:
```
  Checking GOOGLE_API_KEY    ... [WORKING] (1.83s) - Responded: 'OK'
  Working keys:       1 / 1
```

### Run the Full Benchmark

```bash
python run_benchmark.py
```

Expected output:
```
Starting SpecMutate Full Benchmark Run (15 tasks)...
==================================================
Running pipeline on T01: merge_sorted_lists
Ground truth: underconstrained
Predicted: underconstrained | Ground truth: underconstrained | Correct: True
...
HEADLINE NUMBERS:
Diagnostic accuracy: 15/15 (100.0%)
Repair convergence: 10/10 (100.0%)
```

Results are saved to `results/benchmark_results.json`.

### Streamlit Dashboard

```bash
streamlit run app.py
```

Opens an interactive dashboard at `http://localhost:8501` showing:
- Per-task signal heatmaps
- Verdict decision paths
- Repair iteration history
- Full benchmark summary

---

## Repository Structure

```
specmutate/
├── README.md                  ← You are here
├── requirements.txt           ← Python dependencies
├── benchmark.json             ← 15-task benchmark dataset
├── .env.example               ← API key template
├── run_benchmark.py           ← Main entry point
├── check_api_keys.py          ← API health diagnostic
├── app.py                     ← Streamlit interactive dashboard
│
├── src/                       ← Core engine
│   ├── pipeline.py            ← Top-level orchestrator
│   ├── llm.py                 ← LLM gateway (key rotation, caching)
│   ├── runner.py              ← Subprocess Hypothesis runner
│   ├── diagnosis.py           ← 3-tier verdict cascade
│   ├── mutator.py             ← Coverage-guided mutation engine
│   ├── repair_loop.py         ← Feedback-guided LLM repair loop
│   ├── signal1.py             ← S1: Completeness score
│   ├── signal2.py             ← S2: Discrimination score
│   ├── signal3.py             ← S3: CrossHair symbolic refutation
│   ├── signal4.py             ← S4: Stability score
│   ├── spec_gen.py            ← LLM spec generation
│   ├── impl_gen.py            ← LLM implementation generation
│   └── templates.py           ← All LLM prompt templates
│
├── docs/                      ← Technical documentation
│   ├── architecture.md        ← System overview and data flow
│   ├── signals.md             ← Signal design and formulas
│   ├── diagnosis.md           ← Verdict cascade logic
│   ├── mutation_engine.md     ← AST mutation operators
│   ├── repair_loop.md         ← Repair loop with case studies
│   └── benchmark.md           ← Benchmark design and results
│
├── results/                   ← Benchmark output
│   └── benchmark_results.json
│
└── tests/                     ← Unit test suite
    ├── conftest.py
    ├── test_llm.py
    ├── test_mutator.py
    ├── test_pipeline.py
    ├── test_repair.py
    ├── test_runner.py
    ├── test_signal1.py
    ├── test_signal2.py
    ├── test_signal3.py
    ├── test_signal4.py
    └── test_spec_gen.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

The test suite includes unit tests for all signal computations, the mutation engine, the runner, and the repair loop. LLM-dependent tests use caching to avoid API quota consumption.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | Full pipeline walkthrough, module map, key design decisions |
| [Signals](docs/signals.md) | All four diagnostic signals explained in depth |
| [Diagnosis](docs/diagnosis.md) | 3-tier cascade, fusion formula, ablation evidence |
| [Mutation Engine](docs/mutation_engine.md) | AST operators, coverage delta scoring, examples |
| [Repair Loop](docs/repair_loop.md) | Feedback-guided repair, convergence criteria, case studies |
| [Benchmark](docs/benchmark.md) | Dataset design, results, oracle disclosure |

---

## Key Design Principles

**1. Grounded Repair, Not Blind Generation**  
The repair loop does not ask the LLM to "fix this spec." It identifies the exact AST node responsible for the fault, measures the coverage delta, extracts a counterexample, and provides all of this in a structured prompt. The LLM is told exactly what to fix and why.

**2. Subprocess Isolation**  
All Hypothesis and coverage.py operations run in separate subprocesses. This prevents state leakage between test runs and makes the system robust to malformed specs and implementations.

**3. Placeholder Substitution**  
Code is injected into templates via `###PLACEHOLDER###.replace()`, never via f-strings or `.format()`. Python source code contains `{curly braces}` that would corrupt string formatting.

**4. Deterministic Gates Before Probabilistic Fusion**  
The weighted fusion formula cannot resolve the fundamental ambiguity between underconstrained and overconstrained specs (both show S2 = 0.0). Deterministic gates that run the correct implementation against the spec resolve this unambiguously before any signal weighting occurs.

**5. Multi-Key LLM Resilience**  
The LLM layer supports up to 10 Gemini API keys with automatic rotation on quota exhaustion. When all keys exhaust on one model, it escalates to the next model in the rotation list. This makes long benchmark runs resilient to per-key rate limits.

---

## Contributing

See [AGENTS.md](AGENTS.md) for contributor guidelines, including instructions for extending the mutation operator set, adding new signals, and expanding the benchmark dataset.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
