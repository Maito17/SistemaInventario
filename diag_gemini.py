import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
print(f"Testing with key starting with: {api_key[:10]}...")

genai.configure(api_key=api_key)

print("\n--- Available Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model: {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")

print("\n--- Testing gemini-1.5-flash ---")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content('Hi')
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error with gemini-1.5-flash: {e}")

print("\n--- Testing gemini-1.5-flash-latest ---")
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    response = model.generate_content('Hi')
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error with gemini-1.5-flash-latest: {e}")
