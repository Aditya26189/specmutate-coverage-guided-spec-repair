# src/signal4.py
# Spec stability: generate same spec 3x at T=0.7, measure agreement rate
# Novel contribution: epistemic uncertainty in LLM spec generation

from src.llm import call_llm
from src.runner import run_spec_against_impl
from src.templates import SPEC_GEN_PROMPT


def compute_stability_score(
    task_description: str,
    function_name: str,
    n_generations: int = 3,
    test_impls: list[str] | None = None,
    correct_impl: str | None = None
) -> float:
    """
    Generate the same spec n times at temperature=0.7 and use_cache=False.
    Measure consensus agreement against correct_impl.
    Score = 1.0 if all agree (all pass or all fail).
    Score = 0.0 if there is a split decision.
    """
    if correct_impl is None:
        return 1.0

    specs = []
    for _ in range(n_generations):
        prompt = SPEC_GEN_PROMPT.format(
            description=task_description,
            function_name=function_name
        )
        spec = call_llm(prompt, temperature=0.7, use_cache=False)
        specs.append(spec)

    results = [run_spec_against_impl(s, correct_impl)["passed"] for s in specs]
    pass_count = sum(1 for r in results if r)
    
    # Agreement scoring logic: all same (3 pass or 0 pass) -> 1.0, otherwise -> 0.0
    if pass_count == n_generations or pass_count == 0:
        return 1.0
    return 0.0
