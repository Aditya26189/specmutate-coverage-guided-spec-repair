# tests/test_pipeline.py
import json
from src.pipeline import run_pipeline

def test_pipeline_runs_on_sample_task():
    """Verify that run_pipeline executes successfully on a benchmark task."""
    with open("benchmark.json") as f:
        data = json.load(f)
    # Grab T01 (merge_sorted_lists) or another task
    task = data["benchmark"]["tasks"][0]
    
    result = run_pipeline(task, use_planted_spec=True)
    
    assert "task_id" in result
    assert "predicted" in result
    assert "correct_diagnosis" in result
    assert "signals" in result
    assert "diagnosis" in result
