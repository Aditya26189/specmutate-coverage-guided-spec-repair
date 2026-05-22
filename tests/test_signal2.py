# tests/test_signal2.py
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
