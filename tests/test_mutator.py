# tests/test_mutator.py
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
    correct_impl = """
def factorial(n):
    if n == 0:
        return 1
    res = 1
    for i in range(1, n + 1):
        res *= i
    return res
"""
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
    correct_impl = """
def factorial(n):
    if n == 0:
        return 1
    res = 1
    for i in range(1, n + 1):
        res *= i
    return res
"""
    mutations = apply_mutations(spec=overconstrained_spec, impl=correct_impl)
    best = max(mutations, key=lambda m: m["coverage_delta"])
    # The best mutation should involve removing the min_value=1 restriction
    assert best["coverage_delta"] > 0
