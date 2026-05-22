# src/signal2.py
# Oracle-guided variant discrimination
# Input-guided divergence prompting — implementations guided by actual Hypothesis inputs

from itertools import combinations
from src.runner import run_spec_against_impl


def compute_discrimination_score(
    spec: str,
    implementations: list[str]
) -> float:
    """
    S2: What fraction of implementation pairs does the spec DISTINGUISH?
    (One passes, one fails = distinguished. Both pass or both fail = not distinguished.)
    Score = distinguished_pairs / total_pairs
    Low score = spec cannot tell good from bad implementations.
    High score = spec is discriminating.
    """
    if len(implementations) < 2:
        return 0.0

    pairs = list(combinations(range(len(implementations)), 2))
    results = {}

    for i, impl in enumerate(implementations):
        r = run_spec_against_impl(spec=spec, impl=impl)
        results[i] = r["passed"]

    distinguished = 0
    for i, j in pairs:
        if results[i] != results[j]:
            distinguished += 1

    return distinguished / len(pairs)
