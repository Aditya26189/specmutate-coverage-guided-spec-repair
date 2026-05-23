import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_primary_api_key():
    """
    Tests only the primary GOOGLE_API_KEY.
    """
    api_key = "AIzaSyDpnHRhanH_WaQ26Y9LGui11jDXm2l2f8Y"

    if not api_key:
        print("Error: GOOGLE_API_KEY not found in your .env file.")
        return

    print("--- Testing GOOGLE_API_KEY ---")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content("Hello, world!")
        
        if response.text:
            print("✅ Success: GOOGLE_API_KEY is working correctly.")
        else:
            print("⚠️ Warning: GOOGLE_API_KEY produced an empty response.")

    except Exception as e:
        print(f"❌ Error with GOOGLE_API_KEY: {e}")
    
    print("-" * 30)

if __name__ == "__main__":
    test_primary_api_key()