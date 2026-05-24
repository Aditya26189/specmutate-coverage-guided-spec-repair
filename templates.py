# templates.py
# Repair prompt template — grounded feedback-guided repair
# DO NOT modify this string without updating AGENTS.md

REPAIR_PROMPT = """You are repairing a Python Hypothesis specification that has been \
diagnosed as {verdict}.

TASK DESCRIPTION: {task_description}

CURRENT (BROKEN) SPEC:
{current_spec}

DIAGNOSIS:
- Verdict: {verdict}
- S1 Completeness Score: {s1_score:.2f} (low = spec accepts wrong outputs)
- S2 Discrimination Score: {s2_score:.2f} (low = spec cannot distinguish implementations)
- S4 Stability Score: {s4_score:.2f} (low = spec is inconsistent across generations)

BAD CONSTRAINT IDENTIFIED BY MUTATION ENGINE:
AST node: {bad_ast_node}
Operator applied: {mutation_operator}
Coverage delta from this mutation: {coverage_delta:.4f}

COUNTEREXAMPLE INPUT that revealed the spec failure:
{counterexample}

WHAT THE CORRECT IMPLEMENTATION RETURNS ON THIS INPUT:
{correct_output}

WHAT THE BUGGY IMPLEMENTATION RETURNS ON THIS INPUT (that the spec incorrectly accepted):
{buggy_output}

YOUR TASK:
Return ONLY a corrected Python Hypothesis spec. The spec must:
1. Import from hypothesis correctly
2. Use @given decorator with st strategies
3. Contain at least one assert statement stronger than the current spec
4. Be runnable with: exec(spec_string) then hypothesis.core.find()
5. NOT contain markdown fences, explanations, or comments

CORRECTED SPEC:"""


SPEC_GEN_PROMPT = """Generate a Python Hypothesis property-based test specification \
for the following function.

FUNCTION DESCRIPTION: {description}

Requirements:
- Use `from hypothesis import given, settings, assume` and `from hypothesis import strategies as st`
- The function under test is named `{function_name}`
- Include at least one @given decorator with appropriate strategies
- Include at least two assert statements checking postconditions
- Include assume() statements for any necessary preconditions
- Do NOT implement the function itself
- Do NOT include markdown fences or explanations

Return ONLY the Python test function code."""


IMPL_GEN_PROMPT = """Generate {n} different Python implementations of the following \
function. The implementations should be meaningfully different — use different \
algorithms, data structures, or approaches.

FUNCTION DESCRIPTION: {description}
FUNCTION SIGNATURE: {signature}

ORACLE INPUTS (inputs that a correct Hypothesis spec generates — your implementations \
MUST disagree on at least some of these):
{oracle_inputs}

Requirements:
- Each implementation must have the exact function signature shown
- Implementations should intentionally vary in correctness — some may be buggy
- Return as a JSON array of strings, each string being one complete Python function
- Do NOT include markdown fences

JSON ARRAY OF IMPLEMENTATIONS:"""


COVERAGE_REPAIR_CONTEXT = """Additional context for repair:
Uncovered branches in the correct implementation under the current spec:
{uncovered_branches}

These branches being uncovered means the spec's input strategy is too narrow \
(overconstrained precondition) or the postcondition fails to exercise these paths."""
