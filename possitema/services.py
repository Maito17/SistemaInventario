
from django.db import transaction
from decimal import Decimal
from django.shortcuts import get_object_or_404

# Importaciones NECESARIAS para el servicio
from ventas.models import Venta, DetalleVenta
from inventario.models import Producto
from cliente.models import Cliente
from .models import ConfiguracionEmpresa


def obtener_configuracion_empresa(user=None):
    """
    Obtiene la configuración de la empresa para un usuario específico.
    Si no existe, retorna None.
    """
    if user and user.is_authenticated:
        return ConfiguracionEmpresa.objects.filter(user=user).first()
    return None


def registrar_venta_completa(user, carrito_data, total_venta_calculado, cliente_id=None, caja=None, metodo_pago='efectivo'):
    """
    Procesa la venta completa dentro de una transacción atómica.
    Crea la Venta, los DetalleVenta y actualiza el stock de Productos.
    
    Args:
        user: Usuario que realiza la venta
        carrito_data: Lista de diccionarios con info de productos
        total_venta_calculado: Total de la venta
        cliente_id: ID del cliente (opcional)
        caja: Instancia de Caja activa (opcional pero recomendado)
        metodo_pago: Método de pago (efectivo, tarjeta, credito, etc.)
    """
    
    # Iniciar la transacción atómica: si algo falla, todo se revierte
    from finanzas.models import CuentaPorCobrar
    with transaction.atomic():
        # 1. Obtener Cliente (si existe)
        cliente = None
        if cliente_id:
            try:
                # Si el cliente_id es una cadena vacía, lo tratamos como nulo
                cliente_id = cliente_id if cliente_id != '' else None
            except ValueError:
                pass # No hacemos nada si no es un PK válido

        if cliente_id:
            try:
                cliente = Cliente.objects.get(pk=cliente_id)
            except Cliente.DoesNotExist:
                raise Exception("Cliente no encontrado o ID inválido.")
        
        # 2. Crear la instancia de Venta (usando 'antendido_por', 'total' y 'caja')
        es_credito = metodo_pago == 'credito'
        venta = Venta.objects.create(
            antendido_por=user,
            owner=user,
            cliente=cliente, 
            total=total_venta_calculado,
            caja=caja,
            metodo_pago=metodo_pago,
            es_credito=es_credito,
            monto_credito=total_venta_calculado if es_credito else Decimal('0.00'),
            monto_pagado=Decimal('0.00') if es_credito else total_venta_calculado,
            estado_credito='PENDIENTE' if es_credito else 'PAGADA',
        )
        
        detalles_a_crear = []
        productos_a_actualizar = []

        # 3. Procesar cada ítem del carrito
        for item in carrito_data:
            producto_pk = item.get('id') 
            cantidad_vendida = int(item.get('cantidad'))
            precio_unitario = Decimal(str(item.get('precio')))

            try:
                # Bloquear la fila del producto para asegurar consistencia de stock
                # Asumo que el campo de stock en Producto es 'cantidad'
                producto = Producto.objects.select_for_update().get(pk=producto_pk)
            except Producto.DoesNotExist:
                raise Exception(f"Producto ID {producto_pk} no encontrado en el inventario.")

            # Validación de stock 
            if producto.cantidad < cantidad_vendida: 
                raise Exception(f"Stock insuficiente para {producto.nombre}. Disponible: {producto.cantidad}, Solicitado: {cantidad_vendida}.")

            # Preparar DetalleVenta
            subtotal = precio_unitario * cantidad_vendida
            detalles_a_crear.append(DetalleVenta(
                venta=venta,
                producto=producto,
                cantidad=cantidad_vendida,
                precio_unitario=precio_unitario,
                subtotal=subtotal,
                costo_al_vender=producto.precio_costo  # Guardar el costo al momento de venta
            ))
            
            # Descontar stock
            producto.cantidad -= cantidad_vendida 
            productos_a_actualizar.append(producto)

        # 4. Guardar todos los detalles y actualizar stock en masa
        DetalleVenta.objects.bulk_create(detalles_a_crear)
        Producto.objects.bulk_update(productos_a_actualizar, ['cantidad']) 

        # 5. Crear CuentaPorCobrar si la venta es a crédito
        if hasattr(venta, 'es_credito') and venta.es_credito:
            # Usar monto_credito si está definido, si no usar total
            monto_credito = venta.monto_credito if venta.monto_credito > 0 else venta.total
            CuentaPorCobrar.objects.create(
                owner=user,
                venta=venta,
                monto_total=monto_credito,
                monto_cobrado=venta.monto_pagado,
                saldo=monto_credito - venta.monto_pagado,
                fecha_vencimiento=venta.fecha_vencimiento,
            )

        return venta


# ===== FUNCIONES PARA GENERACIÓN DE CLAVE DE ACCESO DEL SRI =====

