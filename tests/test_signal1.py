# tests/test_signal1.py
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
    assert score < 0.7, f"Expected score < 0.7, got {score}"

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
