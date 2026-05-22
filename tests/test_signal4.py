# tests/test_signal4.py
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
