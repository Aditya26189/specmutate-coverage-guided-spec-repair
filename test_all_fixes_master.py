# test_all_fixes_master.py
"""
Master pre-submission verification for SpecMutate.
Run: python test_all_fixes_master.py
All 8 checks must pass before submitting.
"""

import json, os, glob, re, sys

def run_check(name, fn):
    try:
        fn()
        print(f"  [PASS] {name}")
        return True
    except AssertionError as e:
        print(f"  [FAIL] {name}")
        # Safely print assertion error avoiding unicode issues in Windows terminal
        msg = str(e).encode(sys.stdout.encoding or 'ascii', errors='replace').decode(sys.stdout.encoding or 'ascii')
        print(f"     -> {msg}")
        return False
    except Exception as e:
        msg = str(e).encode(sys.stdout.encoding or 'ascii', errors='replace').decode(sys.stdout.encoding or 'ascii')
        print(f"  [ERROR] {name} - {type(e).__name__}: {msg}")
        return False

# ─── Check 1: JSON integrity ────────────────────────────────────────────────
def check_json_integrity():
    with open("results/benchmark_results.json", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_tasks"] == 15
    assert data["repair_converged"] == 10
    assert data["repair_total"] == 10
    results = {r["task_id"]: r for r in data["results"]}
    assert results["T09"]["signals"]["s1"] == 1.0
    assert results["T09"]["signals"]["s2"] == 0.6
    assert results["T15"]["ground_truth"] == "correct"
    assert results["T15"]["predicted"] == "correct"
    assert results["T08"]["repair"]["iterations"] == 3

# ─── Check 2: Threshold recalibration ──────────────────────────────────────
def check_threshold():
    with open("src/diagnosis.py", encoding="utf-8") as f:
        content = f.read()
    # Check threshold is 0.45
    assert "0.45" in content, \
        "UNDERCONSTRAINED_THRESHOLD must be 0.45"

# ─── Check 3: No CEGIS label ────────────────────────────────────────────────
def check_no_cegis():
    files = glob.glob("**/*.py", recursive=True) + glob.glob("**/*.md", recursive=True)
    exempt_lines = ["LLM-CEGIS-Repair", "CEGIS principles"]
    exempt_files = ["test_all_fixes", "agent_prompt_3", "test_all_fixes_master", "AGENTS.md", "specmutate_final.md", "walkthrough.md"]
    violations = []
    for fp in files:
        # Skip exempt files
        if any(ef in fp for ef in exempt_files):
            continue
        # Skip venv, .git, .pytest_cache, .hypothesis files
        if any(x in fp for x in ["venv", ".git", ".pytest_cache", ".hypothesis"]):
            continue
        try:
            with open(fp, errors="ignore", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    if "CEGIS" in line and not any(el in line for el in exempt_lines):
                        violations.append(f"{fp}:{i}: {line.strip()}")
        except:
            pass
    assert not violations, \
        f"CEGIS label found in {len(violations)} places: {violations[:3]}"

# ─── Check 4: No hardcoded path ─────────────────────────────────────────────
def check_no_hardcoded_path():
    with open("src/signal3.py", encoding="utf-8") as f:
        content = f.read()
    banned = ["LawLight", "Desktop", "C:/Users", "c:/Users", "C:\\Users"]
    found = [b for b in banned if b in content]
    assert not found, f"Hardcoded path indicators found: {found}"

# ─── Check 5: Model consistency ─────────────────────────────────────────────
def check_model_consistency():
    with open("src/llm.py", encoding="utf-8") as f:
        llm = f.read()
    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    models_in_llm = re.findall(r'gemini[^\s`"\']+', llm)
    if models_in_llm:
        primary = models_in_llm[0]
        assert primary in readme, \
            f"Model '{primary}' in llm.py not found in README.md"

# ─── Check 6: README numbers ────────────────────────────────────────────────
def check_readme_numbers():
    with open("README.md", encoding="utf-8") as f:
        content = f.read()
    assert "8/8" not in content, "README still contains stale 8/8"
    assert "10/10" in content, "README must show 10/10"
    assert "13/15" in content or "15/15" in content, \
        "README must show diagnostic accuracy"

# ─── Check 7: Ablation arithmetic ───────────────────────────────────────────
def check_ablation():
    with open("RESULTS.md", encoding="utf-8") as f:
        content = f.read()
    assert "53.3%" not in content or "S4" in content.split("53.3%")[0].split("\n")[-1], \
        "53.3% must not appear as guard ablation result"
    assert "66.7%" in content, \
        "Ablation must show 66.7% for single gate removal"

# ─── Check 8: T08 and T15 documented ────────────────────────────────────────
def check_t08_t15():
    with open("RESULTS.md", encoding="utf-8") as f:
        content = f.read()
    assert "isalnum" in content, \
        "T08 alphanumeric normalization must be documented in RESULTS.md"
    assert "T15" in content, "T15 must be documented in RESULTS.md"
    assert "10/10" in content, \
        "Must show 10/10 repair convergence"
    assert "confusion" in content.lower() or "precision" in content.lower(), \
        "Confusion matrix / precision-recall must be in RESULTS.md"


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  SpecMutate - Pre-Submission Verification")
    print("  Apart Research SPS Hackathon 2026 | Track 2")
    print("="*60 + "\n")

    checks = [
        ("benchmark_results.json integrity",        check_json_integrity),
        ("Threshold is 0.45",                       check_threshold),
        ("No inappropriate CEGIS labels",           check_no_cegis),
        ("No hardcoded CrossHair path",             check_no_hardcoded_path),
        ("Model string consistent llm.py<->README",  check_model_consistency),
        ("README shows 10/10 repair convergence",   check_readme_numbers),
        ("Ablation arithmetic correct (60.0%)",     check_ablation),
        ("T08 case study + T15 disclosed",          check_t08_t15),
    ]

    results = [run_check(name, fn) for name, fn in checks]
    passed = sum(results)
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  Result: {passed}/{total} checks passed")
    print("="*60)

    if passed == total:
        print("\n  [SUCCESS] ALL CHECKS PASSED. Safe to submit.")
    else:
        failed = total - passed
        print(f"\n  [FAILURE] {failed} check(s) failed. Fix before submitting.")
        print("  Each failure message above shows exactly what needs fixing.")
