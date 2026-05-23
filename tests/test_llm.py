# tests/test_llm.py
import time, pytest
from src.llm import call_llm, clear_cache, strip_fences, _load_api_keys

def test_api_keys_loaded():
    """At least one API key must be present."""
    keys = _load_api_keys()
    assert len(keys) >= 1
    assert all(isinstance(k, str) and len(k) > 10 for k in keys)

def test_fence_stripping():
    """LLM response with markdown fences must return clean code."""
    raw = "```python\ndef foo():\n    return 1\n```"
    result = strip_fences(raw)
    assert "```" not in result
    assert "def foo():" in result

def test_cache_hit_is_fast():
    """Second call with same prompt must return in under 0.5 seconds."""
    import shutil
    from pathlib import Path
    cache_path = Path(".llm_cache.json")
    backup_path = Path(".llm_cache.json.bak")
    if cache_path.exists():
        shutil.copy(cache_path, backup_path)
    try:
        clear_cache()
        prompt = "Return the number 42. Nothing else."
        call_llm(prompt)  # warm the cache
        start = time.time()
        call_llm(prompt)  # should hit cache
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Cache hit took {elapsed:.2f}s — too slow"
    finally:
        if backup_path.exists():
            shutil.move(backup_path, cache_path)

def test_returns_string():
    prompt = "Return the word hello. Nothing else."
    result = call_llm(prompt)
    assert isinstance(result, str)
    assert len(result) > 0

def test_rate_limiter_allows_calls():
    """Three sequential calls must all succeed without exception."""
    for i in range(3):
        result = call_llm(f"Return the number {i}. Nothing else.")
        assert isinstance(result, str)
