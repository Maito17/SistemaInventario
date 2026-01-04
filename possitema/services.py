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


def registrar_venta_completa(user, carrito_data, total_venta_calculado, cliente_id=None, caja=None):
    """
    Procesa la venta completa dentro de una transacción atómica.
    Crea la Venta, los DetalleVenta y actualiza el stock de Productos.
    
    Args:
        user: Usuario que realiza la venta
        carrito_data: Lista de diccionarios con info de productos
        total_venta_calculado: Total de la venta
        cliente_id: ID del cliente (opcional)
        caja: Instancia de Caja activa (opcional pero recomendado)
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
        venta = Venta.objects.create(
            antendido_por=user,
            owner=user,
            cliente=cliente, 
            total=total_venta_calculado,
            caja=caja  # Vincular la venta a la caja activa
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
                subtotal=subtotal
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