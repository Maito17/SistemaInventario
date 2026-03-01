from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
import json


class RegistroUsuarioTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_registro_crea_usuario(self):
        url = reverse('usuarios:registro')
        data = {
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123'
        }
        resp = self.client.post(url, data)
        # Debe redirigir al dashboard tras login
        self.assertEqual(resp.status_code, 302)
        User = get_user_model()
        user = User.objects.filter(username='testuser').first()
        self.assertIsNotNone(user)
from django.test import TestCase

# Create your tests here.
