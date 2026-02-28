from django.test import TestCase
from .models import TipoGasto, Gasto, DetalleGastoAdministracion, DetalleGastoVenta
from datetime import date


class TipoGastoTestCase(TestCase):
    def setUp(self):
        TipoGasto.objects.create(nombre='ADMINISTRACION', descripcion='Gastos administrativos')
        TipoGasto.objects.create(nombre='VENTA', descripcion='Gastos de venta')
    
    def test_crear_tipo_gasto(self):
        tipo = TipoGasto.objects.get(nombre='ADMINISTRACION')
        self.assertEqual(tipo.descripcion, 'Gastos administrativos')


class GastoTestCase(TestCase):
    def setUp(self):
        tipo = TipoGasto.objects.create(nombre='ADMINISTRACION')
        Gasto.objects.create(
            tipo_gasto=tipo,
            descripcion='Salarios',
            monto=1000.00,
            fecha_gasto=date.today(),
            estado='PENDIENTE'
        )
    
    def test_crear_gasto(self):
        gasto = Gasto.objects.get(descripcion='Salarios')
        self.assertEqual(float(gasto.monto), 1000.00)
        self.assertEqual(gasto.estado, 'PENDIENTE')
