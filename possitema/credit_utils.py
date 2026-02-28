# possitema/credit_utils.py
"""Utilidades para manejo de créditos en el POS"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from ventas.models import Venta
from cliente.models import Cliente
from finanzas.models import CuentaPorCobrar, AmortizacionCliente


def puede_vender_credito(cliente, monto_venta):
    """
    Verifica si un cliente puede comprar a crédito.
    Retorna (puede_comprar: bool, mensaje: str, credito_disponible: Decimal)
    """
    if not cliente.credito_activo:
        return False, f"Crédito no activo para {cliente.nombre_completo()}", Decimal('0.00')
    
    if cliente.saldo_credito <= 0:
        return False, f"Sin crédito disponible. Límite: ${cliente.limite_credito:,.2f}", Decimal('0.00')
    
    if monto_venta > cliente.saldo_credito:
        return False, f"Monto excede crédito disponible. Disponible: ${cliente.saldo_credito:,.2f}", cliente.saldo_credito
    
    return True, f"Crédito disponible: ${cliente.saldo_credito:,.2f}", cliente.saldo_credito


def registrar_venta_credito(venta):
    """
    Registra automáticamente una venta a crédito en la tabla de cuentas por cobrar
    """
    if venta.es_credito and venta.monto_credito > 0:
        # Actualizar saldo de crédito del cliente
        cliente = venta.cliente
        if cliente:
            cliente.saldo_credito -= venta.monto_credito
            cliente.save()
        
        # Crear cuenta por cobrar si no existe
        cuenta, created = CuentaPorCobrar.objects.get_or_create(
            venta=venta,
            defaults={
                'monto_total': venta.monto_credito,
                'monto_cobrado': venta.monto_pagado,
                'saldo': venta.saldo_credito,
                'fecha_creacion': timezone.now(),
                'fecha_vencimiento': venta.fecha_vencimiento,
                'estado': venta.estado_credito,
            }
        )
        
        return True, "Crédito registrado exitosamente"
    
    return False, "No es una venta a crédito válida"


def obtener_resumen_credito_cliente(cliente):
    """
    Retorna un resumen del estado crediticio del cliente
    """
    resumen = {
        'limite_credito': cliente.limite_credito,
        'saldo_disponible': cliente.saldo_credito,
        'usado': cliente.limite_credito - cliente.saldo_credito,
        'porcentaje_uso': (((cliente.limite_credito - cliente.saldo_credito) / cliente.limite_credito) * 100) if cliente.limite_credito > 0 else 0,
        'credito_activo': cliente.credito_activo,
    }
    
    # Obtener cuentas pendientes de pago
    cuentas_activas = CuentaPorCobrar.objects.filter(
        venta__cliente=cliente,
        estado__in=['PENDIENTE', 'PARCIAL']
    ).select_related('venta')
    
    resumen['cuentas_activas'] = cuentas_activas.count()
    resumen['saldo_total_pendiente'] = sum(c.saldo for c in cuentas_activas)
    resumen['detalles_pendientes'] = list(cuentas_activas.values(
        'id',
        'venta__id_venta',
        'monto_total',
        'saldo',
        'estado',
        'fecha_vencimiento'
    ))
    
    return resumen


def obtener_historial_metodos_pago(venta):
    """
    Retorna el historial de métodos de pago utilizados en una venta
    """
    from ventas.models import MetodoPagoVenta
    
    metodos = MetodoPagoVenta.objects.filter(venta=venta).values(
        'metodo_pago',
        'monto',
        'referencia'
    )
    
    return list(metodos)


def validar_venta_credito(cliente, monto):
    """
    Valida si la venta a crédito es posible con el cliente
    Retorna diccionario con información de la validación
    """
    validacion = {
        'valida': False,
        'mensaje': '',
        'datos': {
            'cliente': cliente.nombre_completo(),
            'limite_credito': float(cliente.limite_credito),
            'saldo_disponible': float(cliente.saldo_credito),
            'monto_solicitud': float(monto),
            'dias_plazo': cliente.dias_plazo,
        }
    }
    
    if not cliente.credito_activo:
        validacion['mensaje'] = f"Cliente {cliente.nombre_completo()} no tiene crédito activo"
        return validacion
    
    if monto > cliente.saldo_credito:
        validacion['mensaje'] = f"Monto solicitud (${monto}) excede crédito disponible (${cliente.saldo_credito})"
        return validacion
    
    validacion['valida'] = True
    validacion['mensaje'] = f"Venta a crédito válida. Crédito restante: ${cliente.saldo_credito - monto}"
    validacion['datos']['credito_restante'] = float(cliente.saldo_credito - monto)
    
    return validacion
