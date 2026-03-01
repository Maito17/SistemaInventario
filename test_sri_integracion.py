"""
Test suite para validar la integración con el SRI
Prueba todos los componentes del flujo de envío de comprobantes
"""

import os
import sys
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')

import django
django.setup()

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from django.contrib.auth.models import User
from django.test import TestCase

from possitema.models import ConfiguracionEmpresa
from ventas.models import Venta
from cliente.models import Cliente
from inventario.models import Producto, Categoria
from enviar_comprobante_sri import ClienteSRIRecepcion, enviar_xml_factura_sri
from integracion_sri import IntegradorSRI
from possitema.services import generar_clave_acceso_desde_venta, generar_xml_factura_sri


class TestClienteSRIRecepcion(TestCase):
    """Tests para el cliente del SRI"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='sriuser',
            password='sripass123'
        )
    
    def setUp(self):
        """Setup para cada test"""
        self.config = ConfiguracionEmpresa.objects.create(
            user=self.user,
            nombre_empresa='SRI Test Co',
            ruc='1234567890123',
            razon_social='SRI Test SA',
            direccion='Test 123',
            codigo_establecimiento_emisor='001',
            codigo_punto_emision='001',
            tipo_ambiente='2',
            tipo_emision='1'
        )
        
        # Crear cliente
        self.cliente = Cliente.objects.create(
            id_cliente='CLI_SRI_001',
            nombre='TestClient',
            apellido='SRI',
            ruc_cedula='9999999999999'
        )
        
        # Crear categoría y producto
        self.categoria = Categoria.objects.create(nombre='SRI Category')
        self.producto = Producto.objects.create(
            id_producto='PROD_SRI_001',
            nombre='SRI Product',
            precio_costo=50.00,
            precio_venta=100.00,
            cantidad=10,
            categoria=self.categoria
        )
        
        # Crear venta
        self.venta = Venta.objects.create(
            owner=self.user,
            cliente=self.cliente,
            total=100.00
        )
    
    def test_inicializacion_cliente(self):
        """Test que el cliente se inicializa correctamente"""
        with patch('enviar_comprobante_sri.Client'):
            cliente = ClienteSRIRecepcion(ambiente='pruebas')
            self.assertEqual(cliente.ambiente, 'pruebas')
            self.assertEqual(cliente.url_ws, ClienteSRIRecepcion.URL_WS_SRI_PRUEBAS)
    
    def test_validacion_clave_acceso_formato(self):
        """Test que valida el formato de la clave de acceso"""
        # Generar clave válida
        clave = generar_clave_acceso_desde_venta(self.venta, self.config)
        
        # Debe ser numérica
        self.assertTrue(clave.isdigit(), "La clave debe ser numérica")
        
        # Debe tener entre 40-49 dígitos
        self.assertGreaterEqual(len(clave), 40, "Clave muy corta")
        self.assertLessEqual(len(clave), 49, "Clave muy larga")
    
    def test_generacion_xml_estructura(self):
        """Test que el XML tiene la estructura correcta """
        clave = generar_clave_acceso_desde_venta(self.venta, self.config)
        xml = generar_xml_factura_sri(self.venta, self.config, clave)
        
        # Validar estructura básica
        self.assertIn('<factura', xml)
        self.assertIn('<claveAcceso>', xml)
        self.assertIn('<infoTributaria>', xml)
        self.assertIn('<infoFactura>', xml)
        self.assertIn(clave, xml)
    
    def test_xml_encoding_utf8(self):
        """Test que el XML está en UTF-8"""
        clave = generar_clave_acceso_desde_venta(self.venta, self.config)
        xml = generar_xml_factura_sri(self.venta, self.config, clave)
        
        # Convertir a bytes como se enviaría al SRI
        xml_bytes = xml.encode('utf-8')
        
        # Validar que puede convertirse de vuelta
        xml_decodificado = xml_bytes.decode('utf-8')
        self.assertEqual(xml, xml_decodificado)
    
    @patch('enviar_comprobante_sri.Client')
    def test_procesamiento_respuesta_exitosa(self, mock_client_class):
        """Test que procesa respuesta exitosa del SRI"""
        # Simular cliente SOAP
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Simular respuesta del SRI
        mock_client.service.validarComprobante.return_value = 'RECIBIDA'
        
        with patch('enviar_comprobante_sri.etree.fromstring') as mock_parse:
            mock_parse.return_value = MagicMock()
            cliente = ClienteSRIRecepcion(ambiente='pruebas')
            resultado = cliente.validar_comprobante('<factura><claveAcceso>123456789</claveAcceso></factura>')
            
            # El resultado debe tener estructura
            self.assertIsNotNone(resultado)
    
    @patch('enviar_comprobante_sri.Client')
    def test_procesamiento_respuesta_error(self, mock_client_class):
        """Test que procesa respuesta de error del SRI"""
        # Simular cliente SOAP
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Simular respuesta de error
        mock_client.service.validarComprobante.return_value = 'RECHAZADA'
        
        with patch('enviar_comprobante_sri.etree.fromstring') as mock_parse:
            mock_parse.return_value = MagicMock()
            cliente = ClienteSRIRecepcion(ambiente='pruebas')
            resultado = cliente.validar_comprobante('<factura><claveAcceso>123456789</claveAcceso></factura>')
            
            self.assertIsNotNone(resultado)


class TestIntegradorSRI(TestCase):
    """Tests para el integrador completo del SRI"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='integradoruser',
            password='integpass123'
        )
    
    def setUp(self):
        """Setup para cada test"""
        self.config = ConfiguracionEmpresa.objects.create(
            user=self.user,
            nombre_empresa='Integrador Test',
            ruc='9876543210123',
            razon_social='Integrador SA',
            direccion='Test 456',
            codigo_establecimiento_emisor='001',
            codigo_punto_emision='001',
            tipo_ambiente='2',
            tipo_emision='1'
        )
        
        # Crear cliente
        self.cliente = Cliente.objects.create(
            id_cliente='CLI_INT_001',
            nombre='Integrador',
            apellido='Cliente',
            ruc_cedula='5555555555555'
        )
        
        # Crear categoría y producto
        self.categoria = Categoria.objects.create(nombre='Int Category')
        self.producto = Producto.objects.create(
            id_producto='PROD_INT_001',
            nombre='Int Product',
            precio_costo=40.00,
            precio_venta=80.00,
            cantidad=20,
            categoria=self.categoria
        )
        
        # Crear venta
        self.venta = Venta.objects.create(
            owner=self.user,
            cliente=self.cliente,
            total=80.00
        )
    
    def test_inicializacion_integrador(self):
        """Test que el integrador se inicializa correctamente"""
        with patch('integracion_sri.ClienteSRIRecepcion'):
            integrador = IntegradorSRI(user=self.user)
            self.assertIsNotNone(integrador.config)
            self.assertEqual(integrador.user, self.user)
            self.assertEqual(integrador.ambiente, 'pruebas')
    
    def test_integrador_sin_configuracion(self):
        """Test que falla si no hay configuración"""
        user_sin_config = User.objects.create_user(
            username='sinconfig',
            password='pass123'
        )
        
        with self.assertRaises(ValueError):
            IntegradorSRI(user=user_sin_config)
    
    @patch('integracion_sri.ClienteSRIRecepcion')
    def test_procesar_factura_sin_certificado(self, mock_sri):
        """Test procesamiento de factura sin certificado"""
        # Simular respuesta del SRI
        mock_sri.return_value.validar_comprobante.return_value = {
            'exito': True,
            'estado': 'RECIBIDA'
        }
        
        integrador = IntegradorSRI(user=self.user)
        resultado = integrador.procesar_factura_completa(self.venta.id_venta)
        
        # Debe procesar exitosamente(aunque sin firma)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado['venta_id'], self.venta.id_venta)
    
    def test_consultar_autorizacion_clave_valida(self):
        """Test consulta de autorización con clave válida"""
        integrador = IntegradorSRI(user=self.user)
        
        # Generar una clave válida
        clave = generar_clave_acceso_desde_venta(self.venta, self.config)
        
        # La consulta debe al menos aceptar la clave
        resultado = integrador.consultar_autorizacion(clave)
        self.assertIn('clave_acceso', resultado)


