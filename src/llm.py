# src/llm.py
# FIX APPLIED: API key rotation on 429 quota errors
# Keys loaded from .env: GOOGLE_API_KEY, GOOGLE_API_KEY_1 ... GOOGLE_API_KEY_9
# Round-robin rotation — never crashes on quota, rotates and retries automatically

import os, time, hashlib, json
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

MODEL_NAME = "gemini-2.5-flash"
CACHE_FILE = Path(".llm_cache.json")
MIN_CALL_INTERVAL = 1.0  # seconds between calls (rate limit safety)
MAX_RETRIES = 3           # retries per call before giving up

# --- API key rotation ---
def _load_api_keys() -> list[str]:
    """Load all available API keys from environment. Primary key first."""
    keys = []
    primary = os.getenv("GOOGLE_API_KEY")
    if primary:
        keys.append(primary)
    for i in range(1, 10):
        k = os.getenv(f"GOOGLE_API_KEY_{i}")
        if k:
            keys.append(k)
    if not keys:
        raise RuntimeError(
            "No API key found. Set GOOGLE_API_KEY in .env"
        )
    return keys

_api_keys: list[str] = _load_api_keys()
_current_key_index: int = 0
_cache: dict = {}
_last_call_time: float = 0.0


def _get_current_key() -> str:
    return _api_keys[_current_key_index]


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
    global _last_call_time
    _load_cache()

    cache_key = hashlib.md5(f"{prompt}|{temperature}".encode()).hexdigest()

    if use_cache and cache_key in _cache:
        return _cache[cache_key]

    # Rate limiting
    elapsed = time.time() - _last_call_time
    if elapsed < MIN_CALL_INTERVAL:
        time.sleep(MIN_CALL_INTERVAL - elapsed)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            genai.configure(api_key=_get_current_key())
            model = genai.GenerativeModel(MODEL_NAME)
            config = genai.types.GenerationConfig(temperature=temperature)
            response = model.generate_content(prompt, generation_config=config)
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
            # 429 = quota exceeded, rotate key and retry immediately
            if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                print(f"[llm] Quota hit on key {_current_key_index}, rotating...")
                _rotate_key()
                time.sleep(2)  # brief pause before retry with new key
                continue
            # Other errors: wait and retry with same key
            print(f"[llm] API error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(5 * (attempt + 1))

    raise RuntimeError(
        f"Gemini 2.5 Flash failed after {MAX_RETRIES} attempts "
        f"across {len(_api_keys)} key(s). Last error: {last_error}"
    )
