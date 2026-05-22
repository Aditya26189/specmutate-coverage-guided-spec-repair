# tests/test_runner.py
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
