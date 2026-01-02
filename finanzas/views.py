from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from decimal import Decimal

from .models import (
    CuentaPorPagar, AmortizacionProveedor,
    CuentaPorCobrar, AmortizacionCliente
)
from inventario.models import Compra
from ventas.models import Venta


# ========== PAGOS A PROVEEDORES ==========

@login_required
def lista_cuentas_por_pagar(request):
    """Lista todas las cuentas por pagar a proveedores"""
    # Filtrar por estado si se proporciona
    estado = request.GET.get('estado', '')
    
    cuentas = CuentaPorPagar.objects.select_related('compra__proveedor').filter(owner=request.user)
    
    if estado:
        cuentas = cuentas.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(cuentas, 10)
    page_number = request.GET.get('page')
    cuentas_paginadas = paginator.get_page(page_number)
    
    context = {
        'cuentas': cuentas_paginadas,
        'paginator': paginator,
        'estado_filter': estado,
    }
    return render(request, 'finanzas/lista_cuentas_por_pagar.html', context)


@login_required
def detalle_cuenta_por_pagar(request, pk):
    """Detalle de una cuenta por pagar con su tabla de amortización"""
    cuenta = get_object_or_404(CuentaPorPagar, pk=pk)
    amortizaciones = cuenta.amortizaciones_proveedor.all()
    
    context = {
        'cuenta': cuenta,
        'amortizaciones': amortizaciones,
    }
    return render(request, 'finanzas/detalle_cuenta_por_pagar.html', context)


