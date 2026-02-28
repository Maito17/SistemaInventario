# Integración SRI - Web Service de Recepción de Comprobantes

## Descripción General

Este módulo implementa la comunicación con el Web Service de Recepción de Comprobantes del SRI Ecuador utilizando la librería **zeep** (cliente SOAP Python).

### Componentes Principales

1. **enviar_comprobante_sri.py** - Cliente SOAP para el Web Service del SRI
2. **integracion_sri.py** - Integrador de alto nivel que une todo el flujo
3. **test_sri_integracion.py** - Suite de tests completa

---

## Instalación

### 1. Instalar la librería zeep

```bash
pip install zeep>=4.2.1
```

O usar requirements.txt (ya está incluida):

```bash
pip install -r requirements.txt
```

---

## How-To: Enviar un Comprobante al SRI

### Opción 1: Flujo Completo (Recomendado)

Procesa automáticamente: Generación → Firma → Envío

```python
from integracion_sri import IntegradorSRI
from django.contrib.auth.models import User

# Obtener el usuario actual
usuario = User.objects.first()

# Crear integrador
integrador = IntegradorSRI(user=usuario)

# Procesar factura completa
resultado = integrador.procesar_factura_completa(venta_id=123)

# Verificar resultado
if resultado['exito']:
    print(f"✓ Estado: {resultado['estado']}")
    print(f"  Clave de Acceso: {resultado['clave_acceso']}")
else:
    print(f"✗ Error: {resultado['error']}")
    print(f"  Paso actual: {resultado['paso_actual']}")
```

### Opción 2: Cliente Directo

Si tienes el XML ya generado y firmado:

```python
from enviar_comprobante_sri import ClienteSRIRecepcion
from pathlib import Path

# Crear cliente
cliente_sri = ClienteSRIRecepcion(ambiente='pruebas')

# Leer XML firmado
with open('factura_firmada.xml', 'r') as f:
    xml_firmado = f.read()

# Enviar
resultado = cliente_sri.validar_comprobante(xml_firmado)

# Analizar resultado
print(f"Estado: {resultado['estado']}")
if resultado['exito']:
    print(f"Autorización: RECIBIDA")
else:
    print(f"Error: {resultado['mensaje']}")
```

### Opción 3: Consultar Autorización

Verificar el estado de un comprobante ya enviado:

```python
# Consultar por clave de acceso (49 dígitos)
resultado = integrador.consultar_autorizacion(
    clave_acceso='2202202601123456789012001001000000027'
)

if resultado['exito']:
    print(f"Estado: {resultado['respuesta']}")
else:
    print(f"Error: {resultado['error']}")
```

---

## Estructura de Respuestas

### Respuesta Exitosa (Estado RECIBIDA)

```python
{
    'exito': True,
    'estado': 'RECIBIDA',
    'clave_acceso': '2202202601123456789012001001000000027',
    'timestamp': '2026-02-22T17:54:38.123456',
    'mensaje': 'El comprobante fue recibido correctamente por el SRI',
    'ambiente': 'pruebas'
}
```

### Respuesta de Error (No Autorizado)

```python
{
    'exito': False,
    'estado': 'NO_AUTORIZADO',
    'clave_acceso': '2202202601123456789012001001000000027',
    'timestamp': '2026-02-22T17:54:38.123456',
    'mensaje': 'El comprobante no fue autorizado. Verificar datos tributarios',
    'tipo_error': 'NO_AUTORIZADO',
    'ambiente': 'pruebas'
}
```

### Respuesta de Error (Validación)

```python
{
    'exito': False,
    'estado': 'ERROR_VALIDACION',
    'clave_acceso': '2202202601123456789012001001000000027',
    'timestamp': '2026-02-22T17:54:38.123456',
    'mensaje': 'Error en la validación del comprobante: ...',
    'tipo_error': 'ERROR_VALIDACION',
    'ambiente': 'pruebas'
}
```

---

## Integración con Vistas Django

### Actualizar Vista de Generación de Factura

```python
from django.shortcuts import render
from django.http import JsonResponse
from integracion_sri import procesar_factura_view_helper

def generar_factura_sri_view(request, pk):
    """Vista mejorada que genera y envía factura al SRI"""
    
    try:
        # Procesar factura completa
        resultado = procesar_factura_view_helper(request, venta_id=pk)
        
        # Responder al cliente
        return JsonResponse({
            'exito': resultado['exito'],
            'estado': resultado.get('estado'),
            'clave_acceso': resultado.get('clave_acceso'),
            'mensaje': resultado.get('mensaje'),
            'detalles': resultado.get('respuesta_sri')
        })
        
    except Exception as e:
        return JsonResponse({
            'exito': False,
            'error': str(e),
            'mensaje': 'Error procesando factura'
        }, status=500)
```

