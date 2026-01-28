
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')
django.setup()
from possitema.models import Plan

# Crear planes si no existen
Plan.objects.get_or_create(nombre='Bronce', defaults={
    'precio': 15.00,
    'duracion_dias': 30,
    'limite_usuarios': 1,
    'limite_productos': 50
})
Plan.objects.get_or_create(nombre='Plata', defaults={
    'precio': 23.00,
    'duracion_dias': 30,
    'limite_usuarios': 3,
    'limite_productos': 500
})
Plan.objects.get_or_create(nombre='Oro', defaults={
    'precio': 35.00,
    'duracion_dias': 30,
    'limite_usuarios': None,
    'limite_productos': None
})
print('Planes creados o actualizados.')
