"""
Módulo de Firma Digital XAdES-BES para Facturación SRI
Implementa la generación de firmas electrónicas conforme a estándares SRI Ecuador
"""

from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from lxml import etree
import base64
import hashlib
from datetime import datetime, timezone
import uuid
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ErrorCertificado(Exception):
    """Excepción para errores en manejo de certificados"""
    pass


class ErrorFirma(Exception):
    """Excepción para errores en generación de firma"""
    pass


class FirmadorFactura:
    """
    Clase para firmar facturas electrónicas con XAdES-BES según SRI Ecuador
    
    Maneja:
    - Carga de certificados PKCS#12 (.p12/.pfx)
    - Extracción de clave privada
    - Generación de firma XAdES-BES
    - Validación de certificados
    """
    
    # Namespace para XAdES-BES
    NAMESPACE_XADES = "http://uri.etsi.org/01903/v1.3.2#"
    NAMESPACE_DS = "http://www.w3.org/2000/09/xmldsig#"
    NAMESPACE_FACTURAELECTRONICA = "http://www.sri.gob.ec/comprobantes"
    
    def __init__(self, config_empresa):
        """
        Inicializa el firmador con la configuración de empresa
        
        Args:
            config_empresa: Instancia de ConfiguracionEmpresa con certificado P12
        """
        self.config_empresa = config_empresa
        self.certificado = None
        self.clave_privada = None
        self.info_certificado = None
        
        # Cargar certificado al inicializar
        self._cargar_certificado()
    
    def _cargar_certificado(self):
        """Carga el certificado PKCS#12 desde el archivo configurado"""
        try:
            ruta_p12 = self.config_empresa.clave_firma_electronica.path
            if not Path(ruta_p12).exists():
                raise ErrorCertificado(f"Archivo P12 no encontrado: {ruta_p12}")
            
            # Obtener contraseña cifrada
            password = self.config_empresa.obtener_password_p12()
            password_bytes = password.encode() if password else b''
            
            # Leer archivo P12
            with open(ruta_p12, 'rb') as f:
                p12_data = f.read()
            
            # Cargar certificado y clave privada desde P12
            from cryptography.hazmat.primitives.serialization import pkcs12
            
            try:
                private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                    p12_data,
                    password_bytes,
                    backend=default_backend()
                )
            except ValueError as e:
                if 'password' in str(e).lower() or 'decrypt' in str(e).lower():
                    raise ErrorCertificado("Contraseña de P12 incorrecta o certificado dañado")
                raise ErrorCertificado(f"Error al cargar P12: {str(e)}")
            
            if not private_key or not certificate:
                raise ErrorCertificado("No se pudo extraer clave privada o certificado de P12")
            
            self.clave_privada = private_key
            self.certificado = certificate
            
            # Extraer información del certificado
            self._extraer_info_certificado()
            
            logger.info(f"Certificado cargado exitosamente: {self.info_certificado['subject']}")
            
        except ErrorCertificado:
            raise
        except Exception as e:
            raise ErrorCertificado(f"Error inesperado al cargar certificado: {str(e)}")
    
    def _extraer_info_certificado(self):
        """Extrae información relevante del certificado X.509"""
        try:
            cert = self.certificado
            
            # Subject
            subject_dict = {}
            for attr in cert.subject:
                subject_dict[attr.oid._name] = attr.value
            
            # Validez
            not_before = cert.not_valid_before_utc
            not_after = cert.not_valid_after_utc
            
            # Serial
            serial = cert.serial_number
            
            # Thumbprint (SHA1)
            thumbprint = hashlib.sha1(cert.public_bytes(serialization.Encoding.DER)).hexdigest()
            
            self.info_certificado = {
                'subject': subject_dict,
                'issuer': cert.issuer.rfc4514_string(),
                'serial': serial,
                'thumbprint': thumbprint,
                'valido_desde': not_before,
                'valido_hasta': not_after,
                'valido_ahora': not_before <= datetime.now(timezone.utc) <= not_after
            }
            
            if not self.info_certificado['valido_ahora']:
                logger.warning("Certificado fuera de validez")
        
        except Exception as e:
            logger.error(f"Error extrayendo info de certificado: {str(e)}")
            self.info_certificado = {}
    
    def _generar_reference_uri(self, id_factura):
        """Genera la URI de referencia para XAdES-BES"""
        return f"#{id_factura}"
    
    def _calcular_hash_xml(self, xml_content, algoritmo='SHA256'):
        """Calcula el hash del contenido XML"""
        if isinstance(xml_content, str):
            xml_content = xml_content.encode('utf-8')
        
        if algoritmo == 'SHA256':
            hash_obj = hashlib.sha256(xml_content)
        elif algoritmo == 'SHA1':
            hash_obj = hashlib.sha1(xml_content)
        else:
            hash_obj = hashlib.sha256(xml_content)
        
        return base64.b64encode(hash_obj.digest()).decode('utf-8')
    
    def _generar_firma_digital(self, datos_a_firmar):
        """Genera la firma digital usando RSA-SHA256"""
        try:
            if isinstance(datos_a_firmar, str):
                datos_a_firmar = datos_a_firmar.encode('utf-8')
            
            # Firma con RSA-SHA256
            firma_bytes = self.clave_privada.sign(
                datos_a_firmar,
                serialization.NoEncryption() if hasattr(self.clave_privada, '__class__') else None
            )
            
            # Usar el método correcto según el tipo de clave
            if hasattr(self.clave_privada, 'sign'):
                from cryptography.hazmat.primitives.asymmetric import padding
                firma_bytes = self.clave_privada.sign(
                    datos_a_firmar,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            
            return base64.b64encode(firma_bytes).decode('utf-8')
        
        except Exception as e:
            raise ErrorFirma(f"Error al generar firma digital: {str(e)}")
    
    def _crear_elemento_signed_info(self, reference_uri, hash_documento):
        """Crea el elemento SignedInfo para la firma XAdES-BES"""
        signed_info = etree.Element(
            f"{{{self.NAMESPACE_DS}}}SignedInfo",
            attrib={'Id': f'SignedInfo_{uuid.uuid4().hex[:8]}'}
        )
        
        # CanonicalizationMethod
        canon_method = etree.SubElement(signed_info, f"{{{self.NAMESPACE_DS}}}CanonicalizationMethod")
        canon_method.set('Algorithm', 'http://www.w3.org/2001/10/xml-exc-c14n#')
        
        # SignatureMethod
        sig_method = etree.SubElement(signed_info, f"{{{self.NAMESPACE_DS}}}SignatureMethod")
        sig_method.set('Algorithm', 'http://www.w3.org/2001/04/xmldsig-more#rsa-sha256')
        
        # Reference
        reference = etree.SubElement(signed_info, f"{{{self.NAMESPACE_DS}}}Reference")
        reference.set('Id', f'Reference_{uuid.uuid4().hex[:8]}')
        reference.set('URI', reference_uri)
        reference.set('Type', 'http://www.w3.org/2000/09/xmldsig#Object')
        
        # Transforms
        transforms = etree.SubElement(reference, f"{{{self.NAMESPACE_DS}}}Transforms")
        transform = etree.SubElement(transforms, f"{{{self.NAMESPACE_DS}}}Transform")
        transform.set('Algorithm', 'http://www.w3.org/2000/09/xmldsig#enveloped-signature')
        
        # DigestMethod
        digest_method = etree.SubElement(reference, f"{{{self.NAMESPACE_DS}}}DigestMethod")
        digest_method.set('Algorithm', 'http://www.w3.org/2001/04/xmlenc#sha256')
        
        # DigestValue
        digest_value = etree.SubElement(reference, f"{{{self.NAMESPACE_DS}}}DigestValue")
        digest_value.text = hash_documento
        
        return signed_info
    
    def _crear_elemento_key_info(self):
        """Crea el elemento KeyInfo con el certificado"""
        key_info = etree.Element(f"{{{self.NAMESPACE_DS}}}KeyInfo")
        key_info.set('Id', f'KeyInfo_{uuid.uuid4().hex[:8]}')
        
        # X509Data
        x509_data = etree.SubElement(key_info, f"{{{self.NAMESPACE_DS}}}X509Data")
        
        # X509Certificate
        x509_cert = etree.SubElement(x509_data, f"{{{self.NAMESPACE_DS}}}X509Certificate")
        cert_der = self.certificado.public_bytes(serialization.Encoding.DER)
        x509_cert.text = base64.b64encode(cert_der).decode('utf-8')
        
        # X509SubjectName
        x509_subject = etree.SubElement(x509_data, f"{{{self.NAMESPACE_DS}}}X509SubjectName")
        x509_subject.text = self.certificado.subject.rfc4514_string()
        
        # X509IssuerSerial
        issuer_serial = etree.SubElement(x509_data, f"{{{self.NAMESPACE_DS}}}X509IssuerSerial")
        issuer_name = etree.SubElement(issuer_serial, f"{{{self.NAMESPACE_DS}}}X509IssuerName")
        issuer_name.text = self.certificado.issuer.rfc4514_string()
        serial_number = etree.SubElement(issuer_serial, f"{{{self.NAMESPACE_DS}}}X509SerialNumber")
        serial_number.text = str(self.certificado.serial_number)
        
        return key_info
    
    def firmar_factura(self, venta, xml_factura_str, id_comprobante=None):
        """
        Firma una factura con XAdES-BES
        
        Args:
            venta: Instancia de Venta
            xml_factura_str: XML de la factura como string
            id_comprobante: ID del comprobante (generado si no se proporciona)
        
        Returns:
            str: XML compileto con firma XAdES-BES
        """
        try:
            if id_comprobante is None:
                id_comprobante = f"factura_{venta.id}"
            
            # Validar certificado
            if not self.info_certificado.get('valido_ahora'):
                raise ErrorFirma("Certificado no válido o expirado")
            
            # Parsear XML
            try:
                root = etree.fromstring(xml_factura_str.encode('utf-8'))
            except etree.XMLSyntaxError as e:
                raise ErrorFirma(f"XML inválido: {str(e)}")
            
            # Calcular hash del documento
            hash_documento = self._calcular_hash_xml(xml_factura_str)
            
            # Crear SignedInfo
            reference_uri = self._generar_reference_uri(id_comprobante)
            signed_info = self._crear_elemento_signed_info(reference_uri, hash_documento)
            
            # Generar firma digital del SignedInfo
            signed_info_str = etree.tostring(
                signed_info,
                method='c14n',
                exclusive=True,
                encoding='utf-8'
            )
            firma_digital = self._generar_firma_digital(signed_info_str)
            
            # Crear elemento Signature
            signature = etree.Element(
                f"{{{self.NAMESPACE_DS}}}Signature",
                attrib={'Id': f'Signature_{uuid.uuid4().hex[:8]}'}
            )
            
            # Agregar SignedInfo
            signature.append(signed_info)
            
            # Agregar SignatureValue
            sig_value = etree.SubElement(signature, f"{{{self.NAMESPACE_DS}}}SignatureValue")
            sig_value.set('Id', f'SignatureValue_{uuid.uuid4().hex[:8]}')
            sig_value.text = firma_digital
            
            # Agregar KeyInfo
            key_info = self._crear_elemento_key_info()
            signature.append(key_info)
            
            # Agregar Object con información de firma (XAdES-BES)
            object_elem = etree.SubElement(signature, f"{{{self.NAMESPACE_DS}}}Object")
            object_elem.set('Encoding', 'http://www.w3.org/2000/09/xmldsig#base64')
            
            quality_properties = etree.SubElement(
                object_elem,
                f"{{{self.NAMESPACE_XADES}}}QualifyingProperties",
                attrib={'Target': f'#{signature.get("Id")}'}
            )
            
            signed_properties = etree.SubElement(
                quality_properties,
                f"{{{self.NAMESPACE_XADES}}}SignedProperties",
                attrib={'Id': f'SignedProperties_{uuid.uuid4().hex[:8]}'}
            )
            
            # SignedSignatureProperties
            signed_sig_props = etree.SubElement(
                signed_properties,
                f"{{{self.NAMESPACE_XADES}}}SignedSignatureProperties"
            )
            
            # SigningTime
            signing_time = etree.SubElement(signed_sig_props, f"{{{self.NAMESPACE_XADES}}}SigningTime")
            signing_time.text = datetime.now(timezone.utc).isoformat()
            
            # SigningCertificate
            signing_cert = etree.SubElement(
                signed_sig_props,
                f"{{{self.NAMESPACE_XADES}}}SigningCertificate"
            )
            
            cert_elem = etree.SubElement(signing_cert, f"{{{self.NAMESPACE_XADES}}}Cert")
            cert_digest = etree.SubElement(cert_elem, f"{{{self.NAMESPACE_XADES}}}CertDigest")
            
            digest_method = etree.SubElement(cert_digest, f"{{{self.NAMESPACE_DS}}}DigestMethod")
            digest_method.set('Algorithm', 'http://www.w3.org/2001/04/xmlenc#sha256')
            
            digest_value = etree.SubElement(cert_digest, f"{{{self.NAMESPACE_DS}}}DigestValue")
            cert_der = self.certificado.public_bytes(serialization.Encoding.DER)
            cert_hash = base64.b64encode(hashlib.sha256(cert_der).digest()).decode('utf-8')
            digest_value.text = cert_hash
            
            issuer_serial = etree.SubElement(cert_elem, f"{{{self.NAMESPACE_XADES}}}IssuerSerial")
            issuer_name = etree.SubElement(issuer_serial, f"{{{self.NAMESPACE_DS}}}X509IssuerName")
            issuer_name.text = self.certificado.issuer.rfc4514_string()
            serial_number = etree.SubElement(issuer_serial, f"{{{self.NAMESPACE_DS}}}X509SerialNumber")
            serial_number.text = str(self.certificado.serial_number)
            
            # SignatureProductionPlace
            signature_place = etree.SubElement(
                signed_sig_props,
                f"{{{self.NAMESPACE_XADES}}}SignatureProductionPlace"
            )
            city = etree.SubElement(signature_place, f"{{{self.NAMESPACE_XADES}}}City")
            city.text = "Ecuador"  # Ciudad por defecto para SRI Ecuador
            
            # SignerRole
            signer_role = etree.SubElement(
                signed_sig_props,
                f"{{{self.NAMESPACE_XADES}}}SignerRole"
            )
            claimed_role = etree.SubElement(signer_role, f"{{{self.NAMESPACE_XADES}}}ClaimedRole")
            claimed_role.text = "Emisor"
            
            # Agregar firma al documento
            root.append(signature)
            
            # Retornar XML firmado
            xml_firmado = etree.tostring(
                root,
                xml_declaration=True,
                encoding='UTF-8',
                standalone=True,
                pretty_print=True
            ).decode('utf-8')
            
            logger.info(f"Factura {id_comprobante} firmada exitosamente")
            return xml_firmado
        
        except ErrorFirma:
            raise
        except Exception as e:
            logger.error(f"Error firmando factura: {str(e)}")
            raise ErrorFirma(f"Error al firmar factura: {str(e)}")
    
    def validar_integridad_firma(self, xml_firmado):
        """
        Valida que la firma sea íntegra (verificación básica)
        
        Returns:
            dict: Información de validación
        """
        try:
            root = etree.fromstring(xml_firmado.encode('utf-8'))
            
            # Buscar elemento Signature
            nsmap = {'ds': self.NAMESPACE_DS}
            signatures = root.xpath('//ds:Signature', namespaces=nsmap)
            
            if not signatures:
                return {'valido': False, 'mensaje': 'No se encontró firma en el documento'}
            
            firma = signatures[0]
            
            # Extraer componentes
            signed_info = firma.xpath('.//ds:SignedInfo', namespaces=nsmap)
            sig_value = firma.xpath('.//ds:SignatureValue', namespaces=nsmap)
            
            if not signed_info or not sig_value:
                return {'valido': False, 'mensaje': 'Estructura de firma incompleta'}
            
            return {
                'valido': True,
                'mensaje': 'Firma presente y bien formada',
                'num_firmas': len(signatures)
            }
        
        except Exception as e:
            return {'valido': False, 'mensaje': f'Error validando firma: {str(e)}'}
    
    def obtener_informacion_certificado(self):
        """Retorna información del certificado cargado"""
        return self.info_certificado.copy() if self.info_certificado else {}
