# src/repair_loop.py
# feedback-guided spec repair loop
# Grounded prompt: bad AST node + counterexample + signal scores
# Max 3 iterations. 2 Gemini calls per iteration.
# Convergence = repaired spec passes runner on correct impl AND fails on buggy impls

import re
from src.llm import call_llm
from src.runner import run_spec_against_impl
from src.signal1 import compute_completeness_score
from src.signal2 import compute_discrimination_score
from src.signal4 import compute_stability_score
from src.mutator import identify_bad_constraint
from src.templates import REPAIR_PROMPT


def get_output_on_counterexample(impl_code: str, func_name: str, counterexample_str: str) -> str:
    """
    Attempt to run the implementation on the counterexample input
    to get the output value for LLM context.
    """
    if not counterexample_str or "Falsifying example" not in counterexample_str:
        return "unknown"
    try:
        # Find the function call arguments
        # e.g. test_factorial(n=0) or test_merge_sorted(a=[1], b=[2])
        # We search for test_func_name(...)
        match = re.search(r'test_\w+\s*\((.*)\)', counterexample_str, re.DOTALL)
        if not match:
            # Secondary attempt: search for any parenthesized expression
            match = re.search(r'\((.*)\)', counterexample_str, re.DOTALL)
            if not match:
                return "unknown"
        args_str = match.group(1).strip()
        
        # Evaluate args_str to get kwargs
        local_vars = {}
        exec(f"kwargs = dict({args_str})", {}, local_vars)
        kwargs = local_vars.get("kwargs", {})
        
        # Define the function in a fresh context
        func_vars = {}
        exec(impl_code, {}, func_vars)
        func = func_vars.get(func_name)
        if func:
            res = func(**kwargs)
            return repr(res)
    except Exception as e:
        return f"Error executing: {e}"
    return "unknown"


def run_repair_loop(
    spec: str,
    correct_impl: str,
    task_description: str,
    function_name: str,
    max_iterations: int = 3,
    buggy_impls: list[str] | None = None,
    verdict: str = "underconstrained"
) -> dict:
    """
    feedback-guided repair loop.
    Returns: {
        "converged": bool,
        "iterations": int,
        "final_spec": str,
        "history": list of per-iteration results,
        "convergence_reason": str
    }
    """
    # Check if spec already passes correct impl
    initial_check = run_spec_against_impl(spec=spec, impl=correct_impl)
    if verdict == "correct" and initial_check["passed"]:
        if buggy_impls:
            catches = [
                not run_spec_against_impl(spec=spec, impl=b)["passed"]
                for b in buggy_impls
            ]
            import math
            if sum(catches) >= math.ceil(len(buggy_impls) * 0.70):
                return {
                    "converged": True,
                    "iterations": 0,
                    "final_spec": spec,
                    "history": [],
                    "convergence_reason": f"Initial spec is correct and catches {sum(catches)}/{len(buggy_impls)} buggy impls"
                }
        else:
            return {
                "converged": True,
                "iterations": 0,
                "final_spec": spec,
                "history": [],
                "convergence_reason": "Initial spec is correct"
            }

    current_spec = spec
    history = []

    for iteration in range(1, max_iterations + 1):
        # --- Iteration Step 1: Compute signals ---
        s1_score = compute_completeness_score(
            spec=current_spec,
            task_description=task_description,
            function_name=function_name
        )

        s4_score = compute_stability_score(
            task_description=task_description,
            function_name=function_name,
            correct_impl=correct_impl,
            n_generations=3
        )

        # S2 requires implementations — use buggy_impls if provided
        if buggy_impls and len(buggy_impls) >= 2:
            s2_score = compute_discrimination_score(
                spec=current_spec,
                implementations=buggy_impls + [correct_impl]
            )
        else:
            s2_score = s1_score  # default

        # Identify bad constraint via mutation engine
        bad_constraint = identify_bad_constraint(
            spec=current_spec, impl=correct_impl
        )

        # Get a counterexample
        check = run_spec_against_impl(spec=current_spec, impl=correct_impl)
        counterexample = check.get("counterexample", "No counterexample available")

        if check["passed"] and not counterexample:
            # Use a known-buggy impl to get a counterexample
            if buggy_impls:
                for buggy in buggy_impls:
                    buggy_check = run_spec_against_impl(
                        spec=current_spec, impl=buggy
                    )
                    if not buggy_check["passed"] and buggy_check.get("counterexample"):
                        counterexample = buggy_check["counterexample"]
                        break
                    elif buggy_check["passed"]:
                        # This buggy impl passes — it's the counterexample source
                        counterexample = (
                            f"Buggy impl passes spec: {buggy[:100]}"
                        )
                        break

        # Get correct vs buggy output for context
        correct_output = get_output_on_counterexample(correct_impl, function_name, str(counterexample))
        buggy_output = "unknown"
        if buggy_impls:
            buggy_output = get_output_on_counterexample(buggy_impls[0], function_name, str(counterexample))

        # Format repair prompt using REPAIR_PROMPT
        repair_prompt = REPAIR_PROMPT.format(
            task_description=task_description,
            current_spec=current_spec,
            verdict=verdict,
            s1_score=s1_score,
            s2_score=s2_score,
            s4_score=s4_score,
            bad_ast_node=bad_constraint["original"] if bad_constraint else "unknown",
            mutation_operator=bad_constraint["operator"] if bad_constraint else "unknown",
            coverage_delta=bad_constraint["coverage_delta"] if bad_constraint else 0,
            counterexample=str(counterexample)[:500],
            correct_output=str(correct_output)[:200],
            buggy_output=str(buggy_output)[:200]
        )

        repaired_spec = call_llm(repair_prompt, temperature=0.2, use_cache=False)

        # --- Convergence check ---
        repaired_check = run_spec_against_impl(
            spec=repaired_spec, impl=correct_impl
        )

        converged = False
        convergence_reason = ""

        if repaired_check["passed"]:
            # Check that it catches buggy impls
            if buggy_impls:
                catches = [
                    not run_spec_against_impl(
                        spec=repaired_spec, impl=b
                    )["passed"]
                    for b in buggy_impls
                ]
                import math
                if sum(catches) >= math.ceil(len(buggy_impls) * 0.70):
                    converged = True
                    convergence_reason = (
                        f"Repaired spec passes correct impl and catches "
                        f"{sum(catches)}/{len(catches)} buggy impls"
                    )
            else:
                converged = True
                convergence_reason = "Repaired spec passes correct impl"

        history.append({
            "iteration": iteration,
            "s1_score": s1_score,
            "s2_score": s2_score,
            "s4_score": s4_score,
            "bad_constraint": bad_constraint,
            "counterexample": str(counterexample)[:200],
            "repaired_spec": repaired_spec,
            "converged": converged
        })

        current_spec = repaired_spec

        if converged:
            return {
                "converged": True,
                "iterations": iteration,
                "final_spec": repaired_spec,
                "history": history,
                "convergence_reason": convergence_reason
            }

    # Did not converge in max_iterations
    return {
        "converged": False,
        "iterations": max_iterations,
        "final_spec": current_spec,
        "history": history,
        "convergence_reason": f"Did not converge in {max_iterations} iterations. "
                               f"Final signal scores: S1={s1_score:.2f}, "
                               f"S2={s2_score:.2f}"
    }
