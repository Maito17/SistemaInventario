"""
Script para enviar XML firmado al Web Service de Recepción del SRI
Utiliza zeep para comunicarse con el SOAP WebService del SRI en ambiente de pruebas
"""

import os
import sys
import base64
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')

import django
django.setup()

from zeep import Client, xsd
from zeep.exceptions import Fault
from lxml import etree

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClienteSRIRecepcion:
    """
    Cliente para enviar comprobantes al Web Service de Recepción del SRI Ecuador
    """
    
    # URLs de los Web Services del SRI
    URL_WS_SRI_PRUEBAS = "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesService?wsdl"
    URL_WS_SRI_PRODUCCION = "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesService?wsdl"
    
    def __init__(self, ambiente: str = 'pruebas'):
        """
        Inicializa el cliente del SRI
        
        Args:
            ambiente: 'pruebas' o 'produccion'
        """
        self.ambiente = ambiente
        self.url_ws = self.URL_WS_SRI_PRUEBAS if ambiente == 'pruebas' else self.URL_WS_SRI_PRODUCCION
        self.client = None
        self._inicializar_cliente()
    
    def _inicializar_cliente(self):
        """Inicializa la conexión con el Web Service del SRI"""
        try:
            logger.info(f"Conectando a Web Service del SRI ({self.ambiente}): {self.url_ws}")
            self.client = Client(wsdl=self.url_ws)
            logger.info("✓ Conexión establecida correctamente")
        except Exception as e:
            logger.error(f"✗ Error al conectar con el Web Service: {str(e)}")
            raise
    
    def validar_comprobante(self, xml_firmado: str) -> Dict:
        """
        Envía un XML firmado al Web Service de validación del SRI
        
        Args:
            xml_firmado: String con el XML completo y firmado
        
        Returns:
            Dict con el resultado de la validación
        """
        
        # Validar que el XML esté firmado
        if '<Signature' not in xml_firmado and '<Firma>' not in xml_firmado:
            logger.warning("⚠ Advertencia: El XML no contiene firma digital")
        
        try:
            # Convertir XML a bytes
            xml_bytes = xml_firmado.encode('utf-8')
            
            # Validar estructura XML
            xmlroot = etree.fromstring(xml_bytes)
            logger.info(f"✓ XML validado correctamente")
            logger.debug(f"  Raíz del documento: {xmlroot.tag}")
            
            # Extraer clave de acceso del XML para registro
            clave_elem = xmlroot.find('.//{*}claveAcceso')
            clave_acceso = clave_elem.text if clave_elem is not None else "NO ENCONTRADA"
            logger.info(f"  Clave de acceso: {clave_acceso}")
            
            # Llamar al método validarComprobante del Web Service
            logger.info("Enviando comprobante al Web Service del SRI...")
            respuesta = self.client.service.validarComprobante(xml_bytes)
            
            # Procesar respuesta
            return self._procesar_respuesta(respuesta, clave_acceso, xml_firmado)
            
        except Fault as e:
            logger.error(f"✗ Fault SOAP: {str(e)}")
            return {
                'exito': False,
                'estado': 'ERROR',
                'mensaje': f"Error SOAP del servidor: {str(e)}",
                'tipo_error': 'FAULT_SOAP',
                'detalles': str(e)
            }
        except etree.XMLSyntaxError as e:
            logger.error(f"✗ XML inválido: {str(e)}")
            return {
                'exito': False,
                'estado': 'ERROR',
                'mensaje': f"XML mal formado: {str(e)}",
                'tipo_error': 'XML_INVALIDO'
            }
        except Exception as e:
            logger.error(f"✗ Error inesperado: {str(e)}")
            return {
                'exito': False,
                'estado': 'ERROR',
                'mensaje': str(e),
                'tipo_error': 'ERROR_GENERAL'
            }
    
    def _procesar_respuesta(self, respuesta: any, clave_acceso: str, xml_original: str) -> Dict:
        """
        Procesa la respuesta del Web Service del SRI
        
        Args:
            respuesta: Respuesta del Web Service
            clave_acceso: Clave de acceso del comprobante
            xml_original: XML original enviado
        
        Returns:
            Dict con resultado procesado
        """
        
        logger.info("=" * 70)
        logger.info("RESPUESTA DEL WEB SERVICE DEL SRI")
        logger.info("=" * 70)
        
        # Convertir respuesta a string para análisis
        respuesta_str = str(respuesta)
        
        # Casos de éxito
        if 'RECIBIDA' in respuesta_str or '1' in respuesta_str:
            logger.info("✓ COMPROBANTE RECIBIDO CORRECTAMENTE")
            
            return {
                'exito': True,
                'estado': 'RECIBIDA',
                'clave_acceso': clave_acceso,
                'timestamp': datetime.now().isoformat(),
                'mensaje': 'El comprobante fue recibido correctamente por el SRI',
                'ambiente': self.ambiente,
                'respuesta_completa': respuesta
            }
        
        # Casos de error de validación
        elif 'NO_AUTORIZADO' in respuesta_str or '2' in respuesta_str:
            logger.warning("⚠ COMPROBANTE NO AUTORIZADO")
            
            return {
                'exito': False,
                'estado': 'NO_AUTORIZADO',
                'clave_acceso': clave_acceso,
                'timestamp': datetime.now().isoformat(),
                'mensaje': 'El comprobante no fue autorizado. Verificar datos tributarios',
                'tipo_error': 'NO_AUTORIZADO',
                'ambiente': self.ambiente,
                'respuesta_completa': respuesta
            }
        
        # Casos de error en XML
        elif 'ERROR' in respuesta_str.upper() or 'INVALIDO' in respuesta_str:
            logger.warning("⚠ ERROR DE VALIDACIÓN")
            
            return {
                'exito': False,
                'estado': 'ERROR_VALIDACION',
                'clave_acceso': clave_acceso,
                'timestamp': datetime.now().isoformat(),
                'mensaje': f'Error en la validación del comprobante: {respuesta_str}',
                'tipo_error': 'ERROR_VALIDACION',
                'ambiente': self.ambiente,
                'respuesta_completa': respuesta
            }
        
        # Casos desconocidos
        else:
            logger.info(f"Respuesta del servidor: {respuesta_str}")
            
            return {
                'exito': None,
                'estado': 'DESCONOCIDO',
                'clave_acceso': clave_acceso,
                'timestamp': datetime.now().isoformat(),
                'mensaje': f'Estado desconocido: {respuesta_str}',
                'ambiente': self.ambiente,
                'respuesta_completa': respuesta
            }
    
    def obtener_autorizacion(self, clave_acceso: str) -> Dict:
        """
        Consulta el estado de autorización de un comprobante por su clave de acceso
        
        Args:
            clave_acceso: Clave de acceso del comprobante (49 dígitos)
        
        Returns:
            Dict con información de la autorización
        """
        
        if len(clave_acceso) != 49:
            logger.error(f"✗ Clave de acceso inválida: debe tener 49 dígitos, se recibieron {len(clave_acceso)}")
            return {
                'exito': False,
                'mensaje': 'Clave de acceso debe tener 49 dígitos'
            }
        
        try:
            logger.info(f"Consultando autorización para clave: {clave_acceso}")
            respuesta = self.client.service.obtenerAutorizacion(clave_acceso)
            
            logger.info("✓ Consulta realizada correctamente")
            return {
                'exito': True,
                'clave_acceso': clave_acceso,
                'respuesta': respuesta,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"✗ Error consultando autorización: {str(e)}")
            return {
                'exito': False,
                'clave_acceso': clave_acceso,
                'mensaje': str(e)
            }


