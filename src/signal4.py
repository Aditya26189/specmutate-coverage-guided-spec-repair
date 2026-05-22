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
