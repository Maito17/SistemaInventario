from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

from .models import Plan, RegistroPago, Suscripcion
from .models import WebhookLog


@override_settings(PAYMENT_WEBHOOK_TOKEN='test-token')
class WebhookActivarPagoTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='webhookuser', password='pass', email='webhook@example.com')
        # Crear un plan válido (usar uno de los choices)
        self.plan = Plan.objects.create(nombre='Bronce', precio='10.00', duracion_dias=30)
        self.client = Client()

    def test_webhook_activa_suscripcion_y_registra_pago(self):
        url = '/api/v1/pagos/confirmar-ia/'
        payload = {
            'token_secreto': 'test-token',
            'usuario_id': self.user.pk,
            'monto_real': '10.00',
            'plan_id': self.plan.pk,
            'referencia_bancaria': 'REF-TEST-001'
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        # RegistroPago creado
        exists = RegistroPago.objects.filter(comprobante_id='REF-TEST-001').exists()
        self.assertTrue(exists)
        # Suscripcion creada/actualizada
        sus = Suscripcion.objects.filter(user=self.user, plan_actual=self.plan).first()
        self.assertIsNotNone(sus)
        # WebhookLog creado (success)
        self.assertTrue(WebhookLog.objects.filter(referencia='REF-TEST-001', status='success').exists())

    def test_webhook_rechaza_referencia_duplicada(self):
        # Crear registro previo
        RegistroPago.objects.create(
            usuario=self.user,
            plan=self.plan,
            numero_comprobante='REF-TEST-002',
            comprobante_id='REF-TEST-002',
            comprobante='',
            monto_reportado='10.00',
            estado='Aprobado',
            nombre_cliente='Test',
            email_cliente='t@test.com',
            telefono_cliente='',
            id_cliente=''
        )

        url = '/api/v1/pagos/confirmar-ia/'
        payload = {
            'token_secreto': 'test-token',
            'usuario_id': self.user.pk,
            'monto_real': '10.00',
            'plan_id': self.plan.pk,
            'referencia_bancaria': 'REF-TEST-002'
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        # WebhookLog creado para fallo
        self.assertTrue(WebhookLog.objects.filter(referencia='REF-TEST-002', status='failed').exists())