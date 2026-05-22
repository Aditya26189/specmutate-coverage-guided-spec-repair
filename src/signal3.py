# src/signal3.py
# CrossHair symbolic refutation
# Uses crosshair-tool for contract checking
# HEALTH CHECK GATE: if CrossHair fails on a known case, mark N/A for all tasks

import subprocess, sys, tempfile
from pathlib import Path

HEALTH_CHECK_CODE = '''
def double(x: int) -> int:
    """
    pre: x > 0
    post: __return__ > x
    """
    return x * 2
'''


def crosshair_health_check() -> bool:
    """Returns True if CrossHair is functional, False otherwise."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                    delete=False) as f:
        f.write(HEALTH_CHECK_CODE)
        tmp = f.name
    try:
        # Check using crosshair command from our virtual environment's Scripts if it exists,
        # or fall back to system crosshair command.
        # Inside the venv, crosshair is installed in venv/Scripts/crosshair.exe.
        # Let's try running crosshair.
        cmd = "crosshair"
        # We can construct path to crosshair in the virtual environment relative to the file.
        # The workspace is c:\Users\LawLight\Desktop\sps hackathon.
        # The crosshair path is c:\Users\LawLight\Desktop\sps hackathon\venv\Scripts\crosshair.exe.
        # Using that is safer. Let's resolve it.
        venv_crosshair = Path("c:/Users/LawLight/Desktop/sps hackathon/venv/Scripts/crosshair.exe")
        if venv_crosshair.exists():
            cmd = str(venv_crosshair)

        result = subprocess.run(
            [cmd, "check", tmp],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0 or "Counterexample" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    finally:
        Path(tmp).unlink(missing_ok=True)


def compute_crosshair_score(function_code: str) -> dict:
    """
    Run CrossHair on a function with contracts.
    Returns: {"available": bool, "counterexample": str|None, "score": float}
    score=1.0 if CrossHair finds a counterexample (spec is refutable = bad spec)
    score=0.0 if CrossHair confirms spec (no counterexample found)
    score=0.5 if CrossHair is unavailable (N/A)
    """
    if not crosshair_health_check():
        return {"available": False, "counterexample": None, "score": 0.5}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                    delete=False) as f:
        f.write(function_code)
        tmp = f.name
    try:
        cmd = "crosshair"
        venv_crosshair = Path("c:/Users/LawLight/Desktop/sps hackathon/venv/Scripts/crosshair.exe")
        if venv_crosshair.exists():
            cmd = str(venv_crosshair)

        result = subprocess.run(
            [cmd, "check", tmp],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        if "Counterexample" in output or "cannot be satisfied" in output:
            return {"available": True, "counterexample": output[:500], "score": 1.0}
        return {"available": True, "counterexample": None, "score": 0.0}
    except subprocess.TimeoutExpired:
        return {"available": True, "counterexample": None, "score": 0.5}
    finally:
        Path(tmp).unlink(missing_ok=True)
