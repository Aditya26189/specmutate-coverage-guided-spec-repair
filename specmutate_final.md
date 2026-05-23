# SPECMUTATE — MASTER AI AGENT INSTRUCTION PROMPT
### Read this entire document before writing a single line of code.
### This is your harness. Every decision is locked. Every phase has an exit condition.

---

> **STATUS: ALL 11 FIXES APPLIED — THIS IS THE FINAL AGENT PROMPT.**
> Every code block below is correct as written. Do NOT re-introduce old broken versions.
>
> **Pre-existing Bug Fixes (v2 baseline):**
> - Bug 1 (repair_loop.py): REPAIR_PROMPT format keys now match template — `s1_score=`, `s2_score=`, `s4_score=`
> - Bug 2 (runner.py): placeholder replacement (`###IMPL_CODE###`) instead of `.format()` — safe for dicts/f-strings
> - Bug 3 (signal1.py): `compute_completeness_score` returns `float` not tuple; `compute_s1()` wrapper returns `{"score": float, "counterexamples": list}`
> - Bug 4 (mutator.py): `_measure_coverage` rewritten with `_COVERAGE_TEMPLATE` + placeholder substitution — consistent with runner.py
> - Bug 5 (diagnosis.py): `compute_verdict()` accepts `mutation_result` kwarg for secondary overconstrained detection
>
> **Additional Fixes (SPECMUTATE_FIXES_FINAL.md — all 11 applied):**
> - Fix 1 (requirements.txt): CrossHair floors raised — `crosshair-tool>=0.0.102`, `hypothesis-crosshair>=0.0.27`
> - Fix 2 (test_mutator.py): Import `score_by_coverage_delta` → `identify_bad_constraint` (was hard ImportError at pytest collection)
> - Fix 6 (repair_loop.py + pipeline.py): Binary verdict guess `s1<0.5?under:over` removed; `verdict` param added, pipeline passes `predicted`
> - Fix 7 (Section 1.8): CoverAssert — real DATE 2026 paper on SystemVerilog, not fabricated; corrected description
> - Fix 8 (Section 1.7): VeriAct differentiator sharpened with two-level differentiation (output mutation vs AST, Java/JML vs Python/Hypothesis)
> - Fix 9 (README template): Full SOTA comparison table — VeriSpecGen, SpecRL, AutoSpec, CoverUp all cited with gap analysis
> - Fix 10 (signal4.py + pipeline.py): S4 now uses `correct_impl` as second test impl — without it, S4 = constant 1.0 for every task
> - Fix 11 (diagnosis.py + pipeline.py): Primary overconstrained check via `correct_impl_passes` added before mutation-based secondary check

> **API KEY ROTATION — IMPORTANT:**
> Place up to 10 Gemini API keys in your `.env` file:
> ```
> GOOGLE_API_KEY=your_primary_key_here
> GOOGLE_API_KEY_1=your_second_key_here
> GOOGLE_API_KEY_2=your_third_key_here
> ...
> GOOGLE_API_KEY_9=your_tenth_key_here
> ```
> Only `GOOGLE_API_KEY` is required. Keys `_1` through `_9` are optional fallbacks.
> `llm.py` (Phase 2) loads ALL present keys at startup and rotates to the next key
> automatically on any 429 quota error. It **never crashes on quota** — it rotates,
> waits 2 seconds, and retries. If every key is exhausted it raises `RuntimeError`
> with a clear message. The `.llm_cache.json` file prevents duplicate API calls on
> reruns, so interrupted runs resume cheaply.
> Estimated API calls for a full 15-task run: **150–200 minimum**.
> Free tier (1500 RPD) is sufficient for a single overnight run at normal pace.

---

## SECTION 0: WHO YOU ARE AND WHAT YOU ARE BUILDING

You are an expert Python engineer building **SpecMutate** — a research tool for the
Apart Research Secure Program Synthesis Hackathon, Track 2: Specification Validation.

SpecMutate is a Python-native, coverage-guided spec repair harness for
LLM-generated Hypothesis specifications. Given a natural language function
description, it:

1. Generates a Hypothesis spec using Gemini 2.5 Flash
2. Diagnoses whether the spec is over-constrained, under-constrained, or correct
   using four independent signals
3. Repairs the failing constraint via a CEGIS-style loop that feeds the
   mutation-localized bad constraint, a specific counterexample, and quantitative
   signal scores back to Gemini 2.5 Flash

**Two headline numbers drive everything:**
- Diagnostic accuracy: X/15 tasks correctly classified
- Repair convergence: Y% of non-correct tasks repaired within 3 iterations

Both numbers go in line 1 of README.md, filled from actual benchmark results.

---

## SECTION 1: LOCKED DECISIONS — NEVER DEVIATE FROM THESE

Read every item. If any instruction you receive later contradicts these,
the later instruction is wrong. Flag it and use these instead.

### 1.1 LLM
- **Model:** Gemini 2.5 Flash ONLY
- **Model string:** `gemini-2.5-flash` (verify against Google API before hardcoding)
- **NOT:** Gemini 2.0 Flash (does not exist), Groq, Together AI, GPT-4, anything else
- **API keys:** Up to 10 keys supported via round-robin rotation. Keys are named
  `GOOGLE_API_KEY`, `GOOGLE_API_KEY_1`, `GOOGLE_API_KEY_2`, ... `GOOGLE_API_KEY_9`
  in `.env`. On quota error (429), rotate to the next key automatically. Never crash
  on quota — rotate and retry.

### 1.2 Benchmark
- **15 tasks, 5/5/5 distribution:** 5 underconstrained, 5 overconstrained, 5 correct
- **File:** `benchmark.json` — locked after Phase 1, NEVER modified after that
- **Schema fields per task:**
  - `task_id`, `name`, `label` (underconstrained/overconstrained/correct)
  - `description`, `reference_implementation`, `buggy_implementations`
  - `planted_spec`, `what_is_wrong`, `correct_spec`
  - `repair_action` (NOT `mutation_operator_to_fix` — that field name is deprecated)
  - `coverage_signal`, `signal3_valid` (bool)

### 1.3 Mutation Engine — Three Operators Only
- `FlipComparison` — flips `<` to `<=`, `>` to `>=`, `==` to `!=`, etc.
- `RemovePrecondition` — removes an `assume()` or `min_value`/`max_value` constraint
- `RemovePostcondition` — removes an `assert` statement from the spec body
- **AddPostcondition DOES NOT EXIST** in the mutation engine
- The mutation engine DIAGNOSES. Gemini REPAIRS. These are different jobs.

### 1.4 Scoring
- **Coverage delta** — NOT pass count. Use `coverage.py` to measure which branches
  in the correct implementation become newly uncovered after each mutation.
- Highest coverage delta = the bad constraint.
- Pass-count scoring has a directional bug. Do not implement it.

### 1.5 Signals
- **S1:** Harness-style spectest completeness (invariant checkers, not static pairs)
- **S2:** Oracle-guided variant discrimination (input-guided divergence prompting)
- **S3:** CrossHair symbolic refutation (health-check gate, 5 tasks max, may be N/A)
- **S4:** Spec stability (3 generations at T=0.7, agreement rate)
- **Fusion:** Weighted fusion — weights S1=0.35, S2=0.35, S3=0.20, S4=0.10
- **NO Bayesian framing. NO P=0.65 prior.** Weighted majority vote only.

### 1.6 CrossHair Packages — Two Separate Packages
- `crosshair-tool` (currently v0.0.104) — standalone symbolic checker
- `hypothesis-crosshair` (currently v0.0.27) — Hypothesis backend integration
- Install both. Import them separately. Never conflate them.

### 1.7 Key Differentiator — Say This Exactly
VeriAct (arXiv:2604.00280) uses a Spec-Harness that mutates implementation
OUTPUTS to detect whether a spec is weak, but cannot localize WHICH specific
AST constraint in the spec is wrong. SpecMutate's mutation engine applies
operators directly to the spec's AST nodes and uses coverage delta to identify
the specific bad constraint. That localization grounds the repair prompt: instead
of "the spec is weak, fix it," Gemini receives the exact AST node, the coverage
delta, and a concrete Hypothesis counterexample. VeriAct targets JML/Java with
OpenJML infrastructure. SpecMutate targets Python/Hypothesis with zero formal
verification tooling.

### 1.8 Deprecated — Never Use These
- Gemini 2.0 Flash
- CoverAssert (arXiv:2604.06607, DATE 2026) — real paper, wrong domain.
  It covers iterative SystemVerilog assertion generation for IC hardware
  verification. Do NOT cite as Python spec precedent. SpecMutate adapts
  the coverage-feedback principle to the Python/Hypothesis domain.
- OGHarn as citation for impl generation — OGHarn is C API fuzzing, wrong domain
- `mutation_operator_to_fix` field name — use `repair_action`
- AddPostcondition operator
- Bayesian fusion with P=0.65 prior
- 300,000 scenarios (real number is 70,000+)
- 78.23% → 82.03% accuracy numbers (unverifiable)

---

## SECTION 2: REPOSITORY STRUCTURE

Create this structure before writing any module code:

