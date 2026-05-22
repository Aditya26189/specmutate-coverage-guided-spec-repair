# src/mutator.py
# Coverage-guided mutation engine
# Three operators: FlipComparison, RemovePrecondition, RemovePostcondition
# Scores by coverage DELTA, not pass count
# Highest delta = the bad constraint

import ast, re, subprocess, sys, tempfile, json
from pathlib import Path
from copy import deepcopy


# FIX 5 APPLIED: original approach used f-string to inline impl/spec into the runner
# script. Any impl or spec containing { or } (dict literal, set, f-string, comprehension)
# corrupts the f-string and returns empty coverage sets, making all deltas 0.
# Fix: use ###PLACEHOLDER### substitution — same technique already proven in runner.py.
_COVERAGE_TEMPLATE = '''
import coverage, json, sys

cov = coverage.Coverage(branch=True)
cov.start()

###IMPL_CODE###

from hypothesis import given, settings, strategies as st, assume
###SPEC_CODE###

if __name__ == "__main__":
    try:
        import inspect
        test_fn = None
        for name, obj in list(globals().items()):
            if name.startswith("test_") and callable(obj):
                test_fn = obj
                break
        if test_fn:
            test_fn()
    except Exception:
        pass
    finally:
        cov.stop()
        data = cov.get_data()
        covered = set()
        for f in data.measured_files():
            lines = data.lines(f)
            if lines:
                covered.update(lines)
        print(json.dumps(list(covered)))
'''


def _measure_coverage(impl: str, spec: str, timeout: int = 15) -> set:
    """
    Run spec against impl with coverage.py in subprocess.
    Returns set of covered line numbers in the impl.
    Uses placeholder substitution — safe for impl/spec containing {curly braces},
    dict literals, f-strings, set comprehensions. Never use f-string here.
    """
    script = _COVERAGE_TEMPLATE.replace(
        "###IMPL_CODE###", impl
    ).replace(
        "###SPEC_CODE###", spec
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        tmp = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True, timeout=timeout
        )
        if result.stdout.strip():
            return set(json.loads(result.stdout.strip()))
        return set()
    except Exception:
        return set()
    finally:
        Path(tmp).unlink(missing_ok=True)


def _flip_comparisons(spec: str) -> list[dict]:
    """FlipComparison: flip >, <, >=, <=, ==, != in assert statements."""
    mutations = []
    flips = {">": ">=", ">=": ">", "<": "<=", "<=": "<", "==": "!=", "!=": "=="}

    for original, replacement in flips.items():
        pattern = rf'assert\s+.*{re.escape(original)}'
        for match in re.finditer(pattern, spec):
            mutated = spec[:match.start()] + \
                      match.group().replace(original, replacement, 1) + \
                      spec[match.end():]
            mutations.append({
                "operator": "FlipComparison",
                "original": match.group(),
                "mutated": match.group().replace(original, replacement, 1),
                "mutated_spec": mutated
            })
    return mutations


def _remove_preconditions(spec: str) -> list[dict]:
    """RemovePrecondition: remove assume() calls and min/max value restrictions."""
    mutations = []

    # Remove assume() lines
    for line in spec.split("\n"):
        if "assume(" in line:
            mutated = spec.replace(line + "\n", "").replace(line, "")
            mutations.append({
                "operator": "RemovePrecondition",
                "original": line,
                "mutated": "",
                "mutated_spec": mutated
            })

    # Widen min_value/max_value in @given strategies
    for pattern, replacement in [
        (r'min_value=\d+', 'min_value=0'),
        (r'min_size=\d+', 'min_size=0'),
    ]:
        for match in re.finditer(pattern, spec):
            if match.group() != replacement:
                mutated = spec[:match.start()] + replacement + spec[match.end():]
                mutations.append({
                    "operator": "RemovePrecondition",
                    "original": match.group(),
                    "mutated": replacement,
                    "mutated_spec": mutated
                })
    return mutations


def _remove_postconditions(spec: str) -> list[dict]:
    """RemovePostcondition: remove individual assert statements."""
    mutations = []
    lines = spec.split("\n")

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("assert "):
            remaining = "\n".join(lines[:i] + lines[i+1:])
            mutations.append({
                "operator": "RemovePostcondition",
                "original": stripped,
                "mutated": "",
                "mutated_spec": remaining
            })
    return mutations


def apply_mutations(spec: str, impl: str) -> list[dict]:
    """
    Apply all three mutation operators.
    Score each mutation by coverage delta against the correct implementation.
    Return sorted list (highest delta first).
    """
    baseline_coverage = _measure_coverage(impl=impl, spec=spec)

    all_mutations = (
        _flip_comparisons(spec) +
        _remove_preconditions(spec) +
        _remove_postconditions(spec)
    )

    scored = []
    for mutation in all_mutations:
        mutated_coverage = _measure_coverage(
            impl=impl, spec=mutation["mutated_spec"]
        )
        # Coverage delta: how many new branches become covered after mutation
        new_branches = mutated_coverage - baseline_coverage
        delta = len(new_branches)
        mutation["coverage_delta"] = delta
        mutation["newly_covered_lines"] = list(new_branches)
        scored.append(mutation)

    return sorted(scored, key=lambda m: m["coverage_delta"], reverse=True)


def identify_bad_constraint(spec: str, impl: str) -> dict | None:
    """
    Return the mutation with highest coverage delta.
    This is the bad constraint — the one whose removal reveals the most.
    Returns None if no mutations produce coverage delta > 0.
    """
    mutations = apply_mutations(spec=spec, impl=impl)
    if mutations and mutations[0]["coverage_delta"] > 0:
        return mutations[0]
    return None
