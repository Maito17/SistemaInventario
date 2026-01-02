# reportes/views.py
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F, Value, FloatField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from inventario.models import Producto
from cliente.models import Cliente
from ventas.models import Venta, DetalleVenta
from control.models import RegistroAsistencia
from usuarios.models import EstadoCaja
from django.contrib.auth.models import User


@login_required
def inicio_reportes(request):
    """Vista principal de reportes"""
    context = {
        'titulo': 'Centro de Reportes',
    }
    return render(request, 'reportes/inicio.html', context)


# ==================== REPORTES DE ASISTENCIA ====================

@login_required
def reporte_asistencia(request):
    """Reporte de asistencia del personal"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    
    # Valores por defecto
    hoy = date.today()
    if not fecha_inicio:
        fecha_inicio = (hoy - timedelta(days=7)).isoformat()
    if not fecha_fin:
        fecha_fin = hoy.isoformat()
    
    # Construir query
    registros = RegistroAsistencia.objects.all()
    
    if fecha_inicio:
        registros = registros.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha__lte=fecha_fin)
    if usuario_id:
        registros = registros.filter(user_id=usuario_id)
    
    registros = registros.order_by('-fecha', '-hora_entrada')
    
    # Estadísticas
    total_dias = registros.values('fecha').distinct().count()
    usuarios_activos = registros.values('user').distinct().count()
    
    context = {
        'titulo': 'Reporte de Asistencia',
        'registros': registros,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'usuario_id': usuario_id,
        'usuarios': User.objects.exclude(username='admin'),
        'total_dias': total_dias,
        'usuarios_activos': usuarios_activos,
    }
    return render(request, 'reportes/asistencia.html', context)


# ==================== REPORTES DE CAJA ====================

@login_required
def reporte_caja(request):
    """Reporte de apertura y cierre de caja"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    estado = request.GET.get('estado')
    
    # Valores por defecto
    hoy = date.today()
    if not fecha_inicio:
        fecha_inicio = (hoy - timedelta(days=30)).isoformat()
    if not fecha_fin:
        fecha_fin = hoy.isoformat()
    
    # Construir query
    cajas = EstadoCaja.objects.all()
    
    if fecha_inicio:
        cajas = cajas.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        cajas = cajas.filter(fecha__lte=fecha_fin)
    if usuario_id:
        cajas = cajas.filter(user_id=usuario_id)
    if estado:
        cajas = cajas.filter(estado=estado)
    
    cajas = cajas.order_by('-fecha', '-timestamp_apertura')
    
    # Estadísticas
    total_abierta = cajas.filter(estado='ABIERTA').aggregate(
        total=Sum('monto_inicial')
    )['total'] or 0
    
    total_cerrada = cajas.filter(estado='CERRADA').aggregate(
        total=Sum('monto_cierre')
    )['total'] or 0
    
    total_diferencia = cajas.filter(estado='CERRADA').aggregate(
        diferencia=Sum(F('monto_cierre') - F('monto_inicial'), output_field=FloatField())
    )['diferencia'] or 0
    
    context = {
        'titulo': 'Reporte de Caja',
        'cajas': cajas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'usuario_id': usuario_id,
        'estado': estado,
        'usuarios': User.objects.exclude(username='admin'),
        'total_abierta': total_abierta,
        'total_cerrada': total_cerrada,
        'total_diferencia': total_diferencia,
    }
    return render(request, 'reportes/caja.html', context)


# ==================== REPORTES DE VENTAS ====================

