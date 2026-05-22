# tests/test_repair.py
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
        max_iterations=3,
        verdict="correct"
    )
    assert result["converged"] is True
    assert result["iterations"] == 0
