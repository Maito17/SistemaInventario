"""
Funciones de integración para enviar comprobantes al SRI
Se integra con el flujo de generación de facturas
"""

import logging
from pathlib import Path
from typing import Dict, Optional
from django.http import JsonResponse
from possitema.firma_sri import FirmadorFactura, ErrorCertificado, ErrorFirma
from possitema.services import generar_clave_acceso_desde_venta, generar_xml_factura_sri
from ventas.models import Venta
from possitema.models import ConfiguracionEmpresa
from enviar_comprobante_sri import ClienteSRIRecepcion

logger = logging.getLogger(__name__)


class IntegradorSRI:
    """
    Integrador completo del proceso de facturación con el SRI
    Maneja: Generación -> Firma -> Envío -> Seguimiento
    """
    
    def __init__(self, user):
        """Inicializa el integrador con la configuración del usuario"""
        self.user = user
        self.config = ConfiguracionEmpresa.objects.filter(user=user).first()
        
        if not self.config:
            raise ValueError("No hay configuración de empresa para este usuario")
        
        # Determinar ambiente (por ahora siempre pruebas)
        self.ambiente = 'pruebas'
        self.cliente_sri = None
    
    def procesar_factura_completa(self, venta_id: int) -> Dict:
        """
        Procesa una factura completa: Generación -> Firma -> Envío
        
        Args:
            venta_id: ID de la venta a procesar
        
        Returns:
            Dict con resultado del proceso completo
        """
        
        try:
            # Paso 1: Obtener venta
            venta = Venta.objects.get(id_venta=venta_id)
            logger.info(f"Procesando venta #{venta_id}")
            
            # Paso 2: Generar clave de acceso
            clave_acceso = generar_clave_acceso_desde_venta(venta, self.config)
            logger.info(f"Clave de acceso generada: {clave_acceso}")
            
            # Paso 3: Generar XML
            xml_unsigned = generar_xml_factura_sri(venta, self.config, clave_acceso)
            logger.info(f"XML generado ({len(xml_unsigned)} caracteres)")
            
            # Paso 4: Firmar XML (si está disponible el certificado)
            xml_firmado = self._firmar_xml(xml_unsigned)
            
            if not xml_firmado:
                logger.warning("XML no fue firmado - enviando sin firma")
                xml_for_send = xml_unsigned
            else:
                logger.info("XML firmado correctamente")
                xml_for_send = xml_firmado
            
            # Paso 5: Enviar al SRI
            resultado_sri = self._enviar_al_sri(xml_for_send, clave_acceso)
            
            return {
                'exito': resultado_sri.get('exito'),
                'venta_id': venta_id,
                'clave_acceso': clave_acceso,
                'estado': resultado_sri.get('estado'),
                'mensaje': resultado_sri.get('mensaje'),
                'paso_actual': 'ENVIADO_AL_SRI',
                'xml_generado': len(xml_unsigned),
                'xml_firmado': xml_firmado is not None,
                'respuesta_sri': resultado_sri
            }
            
        except Venta.DoesNotExist:
            logger.error(f"Venta #{venta_id} no encontrada")
            return {
                'exito': False,
                'venta_id': venta_id,
                'error': 'Venta no encontrada',
                'paso_actual': 'OBTENER_VENTA'
            }
        
        except Exception as e:
            logger.error(f"Error en proceso completo: {str(e)}")
            return {
                'exito': False,
                'venta_id': venta_id,
                'error': str(e),
                'paso_actual': 'ERROR_GENERAL'
            }
    
    def _firmar_xml(self, xml_unsigned: str) -> Optional[str]:
        """
        Intenta firmar el XML si está disponible el certificado
        
        Args:
            xml_unsigned: XML sin firmar
        
        Returns:
            XML firmado o None si no se puede firmar
        """
        
        try:
            if not self.config.clave_firma_electronica:
                logger.info("No hay certificado digital configurado")
                return None
            
            # Obtener password cifrado
            password_p12 = self.config.obtener_password_p12()
            if not password_p12:
                logger.warning("No hay contraseña del certificado")
                return None
            
            # Crear firmador
            firmador = FirmadorFactura(
                config_empresa=self.config,
                ruta_p12=self.config.clave_firma_electronica.path
            )
            
            # Firmar
            xml_firmado = firmador.firmar_factura(xml_unsigned)
            return xml_firmado
            
        except ErrorCertificado as e:
            logger.warning(f"Error con certificado: {str(e)}")
            return None
        except ErrorFirma as e:
            logger.warning(f"Error al firmar: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Error en firma: {str(e)}")
            return None
    
    def _enviar_al_sri(self, xml: str, clave_acceso: str) -> Dict:
        """
        Envía el XML al SRI
        
        Args:
            xml: XML a enviar
            clave_acceso: Clave de acceso
        
        Returns:
            Resultado del envío
        """
        
        try:
            if not self.cliente_sri:
                self.cliente_sri = ClienteSRIRecepcion(ambiente=self.ambiente)
            
            resultado = self.cliente_sri.validar_comprobante(xml)
            return resultado
            
        except Exception as e:
            logger.error(f"Error enviando al SRI: {str(e)}")
            return {
                'exito': False,
                'estado': 'ERROR',
                'mensaje': f"Error conectando con SRI: {str(e)}",
                'clave_acceso': clave_acceso
            }
    
    def consultar_autorizacion(self, clave_acceso: str) -> Dict:
        """
        Consulta el estado de un comprobante en el SRI
        
        Args:
            clave_acceso: Clave de acceso de 49 dígitos
        
        Returns:
            Estado de autorización
        """
        
        try:
            if not self.cliente_sri:
                self.cliente_sri = ClienteSRIRecepcion(ambiente=self.ambiente)
            
            return self.cliente_sri.obtener_autorizacion(clave_acceso)
            
        except Exception as e:
            logger.error(f"Error consultando autorización: {str(e)}")
            return {
                'exito': False,
                'clave_acceso': clave_acceso,
                'error': str(e)
            }


def procesar_factura_view_helper(request, venta_id: int) -> Dict:
    """
    Helper para procesar una factura desde una vista Django
    
    Args:
        request: Objeto request de Django
        venta_id: ID de la venta
    
    Returns:
        Dict con resultado
    """
    
    try:
        integrador = IntegradorSRI(user=request.user)
        resultado = integrador.procesar_factura_completa(venta_id)
        return resultado
        
    except ValueError as e:
        return {
            'exito': False,
            'error': str(e),
            'mensaje': 'No hay configuración de empresa'
        }
    except Exception as e:
        logger.error(f"Error en vista de procesamiento: {str(e)}")
        return {
            'exito': False,
            'error': str(e),
            'mensaje': 'Error procesando factura'
        }