def calcular_digito_verificador_modulo11(clave_sin_digito: str) -> int:
    """
    Calcula el dígito verificador usando el algoritmo Módulo 11
    según las especificaciones técnicas del SRI Ecuador.
    
    El algoritmo funciona de la siguiente manera:
    1. Multiplicar cada dígito (de derecha a izquierda) por su peso
    2. Los pesos se repiten en secuencia: 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 6, 7, ...
    3. Sumar todos los productos
    4. Dividir la suma entre 11 y obtener el residuo
    5. Restar el residuo de 11
    6. Si el resultado es 11, el dígito es 0
    7. Si el resultado es 10, el dígito es 1
    
    Args:
        clave_sin_digito: String de 48 dígitos sin el dígito verificador
    
    Returns:
        int: Dígito verificador (0-9)
    """
    pesos = [2, 3, 4, 5, 6, 7]
    suma = 0
    
    # Procesar de derecha a izquierda
    for i, digito in enumerate(reversed(clave_sin_digito)):
        peso = pesos[i % 6]  # Los pesos se repiten cada 6 posiciones
        suma += int(digito) * peso
    
    # Calcular residuo
    residuo = suma % 11
    
    # Calcular dígito verificador
    digito_verificador = 11 - residuo
    
    # Ajustes especiales
    if digito_verificador == 11:
        digito_verificador = 0
    elif digito_verificador == 10:
        digito_verificador = 1
    
    return digito_verificador


def generar_clave_acceso_sri(
    fecha_emision: str,
    tipo_comprobante: str,
    ruc: str,
    ambiente: str,
    establecimiento: str,
    punto_emision: str,
    secuencial: str,
    tipo_emision: str
) -> str:
    """
    Genera la Clave de Acceso de 49 dígitos para documentos electrónicos del SRI Ecuador.
    
    Args:
        fecha_emision: Fecha en formato DDMMYYYY (ej: '15022026')
        tipo_comprobante: Código de tipo de comprobante (2 dígitos)
                         Ej: '01'=Factura, '04'=Nota de Crédito, '05'=Nota de Débito
        ruc: RUC del contribuyente (13 dígitos con ceros a la izquierda)
        ambiente: '1' para producción, '2' para prueba
        establecimiento: Código del establecimiento (3 dígitos)
        punto_emision: Código del punto de emisión (3 dígitos)
        secuencial: Número secuencial del comprobante (9 dígitos)
        tipo_emision: '1' normal, '2' indisponibilidad, '3' contingencia
    
    Returns:
        str: Clave de Acceso de 49 dígitos
    
    Raises:
        ValueError: Si los parámetros no tienen el formato correcto
    """
    
    # Validaciones
    if len(fecha_emision) != 8 or not fecha_emision.isdigit():
        raise ValueError("Fecha debe tener formato DDMMYYYY (ej: 15022026)")
    
    if len(tipo_comprobante) != 2 or not tipo_comprobante.isdigit():
        raise ValueError("Tipo de comprobante debe tener 2 dígitos")
    
    if len(ruc) != 13 or not ruc.isdigit():
        raise ValueError(f"RUC debe tener 13 dígitos, se recibió: {ruc}")
    
    if ambiente not in ['1', '2']:
        raise ValueError("Ambiente debe ser '1' (producción) o '2' (prueba)")
    
    if len(establecimiento) != 3 or not establecimiento.isdigit():
        raise ValueError("Establecimiento debe tener 3 dígitos")
    
    if len(punto_emision) != 3 or not punto_emision.isdigit():
        raise ValueError("Punto de emisión debe tener 3 dígitos")
    
    if len(secuencial) != 9 or not secuencial.isdigit():
        raise ValueError(f"Secuencial debe tener 9 dígitos, se recibió: {secuencial}")
    
    if tipo_emision not in ['1', '2', '3']:
        raise ValueError("Tipo de emisión debe ser '1', '2' o '3'")
    
    # Construir la clave sin el dígito verificador (48 dígitos)
    clave_sin_digito = (
        fecha_emision +
        tipo_comprobante +
        ruc +
        ambiente +
        establecimiento +
        punto_emision +
        secuencial +
        tipo_emision
    )
    
    # Calcular dígito verificador usando Módulo 11
    digito_verificador = calcular_digito_verificador_modulo11(clave_sin_digito)
    
    # Clave de acceso completa (49 dígitos)
    clave_acceso = clave_sin_digito + str(digito_verificador)
    
    return clave_acceso


