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


OP_MAP = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt
}

class FlipComparisonTransformer(ast.NodeTransformer):
    def __init__(self, target_index: int):
        self.target_index = target_index
        self.current_index = 0
        self.original_node_str = ""
        self.mutated_node_str = ""

    def visit_Compare(self, node):
        if node.ops and type(node.ops[0]) in OP_MAP:
            if self.current_index == self.target_index:
                self.original_node_str = ast.unparse(node)
                op_type = type(node.ops[0])
                new_op = OP_MAP[op_type]()
                new_node = ast.Compare(
                    left=node.left,
                    ops=[new_op] + node.ops[1:],
                    comparators=node.comparators
                )
                self.mutated_node_str = ast.unparse(new_node)
                self.current_index += 1
                return new_node
            self.current_index += 1
        return self.generic_visit(node)


class RemovePreconditionTransformer(ast.NodeTransformer):
    def __init__(self, target_index: int):
        self.target_index = target_index
        self.current_index = 0
        self.original_node_str = ""
        self.mutated_node_str = ""

    def visit_Call(self, node):
        # 1. Check if it is assume(...) call
        if isinstance(node.func, ast.Name) and node.func.id == "assume":
            if self.current_index == self.target_index:
                self.original_node_str = ast.unparse(node)
                self.mutated_node_str = "pass"
                self.current_index += 1
                return ast.Pass()
            self.current_index += 1

        # 2. Check strategy keyword arguments like min_value or min_size
        new_keywords = []
        modified = False
        for kw in node.keywords:
            if kw.arg in ("min_value", "min_size"):
                if self.current_index == self.target_index:
                    self.original_node_str = f"{kw.arg}={ast.unparse(kw.value)}"
                    self.mutated_node_str = f"{kw.arg}=0"
                    new_kw = ast.keyword(arg=kw.arg, value=ast.Constant(value=0))
                    new_keywords.append(new_kw)
                    modified = True
                    self.current_index += 1
                    continue
                self.current_index += 1
            new_keywords.append(kw)

        if modified:
            new_node = ast.Call(
                func=node.func,
                args=node.args,
                keywords=new_keywords
            )
            return new_node

        return self.generic_visit(node)


class RemovePostconditionTransformer(ast.NodeTransformer):
    def __init__(self, target_index: int):
        self.target_index = target_index
        self.current_index = 0
        self.original_node_str = ""
        self.mutated_node_str = ""

    def visit_Assert(self, node):
        if self.current_index == self.target_index:
            self.original_node_str = ast.unparse(node)
            self.mutated_node_str = "pass"
            self.current_index += 1
            return ast.Pass()
        self.current_index += 1
        return self.generic_visit(node)


def _flip_comparisons(spec: str) -> list[dict]:
    mutations = []
    target_index = 0
    while True:
        try:
            tree = ast.parse(spec)
        except SyntaxError:
            break
        transformer = FlipComparisonTransformer(target_index)
        mutated_tree = transformer.visit(tree)
        if transformer.original_node_str == "":
            break
        ast.fix_missing_locations(mutated_tree)
        mutated_spec = ast.unparse(mutated_tree)
        mutations.append({
            "operator": "FlipComparison",
            "original": transformer.original_node_str,
            "mutated": transformer.mutated_node_str,
            "mutated_spec": mutated_spec
        })
        target_index += 1
    return mutations


def _remove_preconditions(spec: str) -> list[dict]:
    mutations = []
    target_index = 0
    while True:
        try:
            tree = ast.parse(spec)
        except SyntaxError:
            break
        transformer = RemovePreconditionTransformer(target_index)
        mutated_tree = transformer.visit(tree)
        if transformer.original_node_str == "":
            break
        ast.fix_missing_locations(mutated_tree)
        mutated_spec = ast.unparse(mutated_tree)
        mutations.append({
            "operator": "RemovePrecondition",
            "original": transformer.original_node_str,
            "mutated": transformer.mutated_node_str,
            "mutated_spec": mutated_spec
        })
        target_index += 1
    return mutations


def _remove_postconditions(spec: str) -> list[dict]:
    mutations = []
    target_index = 0
    while True:
        try:
            tree = ast.parse(spec)
        except SyntaxError:
            break
        transformer = RemovePostconditionTransformer(target_index)
        mutated_tree = transformer.visit(tree)
        if transformer.original_node_str == "":
            break
        ast.fix_missing_locations(mutated_tree)
        mutated_spec = ast.unparse(mutated_tree)
        mutations.append({
            "operator": "RemovePostcondition",
            "original": transformer.original_node_str,
            "mutated": transformer.mutated_node_str,
            "mutated_spec": mutated_spec
        })
        target_index += 1
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
