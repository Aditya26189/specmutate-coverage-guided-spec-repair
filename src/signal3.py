# src/signal3.py
# CrossHair symbolic refutation using concolic check

import subprocess, sys, tempfile
from pathlib import Path

HEALTH_CHECK_CODE = '''
from hypothesis import given, strategies as st
def double(x: int) -> int:
    return x * 2

@given(st.integers(min_value=1, max_value=100))
def test_double(x):
    assert double(x) > x
'''

_crosshair_health_check_cached = None

def crosshair_health_check() -> bool:
    """Returns True if CrossHair is functional, False otherwise."""
    global _crosshair_health_check_cached
    if _crosshair_health_check_cached is not None:
        return _crosshair_health_check_cached

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(HEALTH_CHECK_CODE)
        tmp = f.name
    try:
        result = subprocess.run(
            [sys.executable, "-m", "crosshair", "check", "--analysis_kind=hypothesis", tmp],
            capture_output=True, text=True, timeout=15
        )
        status = result.returncode == 0 or "Counterexample" in result.stdout or "cannot be satisfied" in result.stdout
        _crosshair_health_check_cached = status
        return status
    except (subprocess.TimeoutExpired, FileNotFoundError):
        _crosshair_health_check_cached = False
        return False
    finally:
        Path(tmp).unlink(missing_ok=True)


def compute_crosshair_score(function_code: str) -> dict:
    """
    Run CrossHair check --analysis_kind=hypothesis on a combined function code.
    Returns: {"available": bool, "counterexample": str|None, "score": float}
    score=1.0 if CrossHair finds a counterexample (spec is refutable = bad spec)
    score=0.0 if CrossHair confirms spec (no counterexample found)
    score=0.5 if CrossHair is unavailable (N/A)
    """
    if not crosshair_health_check():
        return {"available": False, "counterexample": None, "score": 0.5}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(function_code)
        tmp = f.name
    try:
        result = subprocess.run(
            [sys.executable, "-m", "crosshair", "check", "--analysis_kind=hypothesis", tmp],
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


def compute_s3(spec: str, correct_impl: str) -> float:
    """Public helper returning float score directly, accepting spec and correct_impl."""
    combined = f"{correct_impl}\n\n{spec}"
    res = compute_crosshair_score(combined)
    return res["score"]