def enviar_xml_factura_sri(ruta_xml: Path, ambiente: str = 'pruebas') -> Dict:
    """
    Función principal para enviar un XML de factura al SRI
    
    Args:
        ruta_xml: Ruta al archivo XML firmado
        ambiente: 'pruebas' o 'produccion'
    
    Returns:
        Dict con resultado del envío
    """
    
    # Validar archivo
    if not ruta_xml.exists():
        logger.error(f"✗ Archivo no encontrado: {ruta_xml}")
        return {'exito': False, 'mensaje': 'Archivo XML no encontrado'}
    
    # Leer XML
    with open(ruta_xml, 'r', encoding='utf-8') as f:
        xml_contenido = f.read()
    
    logger.info(f"Lectura de archivo: {ruta_xml.name} ({len(xml_contenido)} caracteres)")
    
    # Crear cliente y enviar
    cliente = ClienteSRIRecepcion(ambiente=ambiente)
    resultado = cliente.validar_comprobante(xml_contenido)
    
    return resultado


def test_conexion_sri(ambiente: str = 'pruebas') -> bool:
    """
    Prueba la conexión al Web Service del SRI
    
    Args:
        ambiente: 'pruebas' o 'produccion'
    
    Returns:
        True si la conexión es exitosa
    """
    
    try:
        logger.info(f"Probando conexión al SRI ({ambiente})...")
        cliente = ClienteSRIRecepcion(ambiente=ambiente)
        
        # Intentar obtener métodos disponibles
        logger.info("✓ Métodos disponibles en el Web Service:")
        for servicio in cliente.client.wsdl.services.values():
            for puerto in servicio.ports.values():
                for operacion in puerto.binding_options['operations'].values():
                    logger.info(f"  - {operacion.name}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Error en la conexión: {str(e)}")
        return False


