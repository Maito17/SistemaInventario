import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("Error: No se encontró GEMINI_API_KEY en el entorno.")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"Consultando modelos disponibles para la llave: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-4:]}")
    try:
        modelos = list(genai.list_models())
        if not modelos:
            print("No se encontraron modelos disponibles.")
        else:
            for m in modelos:
                if 'generateContent' in m.supported_generation_methods:
                    print(f"Modelo: {m.name}")
    except Exception as e:
        print(f"Error al listar modelos: {e}")