class TestXMLGeneracion(TestCase):
    """Tests específicos para generación de XML"""
    
    @classmethod
    def setUpClass(cls):
        """Configuración inicial"""
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='xmluser',
            password='xmlpass123'
        )
    
    def setUp(self):
        """Setup para cada test"""
        self.config = ConfiguracionEmpresa.objects.create(
            user=self.user,
            nombre_empresa='XML Test Co',
            ruc='1111111111111',
            razon_social='XML Test SA',
            direccion='XML Test St',
            codigo_establecimiento_emisor='002',
            codigo_punto_emision='002',
            tipo_ambiente='2',
            tipo_emision='1'
        )
        
        # Crear cliente
        self.cliente = Cliente.objects.create(
            id_cliente='CLI_XML_001',
            nombre='XMLCliente',
            apellido='Test',
            ruc_cedula='7777777777777'
        )
        
        # Crear venta
        self.venta = Venta.objects.create(
            owner=self.user,
            cliente=self.cliente,
            total=150.00
        )
    
    def test_xml_contiene_todos_campos_obligatorios(self):
        """Test que XML contiene todos los campos obligatorios del SRI"""
        clave = generar_clave_acceso_desde_venta(self.venta, self.config)
        xml = generar_xml_factura_sri(self.venta, self.config, clave)
        
        campos_obligatorios = [
            'claveAcceso',
            'tipoComprobante',
            'razonSocial',
            'ruc',
            'fechaEmision',
            'tipoIdentificacionComprador',
            'identificacionComprador',
            'razonSocialComprador'
        ]
        
        for campo in campos_obligatorios:
            self.assertIn(campo, xml, f"Campo obligatorio faltante: {campo}")
    
    def test_xml_bien_formado(self):
        """Test que el XML está bien formado"""
        from lxml import etree
        
        clave = generar_clave_acceso_desde_venta(self.venta, self.config)
        xml = generar_xml_factura_sri(self.venta, self.config, clave)
        
        # Debe poder ser parseado sin errores
        try:
            root = etree.fromstring(xml.encode('utf-8'))
            self.assertIsNotNone(root)
        except etree.XMLSyntaxError as e:
            self.fail(f"XML mal formado: {str(e)}")


def run_tests():
    """Ejecuta todos los tests"""
    import unittest
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar tests
    suite.addTests(loader.loadTestsFromTestCase(TestClienteSRIRecepcion))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegradorSRI))
    suite.addTests(loader.loadTestsFromTestCase(TestXMLGeneracion))
    
    # Ejecutar
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("TEST SUITE - INTEGRACIÓN CON SRI")
    print("=" * 70 + "\n")
    
    exit_code = run_tests()
    
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✓ TODOS LOS TESTS PASARON")
    else:
        print("✗ ALGUNOS TESTS FALLARON")
    print("=" * 70 + "\n")
    
    sys.exit(exit_code)
