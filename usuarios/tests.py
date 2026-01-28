from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from possitema.models import Plan, Suscripcion
from django.utils import timezone
import json


class RegistroConTrialTestCase(TestCase):
    def setUp(self):
        # Crear plan por defecto
        self.plan = Plan.objects.create(nombre='Bronce', precio='0.00', duracion_dias=30)
        self.client = Client()

    def test_registro_crea_suscripcion_trial(self):
        url = reverse('usuarios:registro')
        data = {
            'username': 'trialuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'trial@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        resp = self.client.post(url, data)
        # Debe redirigir al dashboard tras login
        self.assertEqual(resp.status_code, 302)
        User = get_user_model()
        user = User.objects.filter(username='trialuser').first()
        self.assertIsNotNone(user)
        sus = Suscripcion.objects.filter(user=user).first()
        self.assertIsNotNone(sus)
        # verificar duración ~30 días
        self.assertTrue((sus.fecha_vencimiento - sus.fecha_inicio).days >= 29)
from django.test import TestCase

# Create your tests here.