@login_required
def registrar_pago_proveedor(request, pk):
    """Registrar un nuevo pago a un proveedor"""
    cuenta = get_object_or_404(CuentaPorPagar, pk=pk)
    
    if request.method == 'POST':
        try:
            monto = Decimal(request.POST.get('monto', 0))
            metodo_pago = request.POST.get('metodo_pago', 'efectivo')
            referencia = request.POST.get('referencia', '')
            notas = request.POST.get('notas', '')
            
            if monto <= 0:
                messages.error(request, 'El monto debe ser mayor a 0')
                return redirect('finanzas:detalle_cuenta_por_pagar', pk=pk)
            
            if monto > cuenta.saldo:
                messages.error(request, f'El monto no puede ser mayor al saldo pendiente: ${cuenta.saldo}')
                return redirect('finanzas:detalle_cuenta_por_pagar', pk=pk)
            
            with transaction.atomic():
                # Calcular número de cuota
                numero_cuota = cuenta.amortizaciones_proveedor.count() + 1
                saldo_anterior = cuenta.saldo
                saldo_nuevo = saldo_anterior - monto
                
                # Crear registro de amortización
                AmortizacionProveedor.objects.create(
                    cuenta=cuenta,
                    numero_cuota=numero_cuota,
                    monto_abonado=monto,
                    saldo_anterior=saldo_anterior,
                    saldo_nuevo=saldo_nuevo,
                    metodo_pago=metodo_pago,
                    referencia=referencia,
                    notas=notas,
                )
                
                # Actualizar la cuenta
                cuenta.actualizar_saldo()
                
                messages.success(request, f'Pago de ${monto} registrado exitosamente. Saldo pendiente: ${cuenta.saldo}')
        except Exception as e:
            messages.error(request, f'Error al registrar el pago: {str(e)}')
        
        return redirect('finanzas:detalle_cuenta_por_pagar', pk=pk)
    
    amortizaciones = cuenta.amortizaciones_proveedor.all()
    
    context = {
        'cuenta': cuenta,
        'amortizaciones': amortizaciones,
        'metodos_pago': [
            ('efectivo', 'Efectivo'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
            ('cheque', 'Cheque'),
        ],
    }
    return render(request, 'finanzas/registrar_pago_proveedor.html', context)


# ========== COBROS A CLIENTES ==========

@login_required
def lista_cuentas_por_cobrar(request):
    """Lista todas las cuentas por cobrar a clientes"""
    # Filtrar por estado si se proporciona
    estado = request.GET.get('estado', '')
    
    cuentas = CuentaPorCobrar.objects.select_related('venta__cliente').filter(owner=request.user)
    
    if estado:
        cuentas = cuentas.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(cuentas, 10)
    page_number = request.GET.get('page')
    cuentas_paginadas = paginator.get_page(page_number)
    
    context = {
        'cuentas': cuentas_paginadas,
        'paginator': paginator,
        'estado_filter': estado,
    }
    return render(request, 'finanzas/lista_cuentas_por_cobrar.html', context)


@login_required
def detalle_cuenta_por_cobrar(request, pk):
    """Detalle de una cuenta por cobrar con su tabla de amortización"""
    cuenta = get_object_or_404(CuentaPorCobrar, pk=pk)
    amortizaciones = cuenta.amortizaciones_cliente.all()
    
    context = {
        'cuenta': cuenta,
        'amortizaciones': amortizaciones,
    }
    return render(request, 'finanzas/detalle_cuenta_por_cobrar.html', context)


@login_required
def registrar_cobro_cliente(request, pk):
    """Registrar un nuevo cobro a un cliente"""
    cuenta = get_object_or_404(CuentaPorCobrar, pk=pk)
    
    if request.method == 'POST':
        try:
            monto = Decimal(request.POST.get('monto', 0))
            metodo_pago = request.POST.get('metodo_pago', 'efectivo')
            referencia = request.POST.get('referencia', '')
            notas = request.POST.get('notas', '')
            
            if monto <= 0:
                messages.error(request, 'El monto debe ser mayor a 0')
                return redirect('finanzas:detalle_cuenta_por_cobrar', pk=pk)
            
            if monto > cuenta.saldo:
                messages.error(request, f'El monto no puede ser mayor al saldo pendiente: ${cuenta.saldo}')
                return redirect('finanzas:detalle_cuenta_por_cobrar', pk=pk)
            
            with transaction.atomic():
                # Calcular número de cuota
                numero_cuota = cuenta.amortizaciones_cliente.count() + 1
                saldo_anterior = cuenta.saldo
                saldo_nuevo = saldo_anterior - monto
                
                # Crear registro de amortización
                AmortizacionCliente.objects.create(
                    cuenta=cuenta,
                    numero_cuota=numero_cuota,
                    monto_cobrado=monto,
                    saldo_anterior=saldo_anterior,
                    saldo_nuevo=saldo_nuevo,
                    metodo_pago=metodo_pago,
                    referencia=referencia,
                    notas=notas,
                )
                
                # Actualizar la cuenta
                cuenta.actualizar_saldo()
                
                messages.success(request, f'Cobro de ${monto} registrado exitosamente. Saldo pendiente: ${cuenta.saldo}')
        except Exception as e:
            messages.error(request, f'Error al registrar el cobro: {str(e)}')
        
        return redirect('finanzas:detalle_cuenta_por_cobrar', pk=pk)
    
    amortizaciones = cuenta.amortizaciones_cliente.all()
    
    context = {
        'cuenta': cuenta,
        'amortizaciones': amortizaciones,
        'metodos_pago': [
            ('efectivo', 'Efectivo'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
            ('cheque', 'Cheque'),
        ],
    }
    return render(request, 'finanzas/registrar_cobro_cliente.html', context)


# ========== SOLICITUDES DE CRÉDITO ==========

@login_required
def crear_solicitud_credito(request):
    """Crear una nueva solicitud de crédito desde la venta"""
    from cliente.models import Cliente
    from .models import SolicitudCredito
    
    cliente_id = request.GET.get('cliente_id')
    monto = request.GET.get('monto', 0)
    
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        monto_solicitado = Decimal(request.POST.get('monto_solicitado', 0))
        plazo_dias = int(request.POST.get('plazo_dias', 30))
        motivo = request.POST.get('motivo', '')
        productos_detalle = request.POST.get('productos_detalle', '')
        
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
            
            solicitud = SolicitudCredito.objects.create(
                owner=request.user,
                cliente=cliente,
                monto_solicitado=monto_solicitado,
                plazo_dias=plazo_dias,
                motivo=motivo,
                productos_detalle=productos_detalle,
                estado='PENDIENTE'
            )
            
            messages.success(request, f'Solicitud de crédito #{solicitud.id} creada exitosamente')
            return redirect('finanzas:lista_solicitudes_credito')
            
        except Cliente.DoesNotExist:
            messages.error(request, 'Cliente no válido')
    
    # Obtener cliente si viene en la URL
    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            pass
    
    # Obtener lista de clientes
    clientes = Cliente.objects.all().order_by('nombre')
    
    context = {
        'cliente': cliente,
        'cliente_id': cliente_id,
        'monto': monto,
        'clientes': clientes,
    }
    return render(request, 'finanzas/crear_solicitud_credito.html', context)


@login_required
def lista_solicitudes_credito(request):
    """Lista todas las solicitudes de crédito"""
    from .models import SolicitudCredito
    
    estado = request.GET.get('estado', '')
    
    solicitudes = SolicitudCredito.objects.select_related('cliente', 'aprobado_por').filter(owner=request.user)
    
    if estado:
        solicitudes = solicitudes.filter(estado=estado)
    
    # Paginación
    paginator = Paginator(solicitudes, 15)
    page_number = request.GET.get('page')
    solicitudes_paginadas = paginator.get_page(page_number)
    
    context = {
        'solicitudes': solicitudes_paginadas,
        'paginator': paginator,
        'estado_filter': estado,
    }
    return render(request, 'finanzas/lista_solicitudes_credito.html', context)


@login_required
def detalle_solicitud_credito(request, pk):
    """Ver detalles de una solicitud de crédito"""
    from .models import SolicitudCredito
    
    solicitud = get_object_or_404(SolicitudCredito, pk=pk)
    
    context = {
        'solicitud': solicitud,
    }
    return render(request, 'finanzas/detalle_solicitud_credito.html', context)


@login_required
def aprobar_solicitud_credito(request, pk):
    """Aprobar una solicitud de crédito"""
    from .models import SolicitudCredito
    from django.utils import timezone
    
    solicitud = get_object_or_404(SolicitudCredito, pk=pk)
    
    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '')
        
        solicitud.estado = 'APROBADA'
        solicitud.aprobado_por = request.user
        solicitud.fecha_respuesta = timezone.now()
        solicitud.observaciones = observaciones
        solicitud.save()
        
        messages.success(request, f'Solicitud #{solicitud.id} aprobada')
        return redirect('finanzas:detalle_solicitud_credito', pk=pk)
    
    context = {
        'solicitud': solicitud,
    }
    return render(request, 'finanzas/aprobar_solicitud_credito.html', context)


@login_required
def rechazar_solicitud_credito(request, pk):
    """Rechazar una solicitud de crédito"""
    from .models import SolicitudCredito
    from django.utils import timezone
    
    solicitud = get_object_or_404(SolicitudCredito, pk=pk)
    
    if request.method == 'POST':
        observaciones = request.POST.get('observaciones', '')
        
        solicitud.estado = 'RECHAZADA'
        solicitud.aprobado_por = request.user
        solicitud.fecha_respuesta = timezone.now()
        solicitud.observaciones = observaciones
        solicitud.save()
        
        messages.success(request, f'Solicitud #{solicitud.id} rechazada')
        return redirect('finanzas:lista_solicitudes_credito')
    
    context = {
        'solicitud': solicitud,
    }
    return render(request, 'finanzas/rechazar_solicitud_credito.html', context)


# ========== AMORTIZACIONES A PROVEEDORES ==========

@login_required
def lista_amortizaciones_proveedor(request):
    """Lista todas las amortizaciones registradas a proveedores"""
    amortizaciones = AmortizacionProveedor.objects.select_related(
        'cuenta__compra__proveedor'
    ).order_by('-fecha_pago')
    
    # Paginación
    paginator = Paginator(amortizaciones, 10)
    page_number = request.GET.get('page')
    amortizaciones_paginadas = paginator.get_page(page_number)
    
    context = {
        'amortizaciones': amortizaciones_paginadas,
        'paginator': paginator,
    }
    return render(request, 'finanzas/lista_amortizaciones_proveedor.html', context)


# ========== AMORTIZACIONES A CLIENTES ==========

@login_required
def lista_amortizaciones_cliente(request):
    """Lista todas las amortizaciones registradas de clientes"""
    amortizaciones = AmortizacionCliente.objects.select_related(
        'cuenta__venta__cliente'
    ).order_by('-fecha_cobro')
    
    # Paginación
    paginator = Paginator(amortizaciones, 10)
    page_number = request.GET.get('page')
    amortizaciones_paginadas = paginator.get_page(page_number)
    
    context = {
        'amortizaciones': amortizaciones_paginadas,
        'paginator': paginator,
    }
    return render(request, 'finanzas/lista_amortizaciones_cliente.html', context)