---

## Estados Posibles del Comprobante

| Estado | Significado | Acción |
|--------|-------------|--------|
| RECIBIDA | ✓ Aceptado por el SRI | Guardar clave de acceso, mostrar al usuario |
| NO_AUTORIZADO | ✗ Rechazado por datos | Revisar RUC, fecha, establecimiento |
| ERROR_VALIDACION | ✗ XML mal formado | Verificar estructura XML |
| DESCONOCIDO | ? Respuesta inesperada | Contactar soporte SRI |

---

## Flujo Completo: De Venta a Autorización

```
┌─────────────────────────────┐
│ 1. CREAR VENTA              │
│ Producto → Cantidad → Total │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ 2. GENERAR CLAVE ACCESO     │
│ Date+RUC+Ambiente+Sequencial│
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ 3. GENERAR XML              │
│ Estructura SRI validada     │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ 4. FIRMAR DIGITALMENTE      │
│ RSA-SHA256 + XAdES-BES      │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ 5. ENVIAR AL SRI            │
│ SOAP Web Service            │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│ 6. REGISTRAR AUTORIZACIÓN   │
│ Guardar estado en BD        │
└─────────────────────────────┘
```

---

## Configuración Requerida

### En ConfiguracionEmpresa

| Campo | Descripción | Requerido |
|-------|-------------|-----------|
| ruc | RUC de 13 dígitos | ✓ |
| nombre_empresa | Razón social | ✓ |
| codigo_establecimiento_emisor | 001-999 | ✓ |
| codigo_punto_emision | 001-999 | ✓ |
| tipo_ambiente | '1' (prod) o '2' (pruebas) | ✓ |
| tipo_emision | '1' (normal) o '2' (contingencia) | ✓ |
| clave_firma_electronica | Archivo P12/PFX | Opcional* |

*Obligatorio para firmar, opcional si se envía sin firma

### En Model User

Cada usuario debe tener una única ConfiguracionEmpresa asociada.

---

## Pruebas y Validación

### Ejecutar Suite de Tests

```bash
python test_sri_integracion.py -v
```

**Resultado esperado:**
```
Ran 12 tests in 4.782s
OK
```

### Tests por Componente

**TestClienteSRIRecepcion** (6 tests)
- Inicialización del cliente
- Validación de clave de acceso
- Generación de estructura XML
- Encoding UTF-8
- Procesamiento de respuestas (éxito/error)

**TestIntegradorSRI** (3 tests)
- Inicialización del integrador
- Validación de configuración
- Procesamiento de factura sin certificado

**TestXMLGeneracion** (3 tests)
- XML bien formado
- Campos obligatorios presentes
- Encoding correcto

---

## Diagnóstico y Troubleshooting

### Error: "404 Client Error"

**Causa:** Endpoint del SRI no disponible o URL incorrecta.

**Solución:**
```python
# Verificar URL
print(ClienteSRIRecepcion.URL_WS_SRI_PRUEBAS)
# https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesService?wsdl

# O usar producción
cliente = ClienteSRIRecepcion(ambiente='produccion')
```

### Error: "Clave de acceso inválida"

**Causa:** La clave no tiene 49 dígitos.

**Solución:**
```python
clave = generar_clave_acceso_desde_venta(venta, config)
if len(clave) != 49:
    print(f"Error: Clave generada con {len(clave)} dígitos")
    # Verificar campos en ConfiguracionEmpresa
```

### Error: "No hay certificado digital configurado"

**Causa:** El usuario no ha cargado su certificado P12.

**Solución:**
```python
# El sistema envía XML sin firma (permitido en pruebas)
# En producción, configurar certificado en:
# ConfiguracionEmpresa.clave_firma_electronica
```

### Error: "XML mal formado"

**Causa:** Estructura del XML incorrecta.

**Solución:**
```python
from lxml import etree
try:
    root = etree.fromstring(xml.encode('utf-8'))
    print("✓ XML válido")
except etree.XMLSyntaxError as e:
    print(f"✗ Error: {e}")
```

---

## Ambientes

### Pruebas (Recomendado para Desarrollo)

```python
cliente = ClienteSRIRecepcion(ambiente='pruebas')
# URL: https://celcer.sri.gob.ec/comprobantes-electronicos-ws/...
```

### Producción

```python
cliente = ClienteSRIRecepcion(ambiente='produccion')
# URL: https://cel.sri.gob.ec/comprobantes-electronicos-ws/...
```

⚠️ **Nota:** Cambiar a producción solo cuando esté completamente validado.

---

## Campos Obligatorios en XML

El XML generado y enviado debe contener:

```xml
<factura>
  <infoTributaria>
    <ambiente>2</ambiente>                    <!-- 1=Prod, 2=Pruebas -->
    <tipoComprobante>01</tipoComprobante>    <!-- Factura -->
    <razonSocial>Empresa SA</razonSocial>
    <ruc>1234567890123</ruc>                 <!-- 13 dígitos -->
    <claveAcceso>2202202601123456789...</claveAcceso>  <!-- 49 dígitos -->
    <tipoEmision>1</tipoEmision>             <!-- 1=Normal, 2=Contingencia -->
    <estab>001</estab>                       <!-- Establecimiento -->
    <ptoEmi>001</ptoEmi>                     <!-- Punto de emisión -->
    <secuencial>000000001</secuencial>       <!-- 9 dígitos -->
    <dirMatriz>Dirección empresa</dirMatriz>
  </infoTributaria>
  
  <infoFactura>
    <fechaEmision>22/02/2026</fechaEmision>
    <horaEmision>17:54:38</horaEmision>
    <codigoFormaPago>01</codigoFormaPago>    <!-- Forma de pago -->
    <!-- Detalles del cliente, totales, etc. -->
  </infoFactura>
  
  <!-- Si está firmado, debe contener: -->
  <Signature>...</Signature>
</factura>
```

---

## Respuesta SOAP Válida

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <ValidarComprobanteResponse>
      <RespuestaSRI>
        <estado>RECIBIDA</estado>
        <numeroComprobantes>1</numeroComprobantes>
        <comprobantes>
          <comprobante>
            <claveAcceso>2202202601123456789012001001000000027</claveAcceso>
            <estado>RECIBIDA</estado>
          </comprobante>
        </comprobantes>
      </RespuestaSRI>
    </ValidarComprobanteResponse>
  </soap:Body>
</soap:Envelope>
```

---

## Seguridad

### Temas de Seguridad Implementados

✓ **Encriptación de Contraseña P12**
- Almacenada cifrada en BD usando Fernet
- Se desencripta solo cuando se necesita

✓ **Validación de XML**
- Estructura verificada con lxml
- Encoding UTF-8 garantizado

✓ **HTTPS/TLS**
- Comunicación segura con el SRI
- Certificados validados

✓ **Manejo de Errores**
- Excepciones capturadas y registradas
- Respuestas informativas sin exponer datos sensibles

### Recomendaciones

1. **No guardar contraseña en texto plano**
2. **Usar HTTPS en producción**
3. **Validar entrada de datos antes de generar XML**
4. **Registrar todos los envíos y respuestas**
5. **Mantener respaldo de los comprobantes enviados**

---

## Logging

El sistema registra todas las operaciones:

```python
import logging

logger = logging.getLogger('enviar_comprobante_sri')

# Configurar nivel
logger.setLevel(logging.INFO)

# Mensajes generad automáticamente:
# INFO: Conexión al SRI
# INFO: XML validado
# WARNING: XML sin firma
# ERROR: Errores de envío
```

### Ver Logs

```bash
# En Django
tail -f logs/django.log | grep SRI

# O ejecutar directamente
python enviar_comprobante_sri.py
```

---

## API Completa

### ClienteSRIRecepcion

```python
class ClienteSRIRecepcion:
    def __init__(self, ambiente: str = 'pruebas')
    def validar_comprobante(self, xml_firmado: str) -> Dict
    def obtener_autorizacion(self, clave_acceso: str) -> Dict
```

### IntegradorSRI

```python
class IntegradorSRI:
    def __init__(self, user)
    def procesar_factura_completa(self, venta_id: int) -> Dict
    def consultar_autorizacion(self, clave_acceso: str) -> Dict
```

### Funciones Auxiliares

```python
def enviar_xml_factura_sri(ruta_xml: Path, ambiente: str = 'pruebas') -> Dict
def test_conexion_sri(ambiente: str = 'pruebas') -> bool
def generar_xml_ejemplo() -> str
```

---

## Roadmap Futuro

- [ ] Soporte para otros tipos de comprobantes (Nota Crédito, Guía Remisión)
- [ ] Almacenamiento de historial en BD
- [ ] Dashboard de estado de autorizaciones
- [ ] Reintentos automáticos en caso de error
- [ ] Webhook para notificaciones asincrónicas
- [ ] Integración con Email para confirmaciones

---

## Contacto y Soporte

**SRI Ecuador**
- **Web:** https://www.sri.gob.ec
- **Ambiente de Pruebas:** https://celcer.sri.gob.ec
- **Producción:** https://cel.sri.gob.ec

**Documentación SRI**
- Especificación XSD de comprobantes
- Guía de integración SOAP
- Códigos de error y validación

---

## Licencia

Este módulo forma parte del Sistema de Venta Casa y está disponible bajo la misma licencia del proyecto.

---

**Última actualización:** 22 de febrero de 2026  
**Versión:** 1.0  
**Estado:** Producción