```
specmutate/
├── AGENTS.md                    ← 500-word summary of Section 1 for future sessions
├── README.md                    ← Two headline numbers in line 1 (fill after Phase 11)
├── RESULTS.md                   ← Ablation table, filled after Phase 11
├── benchmark.json               ← Locked after Phase 1
├── requirements.txt             ← All dependencies pinned
├── run_checks.sh                ← black + pylint + pytest, run after every change
├── .env.example                 ← GEMINI_API_KEY=your_key_here
├── .gitignore                   ← .env, __pycache__, .hypothesis, htmlcov
├── templates.py                 ← REPAIR_PROMPT string constant
├── src/
│   ├── __init__.py
│   ├── llm.py                   ← Gemini 2.5 Flash wrapper
│   ├── spec_gen.py              ← NL → Hypothesis spec
│   ├── impl_gen.py              ← Spec → 5 divergent implementations
│   ├── runner.py                ← Hypothesis runner (subprocess isolation)
│   ├── signal1.py               ← Spectest completeness
│   ├── signal2.py               ← Variant discrimination
│   ├── signal3.py               ← CrossHair (with health-check gate)
│   ├── signal4.py               ← Spec stability
│   ├── mutator.py               ← Coverage-guided mutation engine
│   ├── repair_loop.py           ← CEGIS-style repair
│   ├── diagnosis.py             ← Weighted signal fusion → verdict
│   └── pipeline.py              ← Full end-to-end orchestration
├── tests/
│   ├── test_llm.py
│   ├── test_runner.py
│   ├── test_signal1.py
│   ├── test_signal2.py
│   ├── test_signal3.py
│   ├── test_signal4.py
│   ├── test_mutator.py
│   ├── test_repair.py
│   └── test_pipeline.py
├── app.py                       ← Streamlit demo
└── results/
    ├── benchmark_results.json   ← Raw results from Phase 11
    └── ablation.json            ← Signal ablation data
```

---

## SECTION 3: TEMPLATES.PY — WRITE THIS FIRST, BEFORE ANY OTHER CODE

This file must exist before Phase 10. Write it in Phase 0.

```python
# templates.py
# Repair prompt template — grounded CEGIS-style repair
# DO NOT modify this string without updating AGENTS.md

REPAIR_PROMPT = """You are repairing a Python Hypothesis specification that has been \
diagnosed as {verdict}.

TASK DESCRIPTION: {task_description}

CURRENT (BROKEN) SPEC:
{current_spec}

DIAGNOSIS:
- Verdict: {verdict}
- S1 Completeness Score: {s1_score:.2f} (low = spec accepts wrong outputs)
- S2 Discrimination Score: {s2_score:.2f} (low = spec cannot distinguish implementations)
- S4 Stability Score: {s4_score:.2f} (low = spec is inconsistent across generations)

BAD CONSTRAINT IDENTIFIED BY MUTATION ENGINE:
AST node: {bad_ast_node}
Operator applied: {mutation_operator}
Coverage delta from this mutation: {coverage_delta:.4f}

COUNTEREXAMPLE INPUT that revealed the spec failure:
{counterexample}

WHAT THE CORRECT IMPLEMENTATION RETURNS ON THIS INPUT:
{correct_output}

WHAT THE BUGGY IMPLEMENTATION RETURNS ON THIS INPUT (that the spec incorrectly accepted):
{buggy_output}

YOUR TASK:
Return ONLY a corrected Python Hypothesis spec. The spec must:
1. Import from hypothesis correctly
2. Use @given decorator with st strategies
3. Contain at least one assert statement stronger than the current spec
4. Be runnable with: exec(spec_string) then hypothesis.core.find()
5. NOT contain markdown fences, explanations, or comments

CORRECTED SPEC:"""


SPEC_GEN_PROMPT = """Generate a Python Hypothesis property-based test specification \
for the following function.

FUNCTION DESCRIPTION: {description}

Requirements:
- Use `from hypothesis import given, settings, assume` and `from hypothesis import strategies as st`
- The function under test is named `{function_name}`
- Include at least one @given decorator with appropriate strategies
- Include at least two assert statements checking postconditions
- Include assume() statements for any necessary preconditions
- Do NOT implement the function itself
- Do NOT include markdown fences or explanations

Return ONLY the Python test function code."""


IMPL_GEN_PROMPT = """Generate {n} different Python implementations of the following \
function. The implementations should be meaningfully different — use different \
algorithms, data structures, or approaches.

FUNCTION DESCRIPTION: {description}
FUNCTION SIGNATURE: {signature}

ORACLE INPUTS (inputs that a correct Hypothesis spec generates — your implementations
MUST disagree on at least some of these):
{oracle_inputs}

Requirements:
- Each implementation must have the exact function signature shown
- Implementations should intentionally vary in correctness — some may be buggy
- Return as a JSON array of strings, each string being one complete Python function
- Do NOT include markdown fences

JSON ARRAY OF IMPLEMENTATIONS:"""


COVERAGE_REPAIR_CONTEXT = """Additional context for repair:
Uncovered branches in the correct implementation under the current spec:
{uncovered_branches}

These branches being uncovered means the spec's input strategy is too narrow
(overconstrained precondition) or the postcondition fails to exercise these paths."""
```

---

## SECTION 4: PHASE-BY-PHASE EXECUTION PLAN

### PHASE 0: Repository Bootstrap (30 minutes)
**Do this before any other phase.**

```bash
# Commands to run:
mkdir specmutate && cd specmutate
git init
git remote add origin https://github.com/YOUR_USERNAME/specmutate.git

# Create .gitignore
cat > .gitignore << 'EOF'
.env
__pycache__/
*.pyc
.hypothesis/
htmlcov/
.coverage
*.egg-info/
dist/
build/
.pytest_cache/
EOF

# Create .env.example
cat > .env.example << 'EOF'
GOOGLE_API_KEY=your_primary_key_here
GOOGLE_API_KEY_1=your_second_key_here
GOOGLE_API_KEY_2=your_third_key_here
GOOGLE_API_KEY_3=your_fourth_key_here
GOOGLE_API_KEY_4=your_fifth_key_here
GOOGLE_API_KEY_5=your_sixth_key_here
GOOGLE_API_KEY_6=your_seventh_key_here
GOOGLE_API_KEY_7=your_eighth_key_here
GOOGLE_API_KEY_8=your_ninth_key_here
GOOGLE_API_KEY_9=your_tenth_key_here
EOF
# Only GOOGLE_API_KEY is required. _1 through _9 are optional.
# llm.py rotates through all present keys on 429 quota errors.

# Create requirements.txt
cat > requirements.txt << 'EOF'
google-generativeai>=0.8.0
hypothesis>=6.100.0
crosshair-tool>=0.0.102
hypothesis-crosshair>=0.0.27
coverage>=7.4.0
pytest>=8.0.0
pytest-timeout>=2.3.0
black>=24.0.0
pylint>=3.0.0
streamlit>=1.35.0
python-dotenv>=1.0.0
EOF

pip install -r requirements.txt

# Write templates.py (copy exact content from Section 3 above)
# Write AGENTS.md (500-word summary of Section 1)
# Create all directory structure from Section 2

# Verify Gemini 2.5 Flash works:
python -c "
import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash')
print(model.generate_content('say hello').text)
"
# If this fails: STOP. Fix the API key and model string before continuing.

git add -A
git commit -m "Phase 0: Repository bootstrap, templates, AGENTS.md"
git push -u origin main
```

**EXIT CONDITION:** `python -c "import google.generativeai; print('OK')"` runs.
Gemini 2.5 Flash responds to a test prompt. Directory structure exists.

---

### PHASE 1: Benchmark JSON (45 minutes)
**Lock the ground truth. Never touch benchmark.json after this phase.**

Create `benchmark.json` with exactly 15 tasks in 5/5/5 distribution.

**UNDERCONSTRAINED tasks (5): T01, T02, T03, T04, T05**
Each must have:
- At least one buggy implementation with `why_it_passes_bad_spec` documented
- A planted spec that is too weak (missing postcondition)
- A correct spec that catches the buggy implementations

T01: merge_sorted_lists — planted spec only checks length
T02: binary_search — planted spec only bounds return value
T03: remove_duplicates — planted spec only checks uniqueness, not order
T04: rotate_list — planted spec only checks length
T05: flatten_nested — planted spec only checks total length

**OVERCONSTRAINED tasks (5): T06, T07, T08, T09, T10**
Each must have:
- NO buggy implementations (correct impls fail the overconstrained spec)
- A planted spec that excludes valid inputs via precondition
- A correct spec that widens the input space

T06: factorial — precondition excludes n=0 AND postcondition result>n fails for n=1,2
T07: gcd — precondition excludes zero inputs (gcd(0,n)=n is valid)
T08: is_palindrome — restricts to lowercase alpha only, excludes empty strings
T09: clamp — assume(lo<=x<=hi) guts the test (never tests clamping cases)
T10: string_palindrome_check — precondition min_size=2 excludes empty string edge case

**CORRECT tasks (5): T11, T12, T13, T14, T15**
Each must have:
- NO buggy implementations
- A spec that is tight and complete
- `what_is_wrong: "Nothing. This spec is correct."`

T11: sum_list — assert result == sum(lst)
T12: max_of_list — assert result in lst AND all(x<=result for x in lst)
T13: has_duplicates — assert result == (len(lst) != len(set(lst)))
T14: is_sorted — assert result == all(a<=b for a,b in zip(lst,lst[1:]))
T15: absolute_value — assert result == abs(x) AND result >= 0

**VALIDATION SCRIPT — run after writing benchmark.json:**
```python
import json
with open('benchmark.json') as f:
    data = json.load(f)
tasks = data['benchmark']['tasks']
assert len(tasks) == 15, f"Expected 15, got {len(tasks)}"
labels = [t['label'] for t in tasks]
assert labels.count('underconstrained') == 5
assert labels.count('overconstrained') == 5
assert labels.count('correct') == 5
for t in tasks:
    assert 'repair_action' in t, f"{t['task_id']} missing repair_action"
    assert 'mutation_operator_to_fix' not in t, f"{t['task_id']} has deprecated field"
    assert 'coverage_signal' in t
    assert 'signal3_valid' in t
print("benchmark.json: ALL CHECKS PASSED")
```

```bash
python validate_benchmark.py
git add benchmark.json validate_benchmark.py
git commit -m "Phase 1: Locked benchmark.json — 5/5/5 distribution, 15 tasks"
git push
```

**EXIT CONDITION:** Validation script prints ALL CHECKS PASSED. Commit is pushed.

---

### PHASE 2: LLM Layer (45 minutes)
**Write the tests first. Then write the code until tests pass.**

