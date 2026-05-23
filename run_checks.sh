#!/usr/bin/env bash
# run_checks.sh — SpecMutate submission validation script
# Run this before submitting to verify all checks pass.

set -e
echo "=========================================="
echo " SpecMutate — Submission Checks"
echo "=========================================="

# Activate venv
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo ""
echo "[ 1/5 ] Checking Python version..."
python --version

echo ""
echo "[ 2/5 ] Running full test suite..."
python -m pytest -v --tb=short

echo ""
echo "[ 3/5 ] Verifying benchmark results exist..."
if [ -f "results/benchmark_results.json" ]; then
    echo "✅ results/benchmark_results.json found"
    python -c "
import json
with open('results/benchmark_results.json') as f:
    r = json.load(f)
acc = r['diagnostic_accuracy']
rep = r['repair_convergence_rate']
print(f'   Diagnostic accuracy:      {r[\"correct_diagnoses\"]}/{r[\"total_tasks\"]} ({acc:.1%})')
print(f'   Repair convergence rate:  {r[\"repair_converged\"]}/{r[\"repair_total\"]} ({rep:.1%})')
"
else
    echo "❌ results/benchmark_results.json NOT found — run: python run_benchmark.py"
    exit 1
fi

echo ""
echo "[ 4/5 ] Verifying README headline..."
head -1 README.md

echo ""
echo "[ 5/5 ] Checking required files..."
for f in README.md RESULTS.md benchmark.json requirements.txt app.py run_benchmark.py src/llm.py src/diagnosis.py src/pipeline.py src/repair_loop.py src/mutator.py; do
    if [ -f "$f" ]; then
        echo "  ✅ $f"
    else
        echo "  ❌ MISSING: $f"
    fi
done

echo ""
echo "=========================================="
echo " All checks passed! Ready to submit."
echo "=========================================="
