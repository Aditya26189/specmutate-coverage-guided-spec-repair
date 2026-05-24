# check_api_keys.py
"""
Gemini API Key Health Checker
Loads all keys from .env and performs a lightweight test request on each
to identify which keys are active, rate-limited, blocked, or invalid.
"""

import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

def load_keys() -> dict:
    """Load all configured API keys mapped to their environment variable names directly from .env."""
    import dotenv
    env_values = dotenv.dotenv_values(".env")
    keys_map = {}
    
    # Check primary key
    primary = env_values.get("GOOGLE_API_KEY")
    if primary:
        keys_map["GOOGLE_API_KEY"] = primary
        
    # Check secondary keys
    for i in range(1, 10):
        name = f"GOOGLE_API_KEY_{i}"
        key = env_values.get(name)
        if key:
            keys_map[name] = key
            
    return keys_map

def check_single_key(name: str, key: str) -> dict:
    """Test a single API key and return status and latency."""
    # Mask the key for safe printing
    masked = f"{key[:6]}...{key[-4:]}" if len(key) > 10 else "Invalid format"
    
    if len(key) <= 10:
        return {"status": "INVALID_FORMAT", "details": "Key is too short", "latency": 0.0, "masked": masked}

    start = time.time()
    try:
        genai.configure(api_key=key)
        # Use gemini-2.5-flash as the fast testing model
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            "Say 'OK' and nothing else.", 
            generation_config={"temperature": 0.0},
            request_options={"timeout": 10.0}
        )
        text = response.text.strip()
        elapsed = time.time() - start
        return {"status": "WORKING", "details": f"Responded: {repr(text)}", "latency": elapsed, "masked": masked}
    except Exception as e:
        elapsed = time.time() - start
        err_str = str(e).lower()
        
        if "403" in err_str or "forbidden" in err_str or "api_key_invalid" in err_str or "api key not valid" in err_str or "invalid api key" in err_str:
            status = "BLOCKED / INVALID (403)"
            details = "API key was rejected by Google (check spelling or billing status)"
        elif "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            status = "QUOTA EXCEEDED (429)"
            details = "Rate limit or usage threshold hit. Key needs a cooldown."
        else:
            status = "ERROR"
            details = str(e)
            
        return {"status": status, "details": details, "latency": elapsed, "masked": masked}

def main():
    print("\n" + "=" * 80)
    print("  Gemini API Key Health Check Diagnostic")
    print("  Evaluating all key slots loaded from .env...")
    print("=" * 80 + "\n")
    
    keys_map = load_keys()
    if not keys_map:
        print("  [ERROR] No keys found in .env! Please define GOOGLE_API_KEY.")
        print("=" * 80 + "\n")
        return

    working_count = 0
    results = {}
    
    for name, key in keys_map.items():
        print(f"  Checking {name:<17} ... ", end="", flush=True)
        res = check_single_key(name, key)
        results[name] = res
        
        if res["status"] == "WORKING":
            working_count += 1
            print(f"[\033[92mWORKING\033[0m] ({res['latency']:.2f}s) - {res['details']}")
        elif "BLOCKED" in res["status"]:
            print(f"[\033[91m{res['status']}\033[0m] - {res['details']}")
        elif "QUOTA" in res["status"]:
            print(f"[\033[93m{res['status']}\033[0m] - {res['details']}")
        else:
            print(f"[\033[95m{res['status']}\033[0m] - {res['details']}")

    print("\n" + "=" * 80)
    print("  Summary:")
    print(f"  Total keys scanned: {len(keys_map)}")
    print(f"  Working keys:       {working_count} / {len(keys_map)}")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