**Write `tests/test_llm.py` first:**
```python
import time, pytest
from src.llm import call_llm, clear_cache, strip_fences, _load_api_keys

def test_api_keys_loaded():
    """At least one API key must be present."""
    keys = _load_api_keys()
    assert len(keys) >= 1
    assert all(isinstance(k, str) and len(k) > 10 for k in keys)

def test_fence_stripping():
    """LLM response with markdown fences must return clean code."""
    raw = "```python\ndef foo():\n    return 1\n```"
    result = strip_fences(raw)
    assert "```" not in result
    assert "def foo():" in result

def test_cache_hit_is_fast():
    """Second call with same prompt must return in under 0.5 seconds."""
    clear_cache()
    prompt = "Return the number 42. Nothing else."
    call_llm(prompt)  # warm the cache
    start = time.time()
    call_llm(prompt)  # should hit cache
    elapsed = time.time() - start
    assert elapsed < 0.5, f"Cache hit took {elapsed:.2f}s — too slow"

def test_returns_string():
    prompt = "Return the word hello. Nothing else."
    result = call_llm(prompt)
    assert isinstance(result, str)
    assert len(result) > 0

def test_rate_limiter_allows_calls():
    """Three sequential calls must all succeed without exception."""
    for i in range(3):
        result = call_llm(f"Return the number {i}. Nothing else.")
        assert isinstance(result, str)
```

**Now write `src/llm.py`:**
```python
# src/llm.py
# FIX APPLIED: API key rotation on 429 quota errors
# Keys loaded from .env: GOOGLE_API_KEY, GOOGLE_API_KEY_1 ... GOOGLE_API_KEY_9
# Round-robin rotation — never crashes on quota, rotates and retries automatically

import os, time, hashlib, json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"
CACHE_FILE = Path(".llm_cache.json")
MIN_CALL_INTERVAL = 1.0  # seconds between calls (rate limit safety)
MAX_RETRIES = 3           # retries per call before giving up

# --- API key rotation ---
def _load_api_keys() -> list[str]:
    """Load all available API keys from environment. Primary key first."""
    keys = []
    primary = os.getenv("GOOGLE_API_KEY")
    if primary:
        keys.append(primary)
    for i in range(1, 10):
        k = os.getenv(f"GOOGLE_API_KEY_{i}")
        if k:
            keys.append(k)
    if not keys:
        raise RuntimeError(
            "No API key found. Set GOOGLE_API_KEY in .env"
        )
    return keys

_api_keys: list[str] = _load_api_keys()
_current_key_index: int = 0
_cache: dict = {}
_last_call_time: float = 0.0


def _get_current_key() -> str:
    return _api_keys[_current_key_index]


def _rotate_key() -> str:
    """Rotate to the next available key. Returns the new key."""
    global _current_key_index
    _current_key_index = (_current_key_index + 1) % len(_api_keys)
    new_key = _api_keys[_current_key_index]
    print(f"[llm] Rotated to API key index {_current_key_index}")
    return new_key


def _load_cache() -> None:
    global _cache
    if CACHE_FILE.exists():
        try:
            _cache = json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            _cache = {}


def _save_cache() -> None:
    CACHE_FILE.write_text(json.dumps(_cache, indent=2))


def clear_cache() -> None:
    global _cache
    _cache = {}
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()


def strip_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def call_llm(
    prompt: str,
    temperature: float = 0.0,
    use_cache: bool = True,
    strip_markdown: bool = True,
) -> str:
    global _last_call_time
    _load_cache()

    cache_key = hashlib.md5(f"{prompt}|{temperature}".encode()).hexdigest()

    if use_cache and cache_key in _cache:
        return _cache[cache_key]

    # Rate limiting
    elapsed = time.time() - _last_call_time
    if elapsed < MIN_CALL_INTERVAL:
        time.sleep(MIN_CALL_INTERVAL - elapsed)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            genai.configure(api_key=_get_current_key())
            model = genai.GenerativeModel(MODEL_NAME)
            config = genai.types.GenerationConfig(temperature=temperature)
            response = model.generate_content(prompt, generation_config=config)
            result = response.text
            _last_call_time = time.time()

            if strip_markdown:
                result = strip_fences(result)

            if use_cache:
                _cache[cache_key] = result
                _save_cache()

            return result

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            # 429 = quota exceeded, rotate key and retry immediately
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                print(f"[llm] Quota hit on key {_current_key_index}, rotating...")
                _rotate_key()
                time.sleep(2)  # brief pause before retry with new key
                continue
            # Other errors: wait and retry with same key
            print(f"[llm] API error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(5 * (attempt + 1))

    raise RuntimeError(
        f"Gemini 2.5 Flash failed after {MAX_RETRIES} attempts "
        f"across {len(_api_keys)} key(s). Last error: {last_error}"
    )
```

```bash
pytest tests/test_llm.py -v
# ALL 4 TESTS MUST PASS before continuing
git add src/llm.py tests/test_llm.py
git commit -m "Phase 2: llm.py — Gemini 2.5 Flash wrapper with cache, rate limit, fence stripping"
git push
```

**EXIT CONDITION:** All 4 tests in test_llm.py pass. No test is skipped.

---

### PHASE 3: Spec + Impl Generation (60 minutes)

**Write `tests/test_spec_gen.py` first:**
```python
from src.spec_gen import generate_spec
from src.impl_gen import generate_implementations
import json

def test_spec_gen_returns_valid_python():
    spec = generate_spec(
        description="Return the sum of all integers in a list.",
        function_name="sum_list"
    )
    assert "@given" in spec
    assert "def test_" in spec
    assert "assert" in spec
    assert "```" not in spec  # no fences

def test_impl_gen_returns_five_implementations():
    impls = generate_implementations(
        description="Return the sum of all integers in a list.",
        signature="def sum_list(lst: list) -> int:",
        oracle_inputs=["[]", "[1,2,3]", "[0]", "[-1,1]", "[100]"]
    )
    assert len(impls) == 5
    for impl in impls:
        assert "def sum_list" in impl
        assert "```" not in impl

def test_impl_gen_produces_divergent_impls():
    impls = generate_implementations(
        description="Return the reverse of a string.",
        signature="def string_reverse(s: str) -> str:",
        oracle_inputs=["'hello'", "'abc'", "''", "'a'"]
    )
    # Not all implementations should be identical
    assert len(set(impls)) > 1
```

**Write `src/spec_gen.py`:**
```python
# src/spec_gen.py
from src.llm import call_llm
from templates import SPEC_GEN_PROMPT

def generate_spec(description: str, function_name: str, temperature: float = 0.0) -> str:
    prompt = SPEC_GEN_PROMPT.format(
        description=description,
        function_name=function_name
    )
    return call_llm(prompt, temperature=temperature)
```

**Write `src/impl_gen.py`:**
```python
# src/impl_gen.py
import json
from src.llm import call_llm
from templates import IMPL_GEN_PROMPT

def generate_implementations(
    description: str,
    signature: str,
    oracle_inputs: list[str],
    n: int = 5
) -> list[str]:
    prompt = IMPL_GEN_PROMPT.format(
        n=n,
        description=description,
        signature=signature,
        oracle_inputs="\n".join(oracle_inputs)
    )
    raw = call_llm(prompt, temperature=0.8)
    try:
        impls = json.loads(raw)
        return [str(impl) for impl in impls[:n]]
    except json.JSONDecodeError:
        # Fallback: split by double newline if JSON fails
        blocks = [b.strip() for b in raw.split("\n\n") if "def " in b]
        return blocks[:n]
```

```bash
pytest tests/test_spec_gen.py -v
git add src/spec_gen.py src/impl_gen.py tests/test_spec_gen.py templates.py
git commit -m "Phase 3: spec_gen.py and impl_gen.py — Gemini-powered spec and implementation generation"
git push
```

**EXIT CONDITION:** All 3 tests pass. Manually inspect output — spec must look like
a valid Hypothesis test with @given, assert, and no markdown.

---

### PHASE 4: Hypothesis Runner (60 minutes)
**CRITICAL: Use subprocess isolation. Do NOT call Hypothesis inline.**

**Write `tests/test_runner.py` first:**
```python
from src.runner import run_spec_against_impl

def test_buggy_impl_passes_weak_spec():
    """Identity bug passes underconstrained spec."""
    weak_spec = '''
from hypothesis import given, strategies as st
@given(st.text(max_size=20))
def test_string_reverse(s):
    result = string_reverse(s)
    assert len(result) == len(s)
    assert sorted(result) == sorted(s)
'''
    buggy_impl = "def string_reverse(s): return s"
    result = run_spec_against_impl(spec=weak_spec, impl=buggy_impl)
    assert result["passed"] is True
    assert result["counterexample"] is None

def test_correct_spec_catches_buggy_impl():
    """Strong spec catches the identity bug."""
    strong_spec = '''
from hypothesis import given, strategies as st
@given(st.text(max_size=20))
def test_string_reverse(s):
    result = string_reverse(s)
    assert result == s[::-1]
'''
    buggy_impl = "def string_reverse(s): return s"
    result = run_spec_against_impl(spec=strong_spec, impl=buggy_impl)
    assert result["passed"] is False
    assert result["counterexample"] is not None

def test_correct_impl_passes_correct_spec():
    """Correct impl must pass the correct spec."""
    strong_spec = '''
from hypothesis import given, strategies as st
@given(st.text(max_size=20))
def test_string_reverse(s):
    result = string_reverse(s)
    assert result == s[::-1]
'''
    correct_impl = "def string_reverse(s): return s[::-1]"
    result = run_spec_against_impl(spec=strong_spec, impl=correct_impl)
    assert result["passed"] is True
```

**Write `src/runner.py`:**
```python
# src/runner.py
# SUBPROCESS ISOLATION — do not call Hypothesis inline.
# FIX APPLIED: use placeholder replacement instead of .format() to avoid
# KeyError when impl or spec contain curly braces (dicts, f-strings, etc.)

import subprocess, sys, tempfile, json
from pathlib import Path


# Use unique placeholders that CANNOT appear in Python source code.
# Never use .format() on code strings — they may contain {curly braces}.
RUNNER_TEMPLATE = '''
import json, sys
from hypothesis import given, settings, assume, strategies as st, HealthCheck

###IMPL_CODE###

###SPEC_CODE###

if __name__ == "__main__":
    try:
        import inspect
        test_fn = None
        for name, obj in list(globals().items()):
            if name.startswith("test_") and callable(obj):
                test_fn = obj
                break
        if test_fn is None:
            print(json.dumps({"passed": False, "error": "No test function found",
                               "counterexample": None}))
            sys.exit(1)
        test_fn()
        print(json.dumps({"passed": True, "counterexample": None, "error": None}))
    except Exception as e:
        msg = str(e)
        counterexample = None
        if "Falsifying example" in msg:
            counterexample = msg
        print(json.dumps({"passed": False, "counterexample": counterexample,
                           "error": msg}))
'''


def run_spec_against_impl(
    spec: str,
    impl: str,
    timeout: int = 30
) -> dict:
    """
    Run a Hypothesis spec against an implementation in a subprocess.
    Returns: {"passed": bool, "counterexample": str|None, "error": str|None}
    Uses placeholder replacement — safe for impls containing {}, f-strings, dicts.
    """
    # SAFE: placeholder replacement, never .format() on user-supplied code
    script = RUNNER_TEMPLATE.replace("###IMPL_CODE###", impl).replace(
        "###SPEC_CODE###", spec
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                    delete=False) as f:
        f.write(script)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True, timeout=timeout
        )
        stdout = result.stdout.strip()
        if not stdout:
            return {
                "passed": False,
                "counterexample": None,
                "error": result.stderr.strip()[:500]
            }
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return {"passed": False, "counterexample": None,
                "error": f"Timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"passed": False, "counterexample": None,
                "error": f"Bad output: {result.stdout[:200]}"}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
