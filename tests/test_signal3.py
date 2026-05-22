# tests/test_signal3.py
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
