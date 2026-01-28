
import os
import json
import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


PROMPT_BASE = (
    "Eres un asistente experto en ventas, estrategias comerciales, recuperación de clientes y análisis de mercado. "
    "Solo puedes responder preguntas relacionadas con ventas, marketing, promociones, estrategias de negocio y recuperación de mercado. "
    "No respondas preguntas fuera de ese ámbito. Sé claro, profesional y enfocado en ayudar a mejorar las ventas.\n"
)

@csrf_exempt
@require_POST
def ia_ventas(request):
    data = json.loads(request.body)
    pregunta = data.get('pregunta', '')
    if not pregunta:
        return JsonResponse({'error': 'Pregunta vacía'}, status=400)

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        return JsonResponse({'error': 'No se encontró GEMINI_API_KEY'}, status=500)

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-flash-latest")

    prompt = PROMPT_BASE + f"\nPregunta: {pregunta}\nRespuesta:"
    try:
        response = model.generate_content(prompt)
        respuesta = response.text.strip()
        return JsonResponse({'respuesta': respuesta})
    except Exception as e:
        print('Error IA Gemini:', str(e))
        return JsonResponse({'error': str(e)}, status=500)