```

```bash
pytest tests/test_runner.py -v
# ALL 3 TESTS MUST PASS
git add src/runner.py tests/test_runner.py
git commit -m "Phase 4: runner.py — subprocess-isolated Hypothesis execution with counterexample capture"
git push
```

**EXIT CONDITION:** All 3 runner tests pass. The identity bug PASSES the weak spec
and FAILS the strong spec. This verifies the core discrimination mechanism works.

---

### PHASE 5: Signal 1 — Spectest Completeness (90 minutes)

**Write `tests/test_signal1.py` first:**
```python
from src.signal1 import compute_completeness_score

def test_underconstrained_scores_low():
    """T01 merge_sorted weak spec should score below 0.4."""
    weak_spec = '''
from hypothesis import given, strategies as st
@given(st.lists(st.integers(), max_size=10),
       st.lists(st.integers(), max_size=10))
def test_merge_sorted(a, b):
    a_sorted = sorted(a)
    b_sorted = sorted(b)
    result = merge_sorted(a_sorted, b_sorted)
    assert len(result) == len(a) + len(b)
'''
    score = compute_completeness_score(
        spec=weak_spec,
        task_description="merge two sorted lists into one sorted list",
        function_name="merge_sorted"
    )
    assert score < 0.4, f"Expected score < 0.4, got {score}"

def test_correct_spec_scores_high():
    """sum_list correct spec should score above 0.7."""
    correct_spec = '''
from hypothesis import given, strategies as st
@given(st.lists(st.integers(min_value=-1000, max_value=1000), max_size=20))
def test_sum_list(lst):
    result = sum_list(lst)
    assert result == sum(lst)
    assert isinstance(result, int)
'''
    score = compute_completeness_score(
        spec=correct_spec,
        task_description="return the sum of all integers in a list",
        function_name="sum_list"
    )
    assert score > 0.7, f"Expected score > 0.7, got {score}"
```

**Write `src/signal1.py`:**
```python
# src/signal1.py
# Harness-style spectest completeness
# Generates invariant-checking harnesses, not static I/O pairs

from src.llm import call_llm
from src.runner import run_spec_against_impl

HARNESS_GEN_PROMPT = """Generate a Python function that VIOLATES the following
specification in 5 different ways. Each violation is a complete implementation
that is WRONG but might pass a weak spec.

TASK: {task_description}
FUNCTION NAME: {function_name}
SPEC: {spec}

Return a JSON array of 5 strings. Each string is a complete Python function
definition. Each function should be wrong in a distinct way.
Do not include markdown fences. Return JSON only."""


def compute_completeness_score(
    spec: str,
    task_description: str,
    function_name: str
) -> float:
    """
    S1: What fraction of wrong implementations does the spec correctly REJECT?
    Score = rejected / total. High score = spec is complete (catches bugs).
    Low score = spec is underconstrained (lets bugs through).
    """
    prompt = HARNESS_GEN_PROMPT.format(
        task_description=task_description,
        function_name=function_name,
        spec=spec
    )

    import json
    raw = call_llm(prompt, temperature=0.7, use_cache=False)
    try:
        wrong_impls = json.loads(raw)
    except json.JSONDecodeError:
        blocks = [b.strip() for b in raw.split("\n\n") if "def " in b]
        wrong_impls = blocks[:5]

    if not wrong_impls:
        return 0.5  # cannot determine

    rejected = 0
    counterexamples = []
    for impl in wrong_impls:
        result = run_spec_against_impl(spec=spec, impl=str(impl))
        if not result["passed"]:
            rejected += 1
        else:
            counterexamples.append({
                "impl": impl,
                "counterexample": result.get("counterexample")
            })

    # BUG 3 FIX APPLIED: original code was `return rejected / len(wrong_impls), counterexamples`
    # That is a tuple. Tests do `assert score < 0.4` — `(0.2, [...]) < 0.4` raises TypeError.
    # compute_completeness_score returns a float ONLY. Use compute_s1() when you need counterexamples.
    return rejected / len(wrong_impls)


def compute_s1(
    spec: str,
    task_description: str,
    function_name: str
) -> dict:
    """
    Full S1 result with both score and counterexamples.
    Returns: {"score": float, "counterexamples": list}

    Use this in pipeline.py and repair_loop.py when you need counterexample data.
    Use compute_completeness_score() directly only when you need the bare float.
    """
    prompt = HARNESS_GEN_PROMPT.format(
        task_description=task_description,
        function_name=function_name,
        spec=spec
    )
    import json
    raw = call_llm(prompt, temperature=0.7, use_cache=False)
    try:
        wrong_impls = json.loads(raw)
    except json.JSONDecodeError:
        blocks = [b.strip() for b in raw.split("\n\n") if "def " in b]
        wrong_impls = blocks[:5]

    if not wrong_impls:
        return {"score": 0.5, "counterexamples": []}

    rejected = 0
    counterexamples = []
    for impl in wrong_impls:
        result = run_spec_against_impl(spec=spec, impl=str(impl))
        if not result["passed"]:
            rejected += 1
        else:
            counterexamples.append({
                "impl": impl,
                "counterexample": result.get("counterexample")
            })
    return {"score": rejected / len(wrong_impls), "counterexamples": counterexamples}
```

```bash
pytest tests/test_signal1.py -v -s
git add src/signal1.py tests/test_signal1.py
git commit -m "Phase 5: signal1.py — harness-style spectest completeness (S1)"
git push
```

**EXIT CONDITION:** Underconstrained task scores < 0.4. Correct task scores > 0.7.

---

### PHASE 6: Signal 4 — Spec Stability (30 minutes)
**Cheapest novel contribution. Build it now while S1 is fresh.**

**Write `tests/test_signal4.py` first:**
```python
from src.signal4 import compute_stability_score

def test_stability_returns_float_between_0_and_1():
    score = compute_stability_score(
        task_description="return the sum of all integers in a list",
        function_name="sum_list",
        n_generations=3
    )
    assert 0.0 <= score <= 1.0

def test_two_tasks_have_different_stability():
    s1 = compute_stability_score("return the sum of all integers in a list",
                                  "sum_list", n_generations=3)
    s2 = compute_stability_score(
        "given a list of integers with possible duplicates, return a new list "
        "with all duplicates removed but preserving the original order of "
        "first occurrences of each element",
        "remove_duplicates", n_generations=3
    )
    # These may not always differ but structurally the function must run
    assert isinstance(s1, float) and isinstance(s2, float)
```

**Write `src/signal4.py`:**
```python
# src/signal4.py
# Spec stability: generate same spec 3x at T=0.7, measure agreement rate
# Novel contribution: epistemic uncertainty in LLM spec generation

from src.llm import call_llm
from src.runner import run_spec_against_impl
from templates import SPEC_GEN_PROMPT


def compute_stability_score(
    task_description: str,
    function_name: str,
    n_generations: int = 3,
    test_impls: list[str] | None = None,
    correct_impl: str | None = None  # FIX 10: use correct impl for meaningful stability signal
) -> float:
    """
    Generate the same spec n times at temperature=0.7.
    Run each spec variant against reference implementations.
    Agreement rate = fraction of (spec, impl) pairs that agree across variants.
    High score = spec is stable (deterministically correct or wrong).
    Low score = task description is ambiguous — flag for human review.
    """
    specs = []
    for _ in range(n_generations):
        prompt = SPEC_GEN_PROMPT.format(
            description=task_description,
            function_name=function_name
        )
        spec = call_llm(prompt, temperature=0.7, use_cache=False)
        specs.append(spec)

    if test_impls is None:
        # FIX 10 APPLIED: original code only used a trivially wrong impl (return None).
        # Every Hypothesis spec ever written fails against `return None`, so all 3 variants
        # at T=0.7 agree it fails → agreement = 1.0 → S4 = 1.0 for every task.
        # The signal is a constant with zero discriminative power.
        # Fix: use both the correct impl (should pass good specs) and the trivially wrong
        # impl (should fail all specs). Agreement across both = genuine stability signal.
        trivially_wrong = f"def {function_name}(*args, **kwargs): return None"
        if correct_impl is not None:
            test_impls = [correct_impl, trivially_wrong]
        else:
            test_impls = [trivially_wrong]

    # Measure agreement: for each impl, do all specs agree on pass/fail?
    agreements = []
    for impl in test_impls:
        results = [run_spec_against_impl(s, impl)["passed"] for s in specs]
        # Agreement = all same
        all_same = len(set(results)) == 1
        agreements.append(1.0 if all_same else 0.0)

    return sum(agreements) / len(agreements) if agreements else 0.5
