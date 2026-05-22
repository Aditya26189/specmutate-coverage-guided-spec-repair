# src/signal1.py
# Harness-style spectest completeness
# Generates invariant-checking harnesses, not static I/O pairs

from src.llm import call_llm
from src.runner import run_spec_against_impl

HARNESS_GEN_PROMPT = """Generate a Python function that VIOLATES the following
specification in 5 different ways. Each violation is a complete implementation
that is WRONG but might pass a weak spec.

TASK: {task_description}
FUNCTION NAME: {function_name}
SPEC: {spec}

Return a JSON array of 5 strings. Each string is a complete Python function
definition. Each function should be wrong in a distinct way.
Do not include markdown fences. Return JSON only."""


def compute_completeness_score(
    spec: str,
    task_description: str,
    function_name: str
) -> float:
    """
    S1: What fraction of wrong implementations does the spec correctly REJECT?
    Score = rejected / total. High score = spec is complete (catches bugs).
    Low score = spec is underconstrained (lets bugs through).
    """
    prompt = HARNESS_GEN_PROMPT.format(
        task_description=task_description,
        function_name=function_name,
        spec=spec
    )

    import json
    raw = call_llm(prompt, temperature=0.7, use_cache=False)
    try:
        wrong_impls = json.loads(raw)
    except json.JSONDecodeError:
        blocks = [b.strip() for b in raw.split("\n\n") if "def " in b]
        wrong_impls = blocks[:5]

    if not wrong_impls:
        return 0.5  # cannot determine

    rejected = 0
    counterexamples = []
    for impl in wrong_impls:
        result = run_spec_against_impl(spec=spec, impl=str(impl))
        if not result["passed"]:
            rejected += 1
        else:
            counterexamples.append({
                "impl": impl,
                "counterexample": result.get("counterexample")
            })

    # BUG 3 FIX APPLIED: original code was `return rejected / len(wrong_impls), counterexamples`
    # That is a tuple. Tests do `assert score < 0.4` — `(0.2, [...]) < 0.4` raises TypeError.
    # compute_completeness_score returns a float ONLY. Use compute_s1() when you need counterexamples.
    return rejected / len(wrong_impls)


def compute_s1(
    spec: str,
    task_description: str,
    function_name: str
) -> dict:
    """
    Full S1 result with both score and counterexamples.
    Returns: {"score": float, "counterexamples": list}

    Use this in pipeline.py and repair_loop.py when you need counterexample data.
    Use compute_completeness_score() directly only when you need the bare float.
    """
    prompt = HARNESS_GEN_PROMPT.format(
        task_description=task_description,
        function_name=function_name,
        spec=spec
    )
    import json
    raw = call_llm(prompt, temperature=0.7, use_cache=False)
    try:
        wrong_impls = json.loads(raw)
    except json.JSONDecodeError:
        blocks = [b.strip() for b in raw.split("\n\n") if "def " in b]
        wrong_impls = blocks[:5]

    if not wrong_impls:
        return {"score": 0.5, "counterexamples": []}

    rejected = 0
    counterexamples = []
    for impl in wrong_impls:
        result = run_spec_against_impl(spec=spec, impl=str(impl))
        if not result["passed"]:
            rejected += 1
        else:
            counterexamples.append({
                "impl": impl,
                "counterexample": result.get("counterexample")
            })
    return {"score": rejected / len(wrong_impls), "counterexamples": counterexamples}
