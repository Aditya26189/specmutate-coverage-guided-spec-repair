# src/pipeline.py
# Full end-to-end orchestration for one task
# Calls every module in sequence, returns structured results

import json
from pathlib import Path
from src.llm import call_llm
from src.spec_gen import generate_spec
from src.impl_gen import generate_implementations
from src.runner import run_spec_against_impl
from src.signal1 import compute_completeness_score
from src.signal2 import compute_discrimination_score
from src.signal3 import compute_crosshair_score, crosshair_health_check
from src.signal4 import compute_stability_score
from src.mutator import identify_bad_constraint
from src.repair_loop import run_repair_loop
from src.diagnosis import compute_verdict


def run_pipeline(task: dict, use_planted_spec: bool = True) -> dict:
    """
    Run the full SpecMutate pipeline on one benchmark task.
    If use_planted_spec=True, use the planted (broken) spec from benchmark.
    If False, generate a new spec from the task description.
    """
    task_id = task["task_id"]
    description = task["description"]
    function_name = task["name"]
    correct_impl = task["reference_implementation"]
    buggy_impls = [b["code"] for b in task.get("buggy_implementations", [])]
    ground_truth = task["label"]

    print(f"\n{'='*50}")
    print(f"Running pipeline on {task_id}: {function_name}")
    print(f"Ground truth: {ground_truth}")

    # Step 1: Get spec
    if use_planted_spec:
        spec = task["planted_spec"]
        print("Using planted spec")
    else:
        spec = generate_spec(description=description, function_name=function_name)
        print("Generated new spec")

    # Step 2: Generate implementations if not in benchmark
    if not buggy_impls:
        all_impls = generate_implementations(
            description=description,
            signature=f"def {function_name}(...):",
            oracle_inputs=[]
        )
    else:
        all_impls = buggy_impls + [correct_impl]

    # Step 3: Run signals
    s1 = compute_completeness_score(spec, description, function_name)
    # Note: returns float directly (Bug 3 fixed). Use compute_s1() for counterexamples.

    s2 = compute_discrimination_score(spec, all_impls)

    s3_result = compute_crosshair_score(
        f"{correct_impl}\n\n# Spec contract:\n{spec}"
    )
    s3 = s3_result["score"]

    s4 = compute_stability_score(
        task_description=description,
        function_name=function_name,
        correct_impl=correct_impl  # FIX 10: pass correct impl for meaningful S4
    )

    # Step 4: Diagnose
    # FIX 11: Direct overconstrained check — does the correct impl pass the spec?
    # This is deterministic and is the primary overconstrained signal.
    correct_impl_passes = run_spec_against_impl(
        spec=spec, impl=correct_impl
    )["passed"]

    # Also use mutation engine for secondary overconstrained signal (Bug 5 fix)
    from src.mutator import identify_bad_constraint
    mutation_result = identify_bad_constraint(spec=spec, impl=correct_impl)
    diagnosis = compute_verdict(
        s1=s1, s2=s2, s3=s3, s4=s4,
        mutation_result=mutation_result,
        correct_impl_passes=correct_impl_passes  # FIX 11
    )
    predicted = diagnosis["verdict"]
    correct_diagnosis = (predicted == ground_truth)

    print(f"Predicted: {predicted} | Ground truth: {ground_truth} | "
          f"Correct: {correct_diagnosis}")

    # Step 5: Repair (only if not correct)
    repair_result = None
    if predicted != "correct":
        repair_result = run_repair_loop(
            spec=spec,
            correct_impl=correct_impl,
            task_description=description,
            function_name=function_name,
            buggy_impls=buggy_impls,
            max_iterations=3,
            verdict=predicted  # FIX 6: pass actual diagnosis so repair prompt is accurate
        )
        print(f"Repair: {'CONVERGED' if repair_result['converged'] else 'DID NOT CONVERGE'} "
              f"in {repair_result['iterations']} iterations")

    return {
        "task_id": task_id,
        "ground_truth": ground_truth,
        "predicted": predicted,
        "correct_diagnosis": correct_diagnosis,
        "signals": {"s1": s1, "s2": s2, "s3": s3, "s4": s4},
        "diagnosis": diagnosis,
        "repair": repair_result,
    }


def run_full_benchmark(output_path: str = "results/benchmark_results.json") -> dict:
    """Run pipeline on all 15 tasks. Save results. Print summary."""
    with open("benchmark.json") as f:
        data = json.load(f)
    tasks = data["benchmark"]["tasks"]

    results = []
    correct_count = 0
    repair_converged = 0
    repair_total = 0

    for task in tasks:
        result = run_pipeline(task, use_planted_spec=True)
        results.append(result)
        if result["correct_diagnosis"]:
            correct_count += 1
        if result["repair"]:
            repair_total += 1
            if result["repair"]["converged"]:
                repair_converged += 1

    accuracy = correct_count / len(tasks)
    repair_rate = repair_converged / repair_total if repair_total > 0 else 0

    summary = {
        "diagnostic_accuracy": accuracy,
        "correct_diagnoses": correct_count,
        "total_tasks": len(tasks),
        "repair_convergence_rate": repair_rate,
        "repair_converged": repair_converged,
        "repair_total": repair_total,
        "results": results
    }

    Path("results").mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"HEADLINE NUMBERS:")
    print(f"Diagnostic accuracy: {correct_count}/{len(tasks)} ({accuracy:.1%})")
    print(f"Repair convergence: {repair_converged}/{repair_total} ({repair_rate:.1%})")
    print(f"{'='*50}")

    return summary