```

```bash
pytest tests/test_signal4.py -v
git add src/signal4.py tests/test_signal4.py
git commit -m "Phase 6: signal4.py — spec stability signal (S4), novel epistemic uncertainty measure"
git push
```

---

### PHASE 7: Signal 2 — Variant Discrimination (60 minutes)

**Write `tests/test_signal2.py` first:**
```python
from src.signal2 import compute_discrimination_score

def test_underconstrained_spec_has_low_discrimination():
    weak_spec = '''
from hypothesis import given, strategies as st
@given(st.lists(st.integers(), max_size=10),
       st.lists(st.integers(), max_size=10))
def test_merge_sorted(a, b):
    a_sorted = sorted(a)
    b_sorted = sorted(b)
    result = merge_sorted(a_sorted, b_sorted)
    assert len(result) == len(a) + len(b)
'''
    impls = [
        "def merge_sorted(a, b): return sorted(a) + sorted(b)",
        "def merge_sorted(a, b): return a + b",
        "def merge_sorted(a, b): return a",
        "def merge_sorted(a, b): return []",
        "def merge_sorted(a, b):\n    result=[]\n    i,j=0,0\n    while i<len(a) and j<len(b):\n        if a[i]<=b[j]: result.append(a[i]);i+=1\n        else: result.append(b[j]);j+=1\n    result.extend(a[i:]);result.extend(b[j:])\n    return result"
    ]
    score = compute_discrimination_score(spec=weak_spec, implementations=impls)
    assert score < 0.4, f"Expected low discrimination, got {score}"
```

**Write `src/signal2.py`:**
```python
# src/signal2.py
# Oracle-guided variant discrimination
# Input-guided divergence prompting — implementations guided by actual Hypothesis inputs

from itertools import combinations
from src.runner import run_spec_against_impl


def compute_discrimination_score(
    spec: str,
    implementations: list[str]
) -> float:
    """
    S2: What fraction of implementation pairs does the spec DISTINGUISH?
    (One passes, one fails = distinguished. Both pass or both fail = not distinguished.)
    Score = distinguished_pairs / total_pairs
    Low score = spec cannot tell good from bad implementations.
    High score = spec is discriminating.
    """
    if len(implementations) < 2:
        return 0.0

    pairs = list(combinations(range(len(implementations)), 2))
    results = {}

    for i, impl in enumerate(implementations):
        r = run_spec_against_impl(spec=spec, impl=impl)
        results[i] = r["passed"]

    distinguished = 0
    for i, j in pairs:
        if results[i] != results[j]:
            distinguished += 1

    return distinguished / len(pairs)
```

```bash
pytest tests/test_signal2.py -v
git add src/signal2.py tests/test_signal2.py
git commit -m "Phase 7: signal2.py — oracle-guided variant discrimination (S2)"
git push
```

---

### PHASE 8: Signal 3 — CrossHair (45 minutes)
**Health check gate is non-negotiable. If it fails, mark N/A and move on.**

**Write `tests/test_signal3.py` first:**
```python
from src.signal3 import compute_crosshair_score, crosshair_health_check

def test_health_check_runs_without_exception():
    """Health check must run and return a bool — no crash allowed."""
    result = crosshair_health_check()
    assert isinstance(result, bool)

def test_crosshair_score_returns_valid_structure():
    spec = "def add(x: int, y: int) -> int:\n    \"\"\"\n    pre: x > 0\n    post: __return__ > x\n    \"\"\"\n    return x + y"
    result = compute_crosshair_score(function_code=spec)
    assert "available" in result
    assert "counterexample" in result
    assert "score" in result
```

**Write `src/signal3.py`:**
```python
# src/signal3.py
# CrossHair symbolic refutation
# Uses crosshair-tool for contract checking
# HEALTH CHECK GATE: if CrossHair fails on a known case, mark N/A for all tasks

import subprocess, sys, tempfile
from pathlib import Path

HEALTH_CHECK_CODE = '''
def double(x: int) -> int:
    """
    pre: x > 0
    post: __return__ > x
    """
    return x * 2
'''


