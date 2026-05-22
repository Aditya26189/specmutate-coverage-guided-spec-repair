# tests/test_spec_gen.py
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
