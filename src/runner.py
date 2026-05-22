# src/runner.py
# SUBPROCESS ISOLATION — do not call Hypothesis inline.
# FIX APPLIED: use placeholder replacement instead of .format() to avoid
# KeyError when impl or spec contain curly braces (dicts, f-strings, etc.)

import subprocess, sys, tempfile, json
from pathlib import Path


# Use unique placeholders that CANNOT appear in Python source code.
# Never use .format() on code strings — they may contain {curly braces}.
RUNNER_TEMPLATE = '''
import json, sys
from hypothesis import given, settings, assume, strategies as st, HealthCheck

###IMPL_CODE###

###SPEC_CODE###

if __name__ == "__main__":
    try:
        import inspect
        test_fn = None
        for name, obj in list(globals().items()):
            if name.startswith("test_") and callable(obj):
                test_fn = obj
                break
        if test_fn is None:
            print(json.dumps({"passed": False, "error": "No test function found",
                               "counterexample": None}))
            sys.exit(1)
        test_fn()
        print(json.dumps({"passed": True, "counterexample": None, "error": None}))
    except Exception as e:
        msg = str(e)
        counterexample = None
        if "Falsifying example" in msg:
            counterexample = msg
        print(json.dumps({"passed": False, "counterexample": counterexample,
                           "error": msg}))
'''


def run_spec_against_impl(
    spec: str,
    impl: str,
    timeout: int = 30
) -> dict:
    """
    Run a Hypothesis spec against an implementation in a subprocess.
    Returns: {"passed": bool, "counterexample": str|None, "error": str|None}
    Uses placeholder replacement — safe for impls containing {}, f-strings, dicts.
    """
    # SAFE: placeholder replacement, never .format() on user-supplied code
    script = RUNNER_TEMPLATE.replace("###IMPL_CODE###", impl).replace(
        "###SPEC_CODE###", spec
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                    delete=False) as f:
        f.write(script)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True, timeout=timeout
        )
        stdout = result.stdout.strip()
        if not stdout:
            return {
                "passed": False,
                "counterexample": None,
                "error": result.stderr.strip()[:500]
            }
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        return {"passed": False, "counterexample": None,
                "error": f"Timed out after {timeout}s"}
    except json.JSONDecodeError:
        return {"passed": False, "counterexample": None,
                "error": f"Bad output: {result.stdout[:200]}"}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