@login_required
def reporte_ventas(request):
    """Reporte de ventas por periodo"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo_reporte = request.GET.get('tipo', 'diario')  # diario, producto, cliente
    
    # Valores por defecto
    hoy = date.today()
    if not fecha_inicio:
        fecha_inicio = (hoy - timedelta(days=30)).isoformat()
    if not fecha_fin:
        fecha_fin = hoy.isoformat()
    
    # Construir query base
    ventas = Venta.objects.filter(
        owner=request.user,
        fecha_venta__gte=fecha_inicio,
        fecha_venta__lte=fecha_fin
    )
    
    if tipo_reporte == 'producto':
        # Agrupar por producto
        ventas_agrupadas = DetalleVenta.objects.filter(
            venta__owner=request.user,
            venta__fecha_venta__gte=fecha_inicio,
            venta__fecha_venta__lte=fecha_fin
        ).values('producto__nombre').annotate(
            total_cantidad=Sum('cantidad'),
            total_monto=Sum(F('cantidad') * F('precio_unitario'), output_field=FloatField()),
            cantidad_ventas=Count('venta_id', distinct=True)
        ).order_by('-total_monto')
        
        context = {
            'titulo': 'Reporte de Ventas por Producto',
            'tipo_reporte': 'producto',
            'ventas': ventas_agrupadas,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        }
    
    elif tipo_reporte == 'cliente':
        # Agrupar por cliente
        ventas_agrupadas = Venta.objects.filter(
            owner=request.user,
            fecha_venta__gte=fecha_inicio,
            fecha_venta__lte=fecha_fin
        ).values('cliente__nombre').annotate(
            total_monto=Sum('total'),
            cantidad_compras=Count('id_venta')
        ).order_by('-total_monto')
        
        context = {
            'titulo': 'Reporte de Ventas por Cliente',
            'tipo_reporte': 'cliente',
            'ventas': ventas_agrupadas,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        }
    
    else:  # diario
        # Agrupar por día
        ventas_agrupadas = Venta.objects.filter(
            owner=request.user,
            fecha_venta__gte=fecha_inicio,
            fecha_venta__lte=fecha_fin
        ).extra(
            select={'fecha': 'DATE(fecha_venta)'}
        ).values('fecha').annotate(
            total_monto=Sum('total'),
            cantidad_ventas=Count('id_venta')
        ).order_by('-fecha')
        
        context = {
            'titulo': 'Reporte de Ventas Diario',
            'tipo_reporte': 'diario',
            'ventas': ventas_agrupadas,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        }
    
    # Totales generales
    total_ventas = ventas.aggregate(
        cantidad=Count('id_venta'),
        monto=Sum('total')
    )
    
    context['total_cantidad'] = total_ventas['cantidad'] or 0
    context['total_monto'] = total_ventas['monto'] or 0
    
    return render(request, 'reportes/ventas.html', context)


# ==================== REPORTES DE CLIENTES ====================

@login_required
def reporte_clientes(request):
    """Reporte de clientes y deudores"""
    from finanzas.models import CuentaPorCobrar
    
    tipo_reporte = request.GET.get('tipo', 'general')  # general, deudores, mejores
    
    if tipo_reporte == 'deudores':
        # Clientes que deben dinero
        clientes = Cliente.objects.filter(
            venta__cuenta_por_cobrar__estado__in=['PENDIENTE', 'PARCIAL'],
            venta__owner=request.user
        ).distinct().annotate(
            total_deuda=Sum(
                'venta__cuenta_por_cobrar__saldo',
                filter=Q(venta__cuenta_por_cobrar__estado__in=['PENDIENTE', 'PARCIAL']) & Q(venta__owner=request.user)
            ),
            cantidad_cuentas=Count('venta__cuenta_por_cobrar', distinct=True)
        ).order_by('-total_deuda')
        
        titulo = 'Reporte de Clientes Deudores'
    
    elif tipo_reporte == 'mejores':
        # Mejores clientes por monto de compra
        clientes = Cliente.objects.annotate(
            total_compras=Sum('venta__total', filter=Q(venta__owner=request.user)),
            cantidad_compras=Count('venta', filter=Q(venta__owner=request.user), distinct=True)
        ).exclude(
            total_compras__isnull=True
        ).order_by('-total_compras')[:20]
        
        titulo = 'Reporte de Mejores Clientes'
    
    else:  # general
        clientes = Cliente.objects.all().annotate(
            total_compras=Coalesce(Sum('venta__total', filter=Q(venta__owner=request.user)), 0),
            cantidad_compras=Count('venta', filter=Q(venta__owner=request.user), distinct=True),
            total_deuda=Coalesce(
                Sum(
                    'venta__cuenta_por_cobrar__saldo',
                    filter=Q(venta__cuenta_por_cobrar__estado__in=['PENDIENTE', 'PARCIAL']) & Q(venta__owner=request.user)
                ),
                0
            )
        ).order_by('-total_compras')
        
        titulo = 'Reporte General de Clientes'
    
    context = {
        'titulo': titulo,
        'clientes': clientes,
        'tipo_reporte': tipo_reporte,
    }
    return render(request, 'reportes/clientes.html', context)


# ==================== REPORTES DE INVENTARIO ====================

@login_required
def reporte_inventario(request):
    """Reporte de inventario y stock"""
    tipo_reporte = request.GET.get('tipo', 'general')  # general, bajo_stock
    
    if tipo_reporte == 'bajo_stock':
        # Productos con bajo stock
        productos = Producto.objects.filter(cantidad__lte=10).order_by('cantidad')
        titulo = 'Reporte de Productos con Bajo Stock'
    else:
        # Todos los productos
        productos = Producto.objects.all().order_by('-cantidad')
        titulo = 'Reporte General de Inventario'
    
    # Calcular estadísticas
    total_productos = productos.count()
    bajo_stock = Producto.objects.filter(cantidad__lte=10).count()
    sin_stock = Producto.objects.filter(cantidad=0).count()
    valor_total_inventario = sum(
        (p.cantidad * (p.precio_costo or 0)) for p in productos
    )
    
    context = {
        'titulo': titulo,
        'productos': productos,
        'tipo_reporte': tipo_reporte,
        'total_productos': total_productos,
        'bajo_stock': bajo_stock,
        'sin_stock': sin_stock,
        'valor_total_inventario': valor_total_inventario,
    }
    return render(request, 'reportes/inventario.html', context)


# ==================== REPORTES FINANCIEROS ====================

@login_required
def reporte_financiero(request):
    """Reporte financiero: ingresos, gastos, utilidades"""
    from finanzas.models import CuentaPorCobrar, CuentaPorPagar
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    # Valores por defecto
    hoy = date.today()
    if not fecha_inicio:
        fecha_inicio = (hoy - timedelta(days=30)).isoformat()
    if not fecha_fin:
        fecha_fin = hoy.isoformat()
    
    # Ingresos por ventas
    ingresos = Venta.objects.filter(
        owner=request.user,
        fecha_venta__gte=fecha_inicio,
        fecha_venta__lte=fecha_fin
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Gastos (sumaremos de varias fuentes)
    # TODO: Si tienes un modelo de gastos, agregarlo aquí
    gastos = 0
    
    # Cuentas por cobrar pendientes
    from finanzas.models import CuentaPorCobrar, CuentaPorPagar
    cuentas_por_cobrar = CuentaPorCobrar.objects.filter(
        owner=request.user,
        estado__in=['PENDIENTE', 'PARCIAL']
    ).aggregate(total=Sum('saldo'))['total'] or 0
    
    # Cuentas por pagar pendientes
    cuentas_por_pagar = CuentaPorPagar.objects.filter(
        owner=request.user,
        estado__in=['PENDIENTE', 'PARCIAL']
    ).aggregate(total=Sum('saldo'))['total'] or 0
    
    # Utilidad neta
    utilidad_neta = ingresos - gastos
    
    context = {
        'titulo': 'Reporte Financiero',
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'ingresos': ingresos,
        'gastos': gastos,
        'utilidad_neta': utilidad_neta,
        'cuentas_por_cobrar': cuentas_por_cobrar,
        'cuentas_por_pagar': cuentas_por_pagar,
    }
    return render(request, 'reportes/financiero.html', context)


# ==================== REPORTES DE PRODUCTOS BAJO STOCK ====================

def productos_bajo_stock(request):
    """Reporte de productos con bajo stock"""
    umbral_stock = 10
    productos = Producto.objects.filter(cantidad__lte=umbral_stock).order_by('cantidad')
    contexto = {
        'productos': productos,
        'umbral': umbral_stock
    }
    return render(request, 'reportes/productos_bajo_stock.html', contexto)