def generar_xml_ejemplo() -> str:
    """
    Genera un XML de ejemplo para pruebas (SIN firma)
    
    Returns:
        String con XML de ejemplo
    """
    
    from possitema.models import ConfiguracionEmpresa
    from ventas.models import Venta
    from possitema.services import generar_clave_acceso_desde_venta, generar_xml_factura_sri
    from django.contrib.auth.models import User
    from cliente.models import Cliente
    
    try:
        # Obtener o crear configuración
        user = User.objects.first()
        if not user:
            logger.error("No hay usuarios en el sistema")
            return None
        
        config = ConfiguracionEmpresa.objects.filter(user=user).first()
        if not config:
            logger.error("No hay configuración de empresa")
            return None
        
        # Obtener última venta
        venta = Venta.objects.last()
        if not venta:
            logger.error("No hay ventas registradas")
            return None
        
        # Generar clave y XML
        clave = generar_clave_acceso_desde_venta(venta, config)
        xml = generar_xml_factura_sri(venta, config, clave)
        
        logger.info(f"XML de ejemplo generado para venta #{venta.id_venta}")
        return xml
        
    except Exception as e:
        logger.error(f"Error generando XML de ejemplo: {str(e)}")
        return None


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("CLIENTE SRI - WEB SERVICE DE RECEPCIÓN DE COMPROBANTES")
    print("=" * 70 + "\n")
    
    # Prueba 1: Conexión
    print("STEP 1: Probando conexión al Web Service...")
    print("-" * 70)
    test_conexion_sri(ambiente='pruebas')
    
    # Prueba 2: Generar XML de ejemplo
    print("\n\nSTEP 2: Generando XML de ejemplo...")
    print("-" * 70)
    xml_ejemplo = generar_xml_ejemplo()
    
    if xml_ejemplo:
        print(f"✓ XML generado exitosamente ({len(xml_ejemplo)} caracteres)")
        
        # Prueba 3: Enviar (comentado porque requiere firma digital)
        print("\n\nSTEP 3: Preparación para envío...")
        print("-" * 70)
        print("""
        Para enviar un comprobante:
        
        1. Firmar el XML digitalmente:
           from possitema.firma_sri import FirmadorFactura
           firmador = FirmadorFactura(config_empresa)
           xml_firmado = firmador.firmar_factura(xml)
        
        2. Enviar al SRI:
           resultado = enviar_xml_factura_sri(Path('factura_firmada.xml'))
        
        3. Verificar resultado:
           if resultado['exito']:
               print(f"Autorización: {resultado['estado']}")
           else:
               print(f"Error: {resultado['mensaje']}")
        """)
    
    print("\n" + "=" * 70)
    print("CLIENTE LISTO")
    print("=" * 70 + "\n")