def generar_clave_acceso_desde_venta(venta, config_empresa):
    """
    Genera la Clave de Acceso a partir de una instancia de Venta y ConfiguracionEmpresa.
    
    Args:
        venta: Instancia del modelo Venta
        config_empresa: Instancia del modelo ConfiguracionEmpresa
    
    Returns:
        str: Clave de Acceso de 49 dígitos o None si falta información
    """
    try:
        # Formato de fecha: DDMMYYYY
        fecha_emision = venta.fecha_venta.strftime('%d%m%Y')
        
        # Tipo de comprobante: '01' para factura (por defecto)
        tipo_comprobante = '01'
        
        # RUC: debe tener 13 dígitos
        ruc = str(config_empresa.ruc).zfill(13)
        
        # Ambiente: obtener de config
        ambiente = config_empresa.tipo_ambiente if config_empresa.tipo_ambiente else '2'
        
        # Establecimiento (3 dígitos)
        establecimiento = str(config_empresa.codigo_establecimiento_emisor or '001').zfill(3)
        
        # Punto de emisión (3 dígitos)
        punto_emision = str(config_empresa.codigo_punto_emision or '001').zfill(3)
        
        # Secuencial: usar ID de venta como base (9 dígitos)
        secuencial = str(venta.id_venta).zfill(9)
        
        # Tipo de emisión: '1' para normal
        tipo_emision = config_empresa.tipo_emision if config_empresa.tipo_emision else '1'
        
        # Generar clave
        clave_acceso = generar_clave_acceso_sri(
            fecha_emision,
            tipo_comprobante,
            ruc,
            ambiente,
            establecimiento,
            punto_emision,
            secuencial,
            tipo_emision
        )
        
        return clave_acceso
        
    except (AttributeError, ValueError) as e:
        import logging
        logging.getLogger(__name__).warning('Error al generar clave de acceso: %s', str(e))
        return None


