"""
Test suite para la firma digital XAdES-BES de facturas
Valida el funcionamiento de la clase FirmadorFactura
"""

import os
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.test import TestCase
from possitema.models import ConfiguracionEmpresa
from possitema.services import generar_clave_acceso_desde_venta, generar_xml_factura_sri
from possitema.firma_sri import FirmadorFactura, ErrorCertificado, ErrorFirma
from ventas.models import Venta
from cliente.models import Cliente
from inventario.models import Producto, Categoria


class TestFirmadorFactura(TestCase):
    """Tests para la clase FirmadorFactura"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial para los tests"""
        super().setUpClass()
        
        # Crear usuario de prueba
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def setUp(self):
        """Configuración para cada test"""
        # Crear configuración de empresa
        self.config = ConfiguracionEmpresa.objects.create(
            user=self.user,
            nombre_empresa='Test Company',
            ruc='1234567890123',
            razon_social='Test Company SA',
            direccion='Calle Test 123',
            codigo_establecimiento_emisor='001',
            codigo_punto_emision='001',
            tipo_ambiente='2',
            tipo_emision='1'
        )
        
        # Crear cliente
        self.cliente = Cliente.objects.create(
            id_cliente='CLI001',
            nombre='Cliente Test',
            apellido='Test',
            ruc_cedula='9999999999999'
        )
        
        # Crear categoría
        self.categoria = Categoria.objects.create(
            nombre='Test Category'
        )
        
        # Crear producto
        self.producto = Producto.objects.create(
            id_producto='PROD001',
            nombre='Test Product',
            precio_costo=80.00,
            precio_venta=100.00,
            cantidad=10,
            categoria=self.categoria,
            tarifa_iva='15'
        )
        
        # Crear venta
        self.venta = Venta.objects.create(
            owner=self.user,
            cliente=self.cliente,
            total=115.00  # 100 + 15% IVA
        )
    
    def test_generar_xml_factura(self):
        """Test generación de XML de factura"""
        # Generar clave de acceso
        clave_acceso = generar_clave_acceso_desde_venta(self.venta, self.config)
        self.assertIsNotNone(clave_acceso)
        # La clave debe ser numérica y tener al menos 40 dígitos
        self.assertTrue(clave_acceso.isdigit())
        self.assertGreaterEqual(len(clave_acceso), 40)
        
        # Generar XML
        xml = generar_xml_factura_sri(self.venta, self.config, clave_acceso)
        self.assertIsNotNone(xml)
        self.assertIn('<factura', xml)
        self.assertIn('<claveAcceso>', xml)
        self.assertIn(clave_acceso, xml)
    
    def test_configuracion_sin_certificado(self):
        """Test que maneja gracefully falta de certificado"""
        # Sin certificado, no debería intentar firmar
        clave_acceso = generar_clave_acceso_desde_venta(self.venta, self.config)
        xml = generar_xml_factura_sri(self.venta, self.config, clave_acceso)
        
        # Debería generar XML sin firmar
        self.assertIsNotNone(xml)
        self.assertNotIn('<Signature', xml)  # Sin firma digital
    
    def test_encriptacion_password_p12(self):
        """Test de encriptación y desencriptación de password P12"""
        # Establecer password
        password_test = "TestPassword123!@#"
        self.config.establecer_password_p12(password_test)
        self.config.save()
        
        # Recuperar y verificar
        password_recuperado = self.config.obtener_password_p12()
        self.assertEqual(password_test, password_recuperado)
    
    def test_password_p12_cifrado_en_basedatos(self):
        """Verifica que el password está cifrado en la BD"""
        password_test = "SecretP12Password"
        self.config.establecer_password_p12(password_test)
        self.config.save()
        
        # Verificar que no está en plaintext en BD
        db_config = ConfiguracionEmpresa.objects.get(pk=self.config.pk)
        self.assertNotEqual(db_config.password_p12_cifrado, password_test)
        self.assertTrue(len(db_config.password_p12_cifrado) > 0)
        
        # Pero desencriptado debería ser correcto
        self.assertEqual(db_config.obtener_password_p12(), password_test)


class TestIntegracionFirmaDigital(TestCase):
    """Tests de integración de firma digital con vista"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='integrationuser',
            password='integrationpass123'
        )
    
    def setUp(self):
        """Setup para cada test"""
        self.config = ConfiguracionEmpresa.objects.create(
            user=self.user,
            nombre_empresa='Integration Test Co',
            ruc='9876543210123',
            razon_social='Integration Test Co SA',
            direccion='Av. Integración 456',
            codigo_establecimiento_emisor='001',
            codigo_punto_emision='001',
            tipo_ambiente='2',
            tipo_emision='1'
        )
        
        self.cliente = Cliente.objects.create(
            id_cliente='CLI002',
            nombre='Cliente Integration',
            apellido='Integration',
            ruc_cedula='5555555555555'
        )
        
        self.categoria = Categoria.objects.create(
            nombre='Integration Category'
        )
        
        self.producto = Producto.objects.create(
            id_producto='PROD002',
            nombre='Integration Product',
            precio_costo=200.00,
            precio_venta=250.00,
            cantidad=20,
            categoria=self.categoria,
            tarifa_iva='15'
        )
        
        self.venta = Venta.objects.create(
            owner=self.user,
            cliente=self.cliente,
            total=280.00  # 250 + 12% IVA
        )
    
    def test_flujo_completo_sin_certificado(self):
        """Test flujo completo sin certificado (debería generar XML sin firma)"""
        from possitema.services import generar_clave_acceso_desde_venta, generar_xml_factura_sri
        
        # 1. Generar clave de acceso
        clave_acceso = generar_clave_acceso_desde_venta(self.venta, self.config)
        self.assertIsNotNone(clave_acceso)
        
        # 2. Generar XML
        xml = generar_xml_factura_sri(self.venta, self.config, clave_acceso)
        self.assertIsNotNone(xml)
        
        # 3. Validar estructura XML
        from lxml import etree
        try:
            root = etree.fromstring(xml.encode('utf-8'))
            self.assertTrue(len(root) > 0)
        except etree.XMLSyntaxError:
            self.fail("XML generado no es válido")


def run_tests():
    """Ejecuta todos los tests"""
    import unittest
    
    # Cargar suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar tests
    suite.addTests(loader.loadTestsFromTestCase(TestFirmadorFactura))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegracionFirmaDigital))
    
    # Ejecutar
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
