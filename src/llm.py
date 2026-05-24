# src/llm.py
# FIX APPLIED: API key rotation on 429 quota errors
# Keys loaded from .env: GOOGLE_API_KEY, GOOGLE_API_KEY_1 ... GOOGLE_API_KEY_9
# Round-robin rotation — never crashes on quota, rotates and retries automatically

import os, time, hashlib, json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv(override=True)

# Model rotation: primary → fallback 1 → fallback 2
# When all keys hit quota on the active model, escalate to the next model.
MODEL_ROTATION_LIST = [
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
]
MODEL_NAME = MODEL_ROTATION_LIST[2]  # kept for backwards-compat references
CACHE_FILE = Path(".llm_cache.json")
MIN_CALL_INTERVAL = 1.0  # seconds between calls (rate limit safety)
MAX_RETRIES = 5           # retries per call before giving up

# --- API key rotation ---
def _load_api_keys() -> list[str]:
    """Load all available API keys directly from .env. Primary key first."""
    import dotenv
    env_values = dotenv.dotenv_values(".env")
    keys = []
    primary = env_values.get("GOOGLE_API_KEY")
    if primary:
        keys.append(primary)
    for i in range(1, 10):
        k = env_values.get(f"GOOGLE_API_KEY_{i}")
        if k:
            keys.append(k)
    if not keys:
        raise RuntimeError(
            "No API key found. Set GOOGLE_API_KEY in .env"
        )
    
    # Deduplicate keys while preserving order
    seen = set()
    unique_keys = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)
    return unique_keys

_api_keys: list[str] = _load_api_keys()
_current_key_index: int = 0
_current_model_index: int = 2  # index into MODEL_ROTATION_LIST
_cache: dict = {}
_last_call_time: float = 0.0
_last_quota_exhaustion_time: float = 0.0
COOLDOWN_PERIOD: float = 300.0  # 5 minutes


def _get_current_key() -> str:
    return _api_keys[_current_key_index]


def _get_active_model() -> str:
    return MODEL_ROTATION_LIST[_current_model_index]


def _rotate_model() -> str:
    """Escalate to the next model in MODEL_ROTATION_LIST. Resets key index."""
    global _current_model_index, _current_key_index, _last_quota_exhaustion_time
    _current_model_index = (_current_model_index + 1) % len(MODEL_ROTATION_LIST)
    _current_key_index = 0
    _last_quota_exhaustion_time = 0.0  # clear cooldown for new model
    new_model = MODEL_ROTATION_LIST[_current_model_index]
    print(f"[llm] *** Model rotated to: {new_model} ***")
    return new_model


def _rotate_key() -> str:
    """Rotate to the next available key. Returns the new key."""
    global _current_key_index
    _current_key_index = (_current_key_index + 1) % len(_api_keys)
    new_key = _api_keys[_current_key_index]
    print(f"[llm] Rotated to API key index {_current_key_index}")
    return new_key


def _load_cache() -> None:
    global _cache
    if CACHE_FILE.exists():
        try:
            _cache = json.loads(CACHE_FILE.read_text())
        except json.JSONDecodeError:
            _cache = {}


def _save_cache() -> None:
    CACHE_FILE.write_text(json.dumps(_cache, indent=2))


def clear_cache() -> None:
    global _cache
    _cache = {}
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()


def strip_fences(text: str) -> str:
    """Remove markdown code fences from LLM response."""
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()




def call_llm(
    prompt: str,
    temperature: float = 0.0,
    use_cache: bool = True,
    strip_markdown: bool = True,
) -> str:
    global _last_call_time, _current_key_index, _current_model_index, _last_quota_exhaustion_time
    _load_cache()

    cache_key = hashlib.md5(f"{prompt}|{temperature}".encode()).hexdigest()

    if use_cache and cache_key in _cache:
        return _cache[cache_key]

    # Circuit breaker: all keys exhausted on ALL models
    all_models_exhausted = (
        _current_model_index == len(MODEL_ROTATION_LIST) - 1
        and time.time() - _last_quota_exhaustion_time < COOLDOWN_PERIOD
    )
    if all_models_exhausted:
        remaining = COOLDOWN_PERIOD - (time.time() - _last_quota_exhaustion_time)
        raise RuntimeError(
            f"[llm] All keys exhausted on all models ({MODEL_ROTATION_LIST}). "
            f"{remaining:.0f}s cooldown remaining."
        )

    # Rate limiting
    elapsed = time.time() - _last_call_time
    if elapsed < MIN_CALL_INTERVAL:
        time.sleep(MIN_CALL_INTERVAL - elapsed)

    last_error = None
    attempt = 0
    keys_tried = set()
    while attempt < MAX_RETRIES:
        if not _api_keys:
            raise RuntimeError("No API keys remaining in list.")
        
        current_key = _get_current_key()
        keys_tried.add(current_key)
        active_model = _get_active_model()
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel(active_model)
            config = genai.types.GenerationConfig(temperature=temperature)
            response = model.generate_content(
                prompt,
                generation_config=config,
                request_options={"timeout": 120.0}
            )
            result = response.text
            _last_call_time = time.time()

            if strip_markdown:
                result = strip_fences(result)

            if use_cache:
                _cache[cache_key] = result
                _save_cache()

            return result

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            
            # Catch 403 / Forbidden / blocked / invalid API key
            if "403" in err_str or "forbidden" in err_str or "api_key_invalid" in err_str or "api key not valid" in err_str or "invalid api key" in err_str:
                print(f"[llm] API key blocked/invalid (403) at index {_current_key_index}, removing permanently.")
                if current_key in _api_keys:
                    _api_keys.remove(current_key)
                if not _api_keys:
                    raise RuntimeError("All configured API keys have been removed (all failed with 403/Forbidden/Invalid Key).")
                _current_key_index = _current_key_index % len(_api_keys)
                # Note: We do NOT increment attempt, we just retry with the next available key
                continue

            # 429 = quota exceeded, rotate key; if all keys exhausted, rotate model
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                if len(keys_tried) >= len(_api_keys):
                    # All keys hit quota on current model — try next model
                    next_model = _rotate_model()
                    keys_tried.clear()
                    attempt += 1
                    print(f"[llm] All keys quota-hit on {active_model}. Switched to {next_model}. Sleeping 5s...")
                    time.sleep(5)
                else:
                    print(f"[llm] Quota hit on key index {_current_key_index} ({active_model}), rotating key...")
                    _rotate_key()
                    time.sleep(2)  # brief pause before retry with new key
                continue
                
            # Other errors: wait and retry with same key
            print(f"[llm] API error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(5 * (attempt + 1))
            attempt += 1

    raise RuntimeError(
        f"[llm] All models {MODEL_ROTATION_LIST} failed after {MAX_RETRIES} total attempts. "
        f"Last error: {last_error}"
    )