def generar_xml_factura_sri(venta, config_empresa, clave_acceso):
    """
    Genera el XML de la factura conforme a la estructura SRI
    
    Args:
        venta: Instancia de Venta
        config_empresa: Instancia de ConfiguracionEmpresa
        clave_acceso: Clave de acceso SRI de 49 dígitos
    
    Returns:
        str: XML de la factura
    """
    from lxml import etree
    from datetime import datetime
    
    try:
        # Crear raíz del documento
        factura = etree.Element(
            'factura',
            attrib={'id': f'factura_{venta.id_venta}'}
        )
        
        # Información general
        info_tributaria = etree.SubElement(factura, 'infoTributaria')
        
        # Ambiente: 1 = Producción, 2 = Pruebas
        ambiente = etree.SubElement(info_tributaria, 'ambiente')
        ambiente.text = '1'  # Producción por defecto
        
        # Tipo de comprobante: 01 = Factura
        tipo_comprobante = etree.SubElement(info_tributaria, 'tipoComprobante')
        tipo_comprobante.text = '01'
        
        # Razon social
        razon_social = etree.SubElement(info_tributaria, 'razonSocial')
        razon_social.text = config_empresa.nombre_empresa or 'Empresa'
        
        # RUC
        ruc = etree.SubElement(info_tributaria, 'ruc')
        ruc.text = config_empresa.ruc or '0000000000'
        
        # Clave de acceso
        clave_acceso_elem = etree.SubElement(info_tributaria, 'claveAcceso')
        clave_acceso_elem.text = clave_acceso
        
        # Tipo de emisión: 1 = Normal, 2 = Contingencia
        tipo_emision = etree.SubElement(info_tributaria, 'tipoEmision')
        tipo_emision.text = '1'
        
        # Establecimiento, punto de emisión y secuencial
        establecimiento = etree.SubElement(info_tributaria, 'estab')
        establecimiento.text = '001'
        
        punto_emision = etree.SubElement(info_tributaria, 'ptoEmi')
        punto_emision.text = '001'
        
        secuencial = etree.SubElement(info_tributaria, 'secuencial')
        secuencial.text = str(venta.id_venta).zfill(9)
        
        # Dirección matriz
        dir_matriz = etree.SubElement(info_tributaria, 'dirMatriz')
        dir_matriz.text = config_empresa.direccion or 'Ecuador'
        
        # Información de la factura
        info_factura = etree.SubElement(factura, 'infoFactura')
        
        # Fecha
        fecha = etree.SubElement(info_factura, 'fechaEmision')
        fecha.text = datetime.now().strftime('%d/%m/%Y')
        
        # Hora
        hora = etree.SubElement(info_factura, 'horaEmision')
        hora.text = datetime.now().strftime('%H:%M:%S')
        
        # Código de forma de pago
        codigo_pago = etree.SubElement(info_factura, 'codigoFormaPago')
        codigo_pago.text = '01'  # Pago sin utilización del sistema financiero
        
        # Información del cliente
        info_cliente = etree.SubElement(info_factura, 'infoCliente')
        
        tipo_identidad = etree.SubElement(info_cliente, 'tipoIdentificacionComprador')
        if venta.cliente:
            # 05 = RUC, 06 = Cédula, 08 = Identificación en el exterior
            tipo_identidad.text = '05' if venta.cliente.ruc_cedula and len(venta.cliente.ruc_cedula) == 13 else '06'
            
            identidad = etree.SubElement(info_cliente, 'identificacionComprador')
            identidad.text = venta.cliente.ruc_cedula or 'CONSUMIDOR'
            
            razon_cliente = etree.SubElement(info_cliente, 'razonSocialComprador')
            razon_cliente.text = venta.cliente.nombre or 'Consumidor Final'
        else:
            tipo_identidad.text = '07'  # Consumidor final
            identidad = etree.SubElement(info_cliente, 'identificacionComprador')
            identidad.text = '9999999999999'
            razon_cliente = etree.SubElement(info_cliente, 'razonSocialComprador')
            razon_cliente.text = 'Consumidor Final'
        
        # Totales
        totales = etree.SubElement(info_factura, 'totales')
        
        # Calcular subtotal e IVA
        subtotal = Decimal('0.00')
        iva_total = Decimal('0.00')
        
        for detalle in venta.detalles.all():
            subtotal += detalle.subtotal
            tarifa_iva = getattr(detalle.producto, 'tarifa_iva', 15)
            iva_item = (detalle.subtotal * Decimal(str(tarifa_iva))) / Decimal('100')
            iva_total += iva_item
        
        # Si no hay detalles, calcular del total
        if not venta.detalles.exists():
            total_decimal = Decimal(str(venta.total))
            subtotal = total_decimal / Decimal('1.15')
            iva_total = total_decimal - subtotal
        
        # Total sin IVA
        total_sin_impuestos = etree.SubElement(totales, 'totalSinImpuestos')
        total_sin_impuestos.text = f"{subtotal:.2f}"
        
        # Desglose de IVA
        detalles_iva = etree.SubElement(totales, 'totalIva')
        detalles_iva.text = f"{iva_total:.2f}"
        
        # Propina (0)
        propina = etree.SubElement(totales, 'propina')
        propina.text = '0.00'
        
        # Importe total
        importe_total = etree.SubElement(totales, 'importeTotal')
        total_final = subtotal + iva_total
        importe_total.text = f"{total_final:.2f}"
        
        # Detalles de la venta
        detalles = etree.SubElement(factura, 'detalles')
        
        for i, detalle in enumerate(venta.detalles.all(), 1):
            detalle_elem = etree.SubElement(detalles, 'detalle')
            
            linea = etree.SubElement(detalle_elem, 'linea')
            linea.text = str(i)
            
            codigo = etree.SubElement(detalle_elem, 'codigoPrincipal')
            codigo.text = str(detalle.producto.id)
            
            descripcion = etree.SubElement(detalle_elem, 'descripcion')
            descripcion.text = detalle.producto.nombre
            
            cantidad = etree.SubElement(detalle_elem, 'cantidad')
            cantidad.text = str(detalle.cantidad)
            
            precio_unitario = etree.SubElement(detalle_elem, 'precioUnitario')
            precio_unitario.text = f"{detalle.precio:.4f}"
            
            descuento = etree.SubElement(detalle_elem, 'descuento')
            descuento.text = '0.00'
            
            precio_total_sin_impuesto = etree.SubElement(detalle_elem, 'precioTotalSinImpuesto')
            precio_total_sin_impuesto.text = f"{detalle.subtotal:.2f}"
            
            # IVA del detalle
            tarifa_iva = getattr(detalle.producto, 'tarifa_iva', 15)
            iva_detalle = (detalle.subtotal * Decimal(str(tarifa_iva))) / Decimal('100')
            
            impuestos = etree.SubElement(detalle_elem, 'impuestos')
            impuesto = etree.SubElement(impuestos, 'impuesto')
            
            codigo_impuesto = etree.SubElement(impuesto, 'codigo')
            codigo_impuesto.text = '2'  # IVA
            
            coeficiente_iva = etree.SubElement(impuesto, 'coeficiente')
            coeficiente_iva.text = '0'  # Tarifa (0=0%, 1=5%, 2=12%, 3=14%, etc.)
            
            base_imponible = etree.SubElement(impuesto, 'baseImponible')
            base_imponible.text = f"{detalle.subtotal:.2f}"
            
            valor_impuesto = etree.SubElement(impuesto, 'valor')
            valor_impuesto.text = f"{iva_detalle:.2f}"
        
        # Convertir a string
        xml_str = etree.tostring(
            factura,
            xml_declaration=True,
            encoding='UTF-8',
            standalone=True,
            pretty_print=True
        ).decode('utf-8')
        
        return xml_str
    
    except Exception as e:
        import logging
        logging.getLogger(__name__).error('Error generando XML de factura: %s', str(e))
        return None