def crosshair_health_check() -> bool:
    """Returns True if CrossHair is functional, False otherwise."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                    delete=False) as f:
        f.write(HEALTH_CHECK_CODE)
        tmp = f.name
    try:
        result = subprocess.run(
            ["crosshair", "check", tmp],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0 or "Counterexample" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    finally:
        Path(tmp).unlink(missing_ok=True)


def compute_crosshair_score(function_code: str) -> dict:
    """
    Run CrossHair on a function with contracts.
    Returns: {"available": bool, "counterexample": str|None, "score": float}
    score=1.0 if CrossHair finds a counterexample (spec is refutable = bad spec)
    score=0.0 if CrossHair confirms spec (no counterexample found)
    score=0.5 if CrossHair is unavailable (N/A)
    """
    if not crosshair_health_check():
        return {"available": False, "counterexample": None, "score": 0.5}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                    delete=False) as f:
        f.write(function_code)
        tmp = f.name
    try:
        result = subprocess.run(
            ["crosshair", "check", tmp],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        if "Counterexample" in output or "cannot be satisfied" in output:
            return {"available": True, "counterexample": output[:500], "score": 1.0}
        return {"available": True, "counterexample": None, "score": 0.0}
    except subprocess.TimeoutExpired:
        return {"available": True, "counterexample": None, "score": 0.5}
    finally:
        Path(tmp).unlink(missing_ok=True)
```

```bash
pytest tests/test_signal3.py -v
git add src/signal3.py tests/test_signal3.py
git commit -m "Phase 8: signal3.py — CrossHair symbolic refutation with health-check gate (S3)"
git push
```

---

### PHASE 9: Coverage-Guided Mutation Engine (90 minutes)
**This is the architectural novelty. Coverage delta, not pass count.**

**Write `tests/test_mutator.py` first:**
```python
from src.mutator import apply_mutations, identify_bad_constraint

def test_flipcomparison_on_overconstrained_spec():
    """FlipComparison on factorial spec should expose n=0 branch."""
    overconstrained_spec = '''
from hypothesis import given, strategies as st
@given(st.integers(min_value=1, max_value=10))
def test_factorial(n):
    result = factorial(n)
    assert result > 0
    assert result > n
'''
    correct_impl = "import math\ndef factorial(n): return math.factorial(n)"
    mutations = apply_mutations(spec=overconstrained_spec, impl=correct_impl)
    assert len(mutations) > 0
    for m in mutations:
        assert "operator" in m
        assert "mutated_spec" in m
        assert "coverage_delta" in m

def test_highest_delta_mutation_identifies_bad_constraint():
    """The mutation with highest coverage delta should be the bad constraint."""
    overconstrained_spec = '''
from hypothesis import given, strategies as st
@given(st.integers(min_value=1, max_value=10))
def test_factorial(n):
    result = factorial(n)
    assert result > 0
'''
    correct_impl = "import math\ndef factorial(n): return math.factorial(n)"
    mutations = apply_mutations(spec=overconstrained_spec, impl=correct_impl)
    best = max(mutations, key=lambda m: m["coverage_delta"])
    # The best mutation should involve removing the min_value=1 restriction
    assert best["coverage_delta"] > 0
```

**Write `src/mutator.py`:**
```python
# src/mutator.py
# Coverage-guided mutation engine
# Three operators: FlipComparison, RemovePrecondition, RemovePostcondition
# Scores by coverage DELTA, not pass count
# Highest delta = the bad constraint

import ast, re, subprocess, sys, tempfile, json
from pathlib import Path
from copy import deepcopy


# FIX 5 APPLIED: original approach used f-string to inline impl/spec into the runner
# script. Any impl or spec containing { or } (dict literal, set, f-string, comprehension)
# corrupts the f-string and returns empty coverage sets, making all deltas 0.
# Fix: use ###PLACEHOLDER### substitution — same technique already proven in runner.py.
_COVERAGE_TEMPLATE = '''
import coverage, json, sys

cov = coverage.Coverage(branch=True)
cov.start()

try:
    ###IMPL_CODE###

    from hypothesis import given, settings, strategies as st, assume
    ###SPEC_CODE###

    import inspect
    test_fn = None
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            test_fn = obj
            break
    if test_fn:
        test_fn()
except Exception:
    pass
finally:
    cov.stop()
    data = cov.get_data()
    covered = set()
    for f in data.measured_files():
        lines = data.lines(f)
        if lines:
            covered.update(lines)
    print(json.dumps(list(covered)))
'''


def _measure_coverage(impl: str, spec: str, timeout: int = 15) -> set:
    """
    Run spec against impl with coverage.py in subprocess.
    Returns set of covered line numbers in the impl.
    Uses placeholder substitution — safe for impl/spec containing {curly braces},
    dict literals, f-strings, set comprehensions. Never use f-string here.
    """
    script = _COVERAGE_TEMPLATE.replace(
        "###IMPL_CODE###", impl
    ).replace(
        "###SPEC_CODE###", spec
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True, timeout=timeout
        )
        if result.stdout.strip():
            return set(json.loads(result.stdout.strip()))
        return set()
    except Exception:
        return set()
    finally:
        Path(tmp).unlink(missing_ok=True)


def _flip_comparisons(spec: str) -> list[dict]:
    """FlipComparison: flip >, <, >=, <=, ==, != in assert statements."""
    mutations = []
    flips = {">": ">=", ">=": ">", "<": "<=", "<=": "<", "==": "!=", "!=": "=="}

    for original, replacement in flips.items():
        pattern = rf'assert\s+.*{re.escape(original)}'
        for match in re.finditer(pattern, spec):
            mutated = spec[:match.start()] + \
                      match.group().replace(original, replacement, 1) + \
                      spec[match.end():]
            mutations.append({
                "operator": "FlipComparison",
                "original": match.group(),
                "mutated": match.group().replace(original, replacement, 1),
                "mutated_spec": mutated
            })
    return mutations


def _remove_preconditions(spec: str) -> list[dict]:
    """RemovePrecondition: remove assume() calls and min/max value restrictions."""
    mutations = []

    # Remove assume() lines
    for line in spec.split("\n"):
        if "assume(" in line:
            mutated = spec.replace(line + "\n", "").replace(line, "")
            mutations.append({
                "operator": "RemovePrecondition",
                "original": line,
                "mutated": "",
                "mutated_spec": mutated
            })

    # Widen min_value/max_value in @given strategies
    for pattern, replacement in [
        (r'min_value=\d+', 'min_value=0'),
        (r'min_size=\d+', 'min_size=0'),
    ]:
        for match in re.finditer(pattern, spec):
            if match.group() != replacement:
                mutated = spec[:match.start()] + replacement + spec[match.end():]
                mutations.append({
                    "operator": "RemovePrecondition",
                    "original": match.group(),
                    "mutated": replacement,
                    "mutated_spec": mutated
                })
    return mutations


def _remove_postconditions(spec: str) -> list[dict]:
    """RemovePostcondition: remove individual assert statements."""
    mutations = []
    lines = spec.split("\n")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("assert "):
            remaining = "\n".join(lines[:i] + lines[i+1:])
            mutations.append({
                "operator": "RemovePostcondition",
                "original": stripped,
                "mutated": "",
                "mutated_spec": remaining
            })
    return mutations


def apply_mutations(spec: str, impl: str) -> list[dict]:
    """
    Apply all three mutation operators.
    Score each mutation by coverage delta against the correct implementation.
    Return sorted list (highest delta first).
    """
    baseline_coverage = _measure_coverage(impl=impl, spec=spec)

    all_mutations = (
        _flip_comparisons(spec) +
        _remove_preconditions(spec) +
        _remove_postconditions(spec)
    )

    scored = []
    for mutation in all_mutations:
        mutated_coverage = _measure_coverage(
            impl=impl, spec=mutation["mutated_spec"]
        )
        # Coverage delta: how many new branches become covered after mutation
        new_branches = mutated_coverage - baseline_coverage
        delta = len(new_branches)
        mutation["coverage_delta"] = delta
        mutation["newly_covered_lines"] = list(new_branches)
        scored.append(mutation)

    return sorted(scored, key=lambda m: m["coverage_delta"], reverse=True)


def identify_bad_constraint(spec: str, impl: str) -> dict | None:
    """
    Return the mutation with highest coverage delta.
    This is the bad constraint — the one whose removal reveals the most.
    Returns None if no mutations produce coverage delta > 0.
    """
    mutations = apply_mutations(spec=spec, impl=impl)
    if mutations and mutations[0]["coverage_delta"] > 0:
        return mutations[0]
    return None
```

```bash
pytest tests/test_mutator.py -v -s
git add src/mutator.py tests/test_mutator.py
git commit -m "Phase 9: mutator.py — coverage-guided mutation engine (FlipComparison, RemovePrecondition, RemovePostcondition)"
git push
```

**EXIT CONDITION:** T06 (overconstrained factorial) mutation with highest coverage
delta must be the one removing `min_value=1`. Verify manually by printing
`apply_mutations(...)` output.

---

### PHASE 10: Repair Loop (90 minutes)
**This is the contribution. Do not rush this phase.**

**Write `tests/test_repair.py` first:**
```python
from src.repair_loop import run_repair_loop

def test_repair_converges_on_underconstrained_spec():
    """T05 string_reverse identity bug: repair must produce spec that catches it."""
    weak_spec = '''
from hypothesis import given, strategies as st
@given(st.text(max_size=20))
def test_string_reverse(s):
    result = string_reverse(s)
    assert len(result) == len(s)
    assert sorted(result) == sorted(s)
'''
    buggy_impl = "def string_reverse(s): return s"
    correct_impl = "def string_reverse(s): return s[::-1]"

    result = run_repair_loop(
        spec=weak_spec,
        correct_impl=correct_impl,
        task_description="return the reverse of a string",
        function_name="string_reverse",
        max_iterations=3
    )

    assert "converged" in result
    assert "final_spec" in result
    assert "iterations" in result
    assert result["iterations"] <= 3

    if result["converged"]:
        # Verify repaired spec actually catches the bug
        from src.runner import run_spec_against_impl
        check = run_spec_against_impl(
            spec=result["final_spec"], impl=buggy_impl
        )
        assert not check["passed"], "Repaired spec must catch buggy impl"

def test_repair_correctly_implemented_is_no_op():
    """Correct spec should not be repaired (already passes)."""
    correct_spec = '''
from hypothesis import given, strategies as st
@given(st.lists(st.integers(min_value=-1000, max_value=1000), max_size=20))
def test_sum_list(lst):
    result = sum_list(lst)
    assert result == sum(lst)
'''
    correct_impl = "def sum_list(lst): return sum(lst)"
    result = run_repair_loop(
        spec=correct_spec,
        correct_impl=correct_impl,
        task_description="return the sum of all integers in a list",
        function_name="sum_list",
        max_iterations=3
    )
    assert result["converged"] is True
    assert result["iterations"] == 0
```

**Write `src/repair_loop.py`:**
```python
# src/repair_loop.py
# CEGIS-style spec repair loop
# Grounded prompt: bad AST node + counterexample + signal scores
# Max 3 iterations. 2 Gemini calls per iteration.
# Convergence = repaired spec passes runner on correct impl AND fails on buggy impls

from src.llm import call_llm
from src.runner import run_spec_against_impl
from src.signal1 import compute_completeness_score
from src.signal2 import compute_discrimination_score
from src.signal4 import compute_stability_score
from src.mutator import identify_bad_constraint
from templates import REPAIR_PROMPT


def run_repair_loop(
    spec: str,
    correct_impl: str,
    task_description: str,
    function_name: str,
    max_iterations: int = 3,
    buggy_impls: list[str] | None = None,
    verdict: str = "underconstrained"
) -> dict:
    """
    CEGIS-style repair loop.
    Returns: {
        "converged": bool,
        "iterations": int,
        "final_spec": str,
        "history": list of per-iteration results,
        "convergence_reason": str
    }
    """
    # Check if spec already passes correct impl
    initial_check = run_spec_against_impl(spec=spec, impl=correct_impl)
    if initial_check["passed"]:
        # Check if it also fails on buggy impls (if provided)
        if not buggy_impls:
            return {
                "converged": True,
                "iterations": 0,
                "final_spec": spec,
                "history": [],
                "convergence_reason": "Initial spec already passes correct impl"
            }

    current_spec = spec
    history = []

    for iteration in range(1, max_iterations + 1):
        # --- Iteration Step 1: Compute signals ---
        s1_score = compute_completeness_score(
            spec=current_spec,
            task_description=task_description,
            function_name=function_name
        )
        # Note: compute_completeness_score returns a float directly (Bug 3 fixed).
        # Use compute_s1() if you need the counterexamples dict.

        s4_score = compute_stability_score(
            task_description=task_description,
            function_name=function_name,
            n_generations=3
        )

        # S2 requires implementations — use buggy_impls if provided
        if buggy_impls and len(buggy_impls) >= 2:
            s2_score = compute_discrimination_score(
                spec=current_spec,
                implementations=buggy_impls + [correct_impl]
            )
        else:
            s2_score = s1_score  # fallback

        # Identify bad constraint via mutation engine
        bad_constraint = identify_bad_constraint(
            spec=current_spec, impl=correct_impl
        )

        # Get a counterexample
        check = run_spec_against_impl(spec=current_spec, impl=correct_impl)
        counterexample = check.get("counterexample", "No counterexample available")

        if check["passed"] and not counterexample:
            # Use a known-buggy impl to get a counterexample
            if buggy_impls:
                for buggy in buggy_impls:
                    buggy_check = run_spec_against_impl(
                        spec=current_spec, impl=buggy
                    )
                    if buggy_check["passed"]:
                        # This buggy impl passes — it's the counterexample source
                        counterexample = (
                            f"Buggy impl passes spec: {buggy[:100]}"
                        )
                        break

        # Get correct vs buggy output for context
        correct_output = "unknown"
        buggy_output = "unknown"
        if buggy_impls:
            try:
                exec_globals = {}
                exec(correct_impl, exec_globals)
                exec_globals_buggy = {}
                exec(buggy_impls[0], exec_globals_buggy)
            except Exception:
                pass

        # BUG 1 FIX APPLIED: original keys were s1=, s2=, s4= but the REPAIR_PROMPT
        # template uses {s1_score:.2f}, {s2_score:.2f}, {s4_score:.2f}.
        # Python raised KeyError on the first repair attempt. Fixed: keys now match exactly.
        repair_prompt = REPAIR_PROMPT.format(
            task_description=task_description,
            current_spec=current_spec,
            verdict=verdict,  # FIX 6: pass actual diagnosis from pipeline, not binary guess
            s1_score=s1_score,
            s2_score=s2_score,
            s4_score=s4_score,
            bad_ast_node=bad_constraint["original"] if bad_constraint else "unknown",
            mutation_operator=bad_constraint["operator"] if bad_constraint else "unknown",
            coverage_delta=bad_constraint["coverage_delta"] if bad_constraint else 0,
            counterexample=str(counterexample)[:500],
            correct_output=str(correct_output)[:200],
            buggy_output=str(buggy_output)[:200]
        )

        repaired_spec = call_llm(repair_prompt, temperature=0.2, use_cache=False)

        # --- Convergence check ---
        repaired_check = run_spec_against_impl(
            spec=repaired_spec, impl=correct_impl
        )

        converged = False
        convergence_reason = ""

        if repaired_check["passed"]:
            # Check that it catches buggy impls
            if buggy_impls:
                catches = [
                    not run_spec_against_impl(
                        spec=repaired_spec, impl=b
                    )["passed"]
                    for b in buggy_impls
                ]
                if any(catches):
                    converged = True
                    convergence_reason = (
                        f"Repaired spec passes correct impl and catches "
                        f"{sum(catches)}/{len(catches)} buggy impls"
                    )
            else:
                converged = True
                convergence_reason = "Repaired spec passes correct impl"

        history.append({
            "iteration": iteration,
            "s1_score": s1_score,
            "s2_score": s2_score,
            "s4_score": s4_score,
            "bad_constraint": bad_constraint,
            "counterexample": str(counterexample)[:200],
            "repaired_spec": repaired_spec,
            "converged": converged
        })

        current_spec = repaired_spec

        if converged:
            return {
                "converged": True,
                "iterations": iteration,
                "final_spec": repaired_spec,
                "history": history,
                "convergence_reason": convergence_reason
            }

    # Did not converge in max_iterations
    return {
        "converged": False,
        "iterations": max_iterations,
        "final_spec": current_spec,
        "history": history,
        "convergence_reason": f"Did not converge in {max_iterations} iterations. "
                               f"Final signal scores: S1={s1_score:.2f}, "
                               f"S2={s2_score:.2f}"
    }
```

```bash
pytest tests/test_repair.py -v -s --timeout=120
git add src/repair_loop.py tests/test_repair.py
git commit -m "Phase 10: repair_loop.py — CEGIS-style grounded spec repair loop (THE CONTRIBUTION)"
git push
```

**EXIT CONDITION:** string_reverse repair converges within 3 iterations AND the
repaired spec catches the identity buggy implementation.

---

### PHASE 11: Diagnosis + Full Pipeline (60 minutes)

**Write `src/diagnosis.py`:**
```python
# src/diagnosis.py
# Weighted signal fusion — NOT Bayesian, NOT P=0.65 prior
# Weights: S1=0.35, S2=0.35, S3=0.20, S4=0.10
#
# BUG 5 FIX APPLIED: original compute_verdict() could not distinguish
# overconstrained from underconstrained when S3 is N/A (7+ tasks).
# Both have LOW S1 and S2 — same signal profile. The only differentiator
# is whether coverage_delta is positive AND the best mutation is
# RemovePrecondition (means the precondition was too tight).
# Without this branch, all overconstrained tasks were misclassified as
# underconstrained, capping accuracy at ~10/15 regardless of everything else.
# Fix: pass mutation_result into compute_verdict(); if best mutation is
# RemovePrecondition with coverage_delta > 0, verdict = overconstrained.

WEIGHTS = {"s1": 0.35, "s2": 0.35, "s3": 0.20, "s4": 0.10}

UNDERCONSTRAINED_THRESHOLD = 0.45  # weighted score below this = underconstrained
OVERCONSTRAINED_THRESHOLD = 0.65   # weighted score above this = overconstrained


def compute_verdict(
    s1: float,
    s2: float,
    s3: float,
    s4: float,
    mutation_result: dict | None = None,
    correct_impl_passes: bool = True  # FIX 11: primary overconstrained signal
) -> dict:
    """
    Fuse four signals into a verdict.
    S1, S2: low scores = underconstrained (spec too weak)
    S3: high score = CrossHair found counterexample (spec has issue)
    S4: used for confidence, not direction
    mutation_result: best mutation from identify_bad_constraint(). Optional but
                     REQUIRED for correct overconstrained detection when S3=N/A.

    Returns: {"verdict": str, "confidence": float, "weighted_score": float}
    """
    # FIX 11 APPLIED: Primary overconstrained signal — deterministic, does not depend
    # on signal weights. If the correct implementation FAILS the spec, the spec is too
    # restrictive by definition. This catches all 5 overconstrained tasks (T06–T10) that
    # were silently misclassified by the mutation-only approach when the mutation engine
    # found ambiguous coverage deltas.
    if not correct_impl_passes:
        return {
            "verdict": "overconstrained",
            "confidence": s4,
            "weighted_score": 0.0,
            "signal_breakdown": {"s1": s1, "s2": s2, "s3": s3, "s4": s4},
            "overconstrained_via": "correct_impl_fails_spec",
        }

    # Secondary: coverage-based overconstrained detection via mutation engine.
    # Overconstrained specs have a narrow precondition — Hypothesis never generates
    # the edge case inputs, so wrong impls never get tested, giving LOW S1 AND S2
    # — identical signal profile to underconstrained. S3 resolves this when
    # available, but S3 is N/A for 7+ tasks. The mutation engine fills the gap:
    # if RemovePrecondition has the highest coverage delta (removing the tight
    # precondition exposes previously-uncovered branches), the spec is overconstrained.
    if (
        mutation_result is not None
        and mutation_result.get("coverage_delta", 0) > 0
        and mutation_result.get("operator") == "RemovePrecondition"
    ):
        return {
            "verdict": "overconstrained",
            "confidence": s4,
            "weighted_score": 0.5,  # signal was ambiguous without mutation
            "signal_breakdown": {"s1": s1, "s2": s2, "s3": s3, "s4": s4},
            "overconstrained_via": "mutation_coverage_delta",
        }

    # Invert S1 and S2 for the fusion score
    # (low S1/S2 = bad spec, so invert to get high = bad)
    underconstrained_signal = (
        WEIGHTS["s1"] * (1 - s1) +
        WEIGHTS["s2"] * (1 - s2) +
        WEIGHTS["s3"] * s3 +
        WEIGHTS["s4"] * (1 - s4)
    )

    confidence = s4  # stability = confidence in diagnosis

    if underconstrained_signal > OVERCONSTRAINED_THRESHOLD:
        verdict = "underconstrained"
    elif underconstrained_signal < UNDERCONSTRAINED_THRESHOLD:
        verdict = "correct"
    else:
        # Middle range: need more signal
        if s3 > 0.8:
            verdict = "overconstrained"
        elif s1 > 0.7 and s2 > 0.7:
            verdict = "correct"
        else:
            verdict = "underconstrained"  # default to underconstrained when uncertain

    return {
        "verdict": verdict,
        "confidence": confidence,
        "weighted_score": underconstrained_signal,
        "signal_breakdown": {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
    }
```

**Write `src/pipeline.py`:**
```python
# src/pipeline.py
# Full end-to-end orchestration for one task
# Calls every module in sequence, returns structured results

import json
from pathlib import Path
from src.llm import call_llm
from src.spec_gen import generate_spec
from src.impl_gen import generate_implementations
from src.runner import run_spec_against_impl
from src.signal1 import compute_completeness_score
from src.signal2 import compute_discrimination_score
from src.signal3 import compute_crosshair_score, crosshair_health_check
from src.signal4 import compute_stability_score
from src.mutator import identify_bad_constraint
from src.repair_loop import run_repair_loop
from src.diagnosis import compute_verdict


def run_pipeline(task: dict, use_planted_spec: bool = True) -> dict:
    """
    Run the full SpecMutate pipeline on one benchmark task.
    If use_planted_spec=True, use the planted (broken) spec from benchmark.
    If False, generate a new spec from the task description.
    """
    task_id = task["task_id"]
    description = task["description"]
    function_name = task["name"]
    correct_impl = task["reference_implementation"]
    buggy_impls = [b["code"] for b in task.get("buggy_implementations", [])]
    ground_truth = task["label"]

    print(f"\n{'='*50}")
    print(f"Running pipeline on {task_id}: {function_name}")
    print(f"Ground truth: {ground_truth}")

    # Step 1: Get spec
    if use_planted_spec:
        spec = task["planted_spec"]
        print("Using planted spec")
    else:
        spec = generate_spec(description=description, function_name=function_name)
        print("Generated new spec")

    # Step 2: Generate implementations if not in benchmark
    if not buggy_impls:
        all_impls = generate_implementations(
            description=description,
            signature=f"def {function_name}(...):",
            oracle_inputs=[]
        )
    else:
        all_impls = buggy_impls + [correct_impl]

    # Step 3: Run signals
    s1 = compute_completeness_score(spec, description, function_name)
    # Note: returns float directly (Bug 3 fixed). Use compute_s1() for counterexamples.

    s2 = compute_discrimination_score(spec, all_impls)

    s3_result = compute_crosshair_score(
        f"{correct_impl}\n\n# Spec contract:\n{spec}"
    )
    s3 = s3_result["score"]

    s4 = compute_stability_score(
        task_description=description,
        function_name=function_name,
        correct_impl=correct_impl  # FIX 10: pass correct impl for meaningful S4
    )

    # Step 4: Diagnose
    # FIX 11: Direct overconstrained check — does the correct impl pass the spec?
    # This is deterministic and is the primary overconstrained signal.
    correct_impl_passes = run_spec_against_impl(
        spec=spec, impl=correct_impl
    )["passed"]

    # Also use mutation engine for secondary overconstrained signal (Bug 5 fix)
    from src.mutator import identify_bad_constraint
    mutation_result = identify_bad_constraint(spec=spec, impl=correct_impl)
    diagnosis = compute_verdict(
        s1=s1, s2=s2, s3=s3, s4=s4,
        mutation_result=mutation_result,
        correct_impl_passes=correct_impl_passes  # FIX 11
    )
    predicted = diagnosis["verdict"]
    correct_diagnosis = (predicted == ground_truth)

    print(f"Predicted: {predicted} | Ground truth: {ground_truth} | "
          f"Correct: {correct_diagnosis}")

    # Step 5: Repair (only if not correct)
    repair_result = None
    if predicted != "correct":
        repair_result = run_repair_loop(
            spec=spec,
            correct_impl=correct_impl,
            task_description=description,
            function_name=function_name,
            buggy_impls=buggy_impls,
            max_iterations=3,
            verdict=predicted  # FIX 6: pass actual diagnosis so repair prompt is accurate
        )
        print(f"Repair: {'CONVERGED' if repair_result['converged'] else 'DID NOT CONVERGE'} "
              f"in {repair_result['iterations']} iterations")

    return {
        "task_id": task_id,
        "ground_truth": ground_truth,
        "predicted": predicted,
        "correct_diagnosis": correct_diagnosis,
        "signals": {"s1": s1, "s2": s2, "s3": s3, "s4": s4},
        "diagnosis": diagnosis,
        "repair": repair_result,
    }


def run_full_benchmark(output_path: str = "results/benchmark_results.json") -> dict:
    """Run pipeline on all 15 tasks. Save results. Print summary."""
    with open("benchmark.json") as f:
        data = json.load(f)
    tasks = data["benchmark"]["tasks"]

    results = []
    correct_count = 0
    repair_converged = 0
    repair_total = 0

    for task in tasks:
        result = run_pipeline(task, use_planted_spec=True)
        results.append(result)
        if result["correct_diagnosis"]:
            correct_count += 1
        if result["repair"]:
            repair_total += 1
            if result["repair"]["converged"]:
                repair_converged += 1

    accuracy = correct_count / len(tasks)
    repair_rate = repair_converged / repair_total if repair_total > 0 else 0

    summary = {
        "diagnostic_accuracy": accuracy,
        "correct_diagnoses": correct_count,
        "total_tasks": len(tasks),
        "repair_convergence_rate": repair_rate,
        "repair_converged": repair_converged,
        "repair_total": repair_total,
        "results": results
    }

    Path("results").mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"HEADLINE NUMBERS:")
    print(f"Diagnostic accuracy: {correct_count}/{len(tasks)} ({accuracy:.1%})")
    print(f"Repair convergence: {repair_converged}/{repair_total} ({repair_rate:.1%})")
    print(f"{'='*50}")

    return summary
```

```bash
# Run on 3 tasks first to verify:
python -c "
from src.pipeline import run_pipeline
import json
with open('benchmark.json') as f:
    tasks = json.load(f)['benchmark']['tasks']
# Test on T01 (underconstrained), T06 (overconstrained), T11 (correct)
for task in [tasks[0], tasks[5], tasks[10]]:
    r = run_pipeline(task)
    print(r['task_id'], r['predicted'], r['ground_truth'], r['correct_diagnosis'])
"

git add src/diagnosis.py src/pipeline.py
git commit -m "Phase 11: diagnosis.py + pipeline.py — weighted signal fusion and full benchmark orchestration"
git push
```

---

### PHASE 12: Full Benchmark Run (45 minutes)

```bash
python -c "
from src.pipeline import run_full_benchmark
summary = run_full_benchmark()
print('ACCURACY:', summary['diagnostic_accuracy'])
print('REPAIR RATE:', summary['repair_convergence_rate'])
"

# Fill in the README with actual numbers from output
# Line 1 of README.md must say:
# SpecMutate achieves X/15 diagnostic accuracy and Y% repair convergence
# on our 15-task SpecMutate-15 benchmark.

git add results/ README.md RESULTS.md
git commit -m "Phase 12: Full benchmark run — headline numbers locked"
git push
```

**RESULTS.md must contain:**
1. 7-row ablation table (S1 alone, S2 alone, S3 alone, S4 alone, S1+S2, S1+S2+S3, all four)
2. Per-category breakdown (5 underconstrained, 5 overconstrained, 5 correct)
3. Repair convergence table (converged vs non-converged, with iteration count)
4. Non-convergence analysis — what signal scores looked like on failing cases

---

### PHASE 13: Streamlit Demo (45 minutes)

**Write `app.py`:**
```python
# app.py
import streamlit as st
import json
from pathlib import Path
from src.pipeline import run_pipeline

st.set_page_config(page_title="SpecMutate", layout="wide")
st.title("SpecMutate: Python Spec Diagnosis & Repair")
st.caption("Apart Research SPS Hackathon — Track 2: Specification Validation")

# Load cached results if available
RESULTS_PATH = "results/benchmark_results.json"

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Try It")
    description = st.text_area(
        "Natural language function description:",
        value="Sort a list of integers in ascending order.",
        height=80
    )
    function_name = st.text_input("Function name:", value="sort_ascending")

    if st.button("Run SpecMutate Pipeline", type="primary"):
        with st.spinner("Running signals and repair loop..."):
            task = {
                "task_id": "demo",
                "name": function_name,
                "description": description,
                "label": "unknown",
                "reference_implementation": f"def {function_name}(lst): return sorted(lst)",
                "buggy_implementations": [],
                "planted_spec": "",
            }
            result = run_pipeline(task, use_planted_spec=False)

        verdict = result["diagnosis"]["verdict"]
        color = {"underconstrained": "🔴", "overconstrained": "🟡", "correct": "🟢"}
        st.markdown(f"### Verdict: {color.get(verdict, '⚪')} {verdict.upper()}")
        st.metric("Confidence", f"{result['diagnosis']['confidence']:.0%}")

        st.subheader("Signal Scores")
        signals = result["signals"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("S1 Completeness", f"{signals['s1']:.2f}")
        c2.metric("S2 Discrimination", f"{signals['s2']:.2f}")
        c3.metric("S3 CrossHair", f"{signals['s3']:.2f}")
        c4.metric("S4 Stability", f"{signals['s4']:.2f}")

        if result.get("repair"):
            repair = result["repair"]
            st.subheader("Repair Loop")
            if repair["converged"]:
                st.success(f"✅ Converged in {repair['iterations']} iteration(s)")
                st.code(repair["final_spec"], language="python")
            else:
                st.warning(f"⚠️ Did not converge in {repair['iterations']} iterations")
                st.text(repair["convergence_reason"])

with col2:
    st.subheader("Benchmark Results")
    if Path(RESULTS_PATH).exists():
        with open(RESULTS_PATH) as f:
            results = json.load(f)
        st.metric("Diagnostic Accuracy",
                  f"{results['correct_diagnoses']}/{results['total_tasks']}")
        st.metric("Repair Convergence Rate",
                  f"{results['repair_convergence_rate']:.0%}")
    else:
        st.info("Run Phase 12 benchmark first to see results here.")
```

```bash
streamlit run app.py
# Verify in browser: paste a description, see verdict + signals + repair
# Must respond in under 30 seconds on cache hit

git add app.py
git commit -m "Phase 13: Streamlit demo — verdict, signals, repair status in browser"
git push
```

---

### PHASE 14: Submission Package (30 minutes)

**README.md template:**
```markdown
# SpecMutate

**Diagnostic accuracy: X/15 | Repair convergence: Y% within 3 iterations**

SpecMutate is a Python-native, coverage-guided spec repair harness for
LLM-generated Hypothesis specifications. [REST OF CANONICAL CLAIM]

## Quickstart
pip install -r requirements.txt
cp .env.example .env  # add your GEMINI_API_KEY
python -c "from src.pipeline import run_full_benchmark; run_full_benchmark()"
streamlit run app.py

## Related Work

| System | Language | Approach | Gap vs SpecMutate |
|--------|----------|----------|-------------------|
| VeriAct [arXiv:2604.00280] | JML/Java | Iterative synthesis-repair via OpenJML verification | Requires OpenJML infrastructure; mutates outputs not spec AST nodes |
| VeriSpecGen [arXiv:2604.10392] | Lean | NL → atomic requirements → clause-level repair with traceability maps | Requires Lean proof infrastructure; 86.6% on VERINA but no Python PBT |
| SpecRL [arXiv:2604.05820] | Dafny | RL training on negative-test completeness signal | Requires training pipeline; inference-time only for SpecMutate |
| AutoSpec [arXiv:2404.00762] | C/ACSL | LLM generation + Frama-C validation loop | C/ACSL domain; no mutation-based constraint localization |
| CoverUp [arXiv:2403.16218] | Python | Coverage-guided test generation | Generates tests, not specs; no repair loop |

SpecMutate is the first Python-native, Hypothesis-native diagnosis-repair harness
to combine coverage-guided AST mutation with a CEGIS-style grounded repair loop,
requiring zero formal verification infrastructure beyond a Gemini API key.

## Future Work (SPS Fellowship Scope)
1. Scale to 100+ task benchmark with independent labeling
2. Extend coverage-guided mutation to full 6-operator set with subsumption ordering
3. Port repair loop to Dafny/JML specs (test language-agnostic generalizability)
4. Evaluate on real GitHub Python repos with known bugs
```

```bash
# Final clean install test
python -m venv test_env
source test_env/bin/activate
pip install -r requirements.txt
python validate_benchmark.py
pytest tests/ -v --timeout=60
python -c "from src.pipeline import run_pipeline; print('OK')"
deactivate && rm -rf test_env

git add README.md RESULTS.md
git commit -m "Phase 14: Submission package — README with headline numbers, RESULTS.md ablation"
git push

echo "SUBMISSION COMPLETE"
```

---

## SECTION 5: run_checks.sh — RUN AFTER EVERY CHANGE

```bash
#!/bin/bash
set -e
echo "=== Formatting ==="
black src/ tests/ --check

echo "=== Static Analysis ==="
pylint src/ --disable=C0114,C0115,C0116,R0903 --fail-under=7.0

echo "=== Tests ==="
pytest tests/ -v --timeout=60

echo "=== ALL CHECKS PASSED ==="
```

```bash
chmod +x run_checks.sh
```

---

## SECTION 6: GITHUB COMMIT DISCIPLINE

Every phase ends with exactly these three commands:
```bash
git add [files changed in this phase]
git commit -m "Phase N: [module] — [one-line description of what it does]"
git push
```

Commit messages must follow this format. Do not squash phases. Every phase
must be independently reviewable in the git log.

---

## SECTION 7: WHAT WINNING LOOKS LIKE

A judge opens your repository. In 30 seconds they see:
1. README line 1: two real numbers (diagnostic accuracy, repair convergence rate)
2. `git log`: 14 commits, one per phase, clean progression
3. `bash run_checks.sh`: passes
4. Streamlit demo: runs, shows verdict + signals + repair in under 30 seconds

That is 1st place. Everything in this document exists to produce those four things.
