# ventas/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Caja, Venta, DetalleVenta 
from datetime import date
from decimal import Decimal
from django.db.models import Sum, F
from django.db.models.functions import TruncDay
from inventario.models import Producto
from datetime import date, timedelta
from .decorators import permission_required_message
from django.db import transaction

# --- VISTAS PRINCIPALES DEL PUNTO DE VENTA (POS) ---

@login_required
def nueva_venta(request):
    """
    Vista principal del Punto de Venta (POS).
    Aquí se realiza la selección de productos y el checkout.
    """
    # Verificar si hay una caja abierta para el usuario
    caja_activa = Caja.objects.filter(usuario_apertura=request.user, abierta=True).first()
    
    if not caja_activa:
        messages.warning(request, "Debes abrir un turno de caja antes de realizar ventas.")
        return redirect('ventas:apertura_caja')
        
    context = {
        'caja_pk': caja_activa.pk,
        'caja': caja_activa,
    }
    return render(request, 'ventas/nueva_venta.html', context)

@login_required
def historial_ventas(request):
    """
    Muestra el listado de todas las ventas registradas con paginación.
    """
    from django.core.paginator import Paginator
    
    # Obtener todas las ventas ordenadas por fecha descendente
    ventas_list = Venta.objects.filter(owner=request.user).order_by('-fecha_venta')
    
    # Obtener items por página del GET, por defecto 10
    per_page = int(request.GET.get('per_page', 10))
    
    # Configurar paginación
    paginator = Paginator(ventas_list, per_page)
    page_number = request.GET.get('page')
    ventas = paginator.get_page(page_number)
    
    context = {
        'ventas': ventas,
        'paginator': paginator,
        'page_range': list(paginator.page_range),
    } 
    # El template 'historial_ventas.html' necesita la lista 'ventas'
    return render(request, 'ventas/historial_ventas.html', context)

# --- VISTAS DE CAJA (APERTURA Y CIERRE) ---

@login_required
def apertura_caja(request):
    """
    Gestiona la apertura de un nuevo turno de caja.
    Si el método es POST, procesa el monto inicial.
    Si el método es GET, muestra el formulario.
    """
    # Verificar si ya tiene una caja abierta
    caja_activa = Caja.objects.filter(usuario_apertura=request.user, abierta=True).first()
    if caja_activa:
        messages.warning(request, "Ya tienes una caja abierta. Ciérrala antes de abrir otra.")
        return redirect('ventas:nueva_venta')
    
    # Lógica de procesamiento de formulario POST
    if request.method == 'POST':
        try:
            monto_inicial = float(request.POST.get('monto_inicial'))
        except (ValueError, TypeError):
            messages.error(request, "El monto inicial debe ser un número válido.")
            return redirect('ventas:apertura_caja')
        
        # Crear el objeto Caja
        Caja.objects.create(
            usuario_apertura=request.user,
            monto_inicial=monto_inicial,
            abierta=True
        )
        
        messages.success(request, f"Turno de caja abierto con éxito. Fondo inicial: ${monto_inicial:.2f}")
        return redirect('ventas:nueva_venta') # Redirige al POS
    
    # Lógica para GET (mostrar formulario)
    context = {
        # 'now' se pasa para mostrar la fecha y hora actual en el formulario
        'now': timezone.now() 
    }
    return render(request, 'ventas/apertura_caja.html', context)

@login_required
def estado_caja(request, pk):
    """
    Revisa el estado actual de la caja (si está abierta o lista para cerrar).
    Redirige a cierre_caja para la caja especificada.
    """
    caja = get_object_or_404(Caja, pk=pk, usuario_apertura=request.user)
    
    if not caja.abierta:
        messages.info(request, "Esta caja ya está cerrada.")
        return redirect('ventas:historial_ventas')
    
    return redirect('ventas:cierre_caja', pk=caja.pk)

@login_required
def cierre_caja(request, pk):
    """
    Gestiona el cierre de un turno de caja específico (usando la PK de la caja).
    """
    caja = get_object_or_404(Caja, pk=pk, usuario_apertura=request.user)
    
    # Verificar que la caja esté abierta
    if not caja.abierta:
        messages.info(request, "Esta caja ya está cerrada.")
        return redirect('ventas:historial_ventas')
    
    # Calcular el total de ventas de esta caja
    total_ventas = caja.calcular_total_ventas()
    monto_cierre_esperado = caja.monto_inicial + total_ventas
    caja.monto_cierre_esperado = monto_cierre_esperado
    caja.save()
    
    # 1. Procesar el Formulario de Cierre (POST)
    if request.method == 'POST':
        try:
            monto_cierre_real = Decimal(request.POST.get('monto_cierre'))
        except (ValueError, TypeError, ArithmeticError):
            messages.error(request, "El monto de cierre debe ser un número válido.")
            return redirect('ventas:cierre_caja', pk=pk)
        
        # Actualizar la caja con los datos de cierre
        caja.monto_cierre_real = monto_cierre_real
        caja.fecha_cierre = timezone.now()
        caja.abierta = False
        diferencia = caja.calcular_diferencia()
        caja.save()
        
        if abs(diferencia) < 0.01:
            messages.success(request, "Caja cerrada con éxito. ¡Monto contado coincide perfectamente!")
        elif diferencia > 0:
            messages.warning(request, f"Caja cerrada. ¡Hay un sobrante de ${diferencia:.2f}!")
        else:
            messages.error(request, f"Caja cerrada. ¡Hay un faltante de ${abs(diferencia):.2f}!")
            
        return redirect('ventas:historial_ventas')

    # 2. Mostrar el Formulario de Cierre (GET)
    ventas_caja = caja.ventas_realizadas.all().order_by('-fecha_venta')
    
    context = {
        'caja': caja,
        'total_ventas': total_ventas,
        'monto_cierre_esperado': monto_cierre_esperado,
        'ventas_caja': ventas_caja
    }
    return render(request, 'ventas/cierre_caja.html', context)

# --- VISTAS DE DETALLE / IMPRESIÓN ---

@login_required
def detalle_venta(request, pk):
    """Muestra el detalle completo de una venta específica (pk)."""
    # venta = get_object_or_404(Venta, pk=pk)
    
    # Simulación de datos
    venta_temp = {
        'pk': pk,
        'fecha': timezone.now(),
        'cliente': 'Consumidor Final',
        'total': 75.50,
        'productos': [
            {'nombre': 'Producto A', 'cantidad': 2, 'precio_unitario': 10.00, 'subtotal': 20.00},
            {'nombre': 'Producto B', 'cantidad': 1, 'precio_unitario': 55.50, 'subtotal': 55.50},
        ],
        'atendido_por': request.user.username
    }
    
    context = {'venta': venta_temp}
    return render(request, 'ventas/detalle_venta.html', context)

@login_required
def imprimir_ticket(request, pk):
    """
    Genera el HTML o PDF para la impresión del ticket/factura.
    """
    # Lógica de impresión
    return HttpResponse(f"<h1>Ticket de Venta #{pk}</h1><p>Esta vista generará el ticket de impresión en formato PDF o HTML.</p>")

# --- VISTAS AJAX (JSON) PARA EL POS (nueva_venta) ---

@login_required
def buscar_por_nombre_ajax(request):
    """Busca productos por nombre (usado en la vista 'nueva_venta')."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        query = request.GET.get('q', '')
        # Aquí iría la lógica de búsqueda en el modelo Producto del inventario
        # productos = Producto.objects.filter(nombre__icontains=query)[:10]
        # data = list(productos.values('id', 'nombre', 'precio_venta', 'stock'))
        
        # Datos de simulación
        data = [
            {'id': 1, 'nombre': f'Monitor LED 24"', 'precio_venta': 120.50, 'stock': 15},
            {'id': 2, 'nombre': f'Teclado Mecánico', 'precio_venta': 45.00, 'stock': 50},
        ]
        return JsonResponse(data, safe=False)
    return JsonResponse({'error': 'Método no permitido'}, status=400)
@login_required
def buscar_clientes_vivo(request):
    """Búsqueda en vivo de clientes mientras el usuario escribe."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        query = request.GET.get('q', '').strip()
        
        if len(query) < 1:
            # Retornar opción de consumidor final si no hay búsqueda
            return JsonResponse([
                {
                    'id': '',
                    'nombre': 'Consumidor Final',
                    'email': '',
                    'telefono': '',
                    'is_default': True
                }
            ], safe=False)
        
        try:
            from django.db.models import Q
            from cliente.models import Cliente
            
            # Buscar por nombre, email, teléfono o ID
            clientes = Cliente.objects.filter(
                Q(nombre__icontains=query) | 
                Q(apellido__icontains=query) | 
                Q(email__icontains=query) | 
                Q(telefono__icontains=query) |
                Q(id_cliente__icontains=query)
            )[:15]  # Limitar a 15 resultados
            
            data = [
                {
                    'id': str(p.id_cliente),
                    'nombre': f"{p.nombre} {p.apellido}",
                    'email': p.email,
                    'telefono': p.telefono,
                    'is_default': False
                }
                for p in clientes
            ]
            
            # Agregar opción de consumidor final al inicio
            data.insert(0, {
                'id': '',
                'nombre': 'Consumidor Final',
                'email': '',
                'telefono': '',
                'is_default': True
            })
            
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=400)


@login_required
def buscar_productos_vivo(request):
    """Búsqueda en vivo de productos mientras el usuario escribe."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        query = request.GET.get('q', '').strip()
        
        if len(query) < 1:
            return JsonResponse([], safe=False)
        
        try:
            from django.db.models import Q
            # Buscar por id_producto o nombre
            productos = Producto.objects.filter(
                Q(id_producto__icontains=query) | Q(nombre__icontains=query),
                cantidad__gt=0,  # Solo mostrar productos con stock
                user=request.user
            )[:10]  # Limitar a 10 resultados
            
            data = [
                {
                    'id': p.id_producto,
                    'id_producto': p.id_producto,
                    'nombre': p.nombre,
                    'precio': float(p.precio_venta),
                    'stock': p.cantidad,
                    'categoria': p.categoria.nombre if p.categoria else 'Sin categoría',
                    'tarifa_iva': p.tarifa_iva if hasattr(p, 'tarifa_iva') else 15
                }
                for p in productos
            ]
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=400)


@login_required
def buscar_por_codigo_ajax(request):
    """Busca un producto por código de barras (id_producto) o nombre."""
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            codigo = data.get('codigo_busqueda', '').strip()
            
            if not codigo:
                return JsonResponse({'success': False, 'message': 'Código vacío'}, status=400)
            
            # Buscar por id_producto (código) o por nombre.
            # Intentamos varias estrategias para ser tolerantes con formatos
            from django.db.models import Q
            producto = Producto.objects.filter(
                Q(id_producto__iexact=codigo) | Q(id_producto__icontains=codigo) | Q(nombre__icontains=codigo),
                user=request.user
            ).first()

            # Si no se encontró, intentar un fallback: buscar productos cuyo
            # `id_producto` esté contenido dentro del código escaneado. Esto
            # es útil cuando el lector devuelve un string mayor que el id
            # almacenado (prefijos/sufijos añadidos por el lector o etiqueta).
            if not producto:
                try:
                    # Recolectar candidatos pequeños y comprobar si su id aparece en el código
                    candidatos = Producto.objects.filter(user=request.user).values_list('id_producto', flat=True)
                    for pid in candidatos:
                        if pid and pid in codigo:
                            producto = Producto.objects.filter(id_producto=pid, user=request.user).first()
                            if producto:
                                break
                except Exception:
                    # Si algo falla en el fallback, ignorar y continuar
                    producto = None
            
            if not producto:
                return JsonResponse({'success': False, 'message': 'Producto no encontrado'}, status=404)
            
            # Retornar los datos del producto
            data = {
                'success': True,
                'id': producto.id_producto,
                'id_producto': producto.id_producto,
                'nombre': producto.nombre,
                'precio': float(producto.precio_venta),
                'stock': producto.cantidad,
                'categoria': producto.categoria.nombre if producto.categoria else 'Sin categoría'
            }
            return JsonResponse(data, safe=False)
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Formato JSON inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error en la búsqueda: {str(e)}'}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=400)

@login_required
def procesar_venta_ajax(request):
    """Recibe la lista de productos y la información de pago para registrar la venta."""
    if request.method == 'POST':
        import json
        from possitema.services import registrar_venta_completa
        
        try:
            # 1. Verificar que hay una caja abierta
            caja_activa = Caja.objects.filter(usuario_apertura=request.user, abierta=True).first()
            if not caja_activa:
                return JsonResponse({
                    'success': False, 
                    'error': 'No hay una caja abierta. Abre un turno antes de procesar ventas.'
                }, status=400)
            
            # 2. Parsear datos del carrito
            try:
                json_data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'Datos inválidos. El JSON no se pudo procesar.'
                }, status=400)
                
            carrito_data = json_data.get('carrito', [])
            total_venta = json_data.get('total', 0)
            cliente_id = json_data.get('cliente_id', None)
            
            # Validar carrito
            if not carrito_data:
                return JsonResponse({
                    'success': False,
                    'error': 'El carrito está vacío.'
                }, status=400)
            
            # 3. Llamar al servicio para registrar la venta completa
            venta = registrar_venta_completa(
                user=request.user,
                carrito_data=carrito_data,
                total_venta_calculado=total_venta,
                cliente_id=cliente_id,
                caja=caja_activa  # Vincular venta a caja activa
            )
            
            return JsonResponse({
                'success': True, 
                'venta_id': venta.id_venta, 
                'mensaje': 'Venta registrada con éxito.'
            }, status=200)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=400)
        
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def dashboard_view(request):
    fecha_limite = date.today() + timedelta(days=30)
    productos_proximo_vencer = Producto.objects.filter(
        fecha_caducidad__lte=fecha_limite
    ).exclude(
        stock__lte=0
    ).order_by('fecha_caducidad')
    context = {
        'prodcutos_proximos_vencer': productos_proximo_vencer,
        'conteo_vencer': productos_proximo_vencer.count()
    }
    return render(request, 'base.html')
@login_required
def reportes_ventas_periodo(request):
    from django.db.models import Sum
    from django.utils import timezone
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    hoy = date.today()
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')

    if fecha_inicio_str and fecha_fin_str:
        fecha_inicio = date.fromisoformat(fecha_inicio_str)
        fecha_fin = date.fromisoformat(fecha_fin_str)
    else:
        fecha_inicio = hoy.replace(day=1)  # Primer día del mes actual
        fecha_fin = hoy  # Hoy

    # Convertir fechas a datetime con zona horaria para comparación correcta
    inicio_dt = timezone.make_aware(datetime.combine(fecha_inicio, datetime.min.time()))
    fin_dt = timezone.make_aware(datetime.combine(fecha_fin + timedelta(days=1), datetime.min.time()))

    # Obtener todas las ventas del período
    if request.user.is_staff or request.user.is_superuser:
        ventas_periodo = Venta.objects.filter(
            fecha_venta__gte=inicio_dt,
            fecha_venta__lt=fin_dt
        ).order_by('fecha_venta')
    else:
        # Usuarios normales sólo ven sus propias ventas
        ventas_periodo = Venta.objects.filter(
            fecha_venta__gte=inicio_dt,
            fecha_venta__lt=fin_dt,
            owner=request.user
        ).order_by('fecha_venta')
    
    # Agrupar por día en Python para evitar problemas de zona horaria
    ventas_por_dia = defaultdict(Decimal)
    for venta in ventas_periodo:
        dia = venta.fecha_venta.date()
        ventas_por_dia[dia] += Decimal(str(venta.total))
    
    # Convertir a lista ordenada (con fechas como strings para JSON y formateadas)
    ventas_diarias = [
        {
            'dia': dia.isoformat(),  # Convertir date a string ISO (YYYY-MM-DD) para gráfica
            'dia_formateado': dia.strftime('%d/%m/%Y'),  # Formato para tabla
            'suma_total': str(total)  # Convertir Decimal a string
        }
        for dia, total in sorted(ventas_por_dia.items())
    ]
    
    # Calcular total general
    total_general = sum(ventas_por_dia.values()) if ventas_por_dia else Decimal('0')
    
    # Cantidad de ventas
    cantidad_ventas = ventas_periodo.count()
    
    contexto = {
        'ventas_diarias': ventas_diarias,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_general': total_general,
        'cantidad_ventas': cantidad_ventas,
    }
    return render(request, 'ventas/reportes_ventas.html', contexto)

@login_required
def ranking_productos(request):
    # Obtener todos los detalles con sus cálculos
    if request.user.is_staff or request.user.is_superuser:
        detalle_qs = DetalleVenta.objects.all()
    else:
        # Usuarios normales sólo ven detalles de sus ventas
        detalle_qs = DetalleVenta.objects.filter(venta__owner=request.user)

    reporte_base = detalle_qs.values(
        'producto__nombre'
    ).annotate(
        cantidad_vendida=Sum('cantidad'),
        ingresos_generados=Sum('subtotal'),
        ganancia_total=Sum(F('subtotal') - (F('costo_al_vender') * F('cantidad')))
    )

    # Ranking por cantidad vendida (volumen) - Top 10
    ranking_cantidad = reporte_base.order_by('-cantidad_vendida')[:10]
    
    # Ranking por ingresos generados (valor) - Top 10
    ranking_ingresos = reporte_base.order_by('-ingresos_generados')[:10]
    
    # Ranking por ganancia - Top 10
    ranking_ganancia = reporte_base.order_by('-ganancia_total')[:10]

    context = {
        'ranking_cantidad': ranking_cantidad,
        'ranking_ingresos': ranking_ingresos,
        'ranking_ganancia': ranking_ganancia
    }
    
    return render(request, 'ventas/ranking_productos.html', context)
@login_required
@permission_required_message('ventas.can_anular_venta') # Requiere permiso específico
def anular_venta(request, pk):
    if request.user.is_staff or request.user.is_superuser:
        venta = get_object_or_404(Venta, pk=pk)
    else:
        venta = get_object_or_404(Venta, pk=pk, owner=request.user)

    if venta.estado != 'ACT':
        messages.warning(request, f"La Venta #{pk} ya está {venta.get_estado_display().lower()}.")
        return redirect('ventas:detalle_venta', pk=pk)

    if request.method == 'POST':
        try:
            # 🌟 TRANSACCIÓN ATÓMICA
            with transaction.atomic():
                
                # A. Devolver Stock
                detalles = venta.detalles.select_related('producto')
                for detalle in detalles:
                    producto = detalle.producto
                    if producto:
                        producto.stock += detalle.cantidad
                        producto.save()

                # B. Marcar la Venta como Anulada
                venta.estado = 'ANU'
                venta.anulado_por = request.user
                venta.fecha_anulacion = timezone.now() # Asegúrate de tener este campo en Venta
                venta.save()
            
            messages.success(request, f"¡Venta #{pk} anulada con éxito! El stock ha sido revertido.")
            return redirect('ventas:historial_ventas')

        except Exception as e:
            messages.error(request, f"Error crítico al anular la venta. La base de datos no fue modificada. Error: {e}")
            return redirect('ventas:detalle_venta', pk=pk)

    context = {'venta': venta}
    return render(request, 'ventas/confirmar_anulacion.html', context)

@login_required
@login_required
def generar_ticket(request, pk):
    """Genera el HTML para el ticket de venta (formato pequeño)."""
    from decimal import Decimal
    from possitema.services import obtener_configuracion_empresa
    
    if request.user.is_staff or request.user.is_superuser:
        venta = get_object_or_404(Venta, pk=pk)
    else:
        venta = get_object_or_404(Venta, pk=pk, owner=request.user)
    
    # Calcular subtotal e IVA basándose en los detalles de venta
    detalles = venta.detalles.all()
    subtotal = Decimal('0.00')
    iva_total = Decimal('0.00')
    
    # Iterar por cada detalle para obtener el IVA real usado
    for detalle in detalles:
        subtotal += detalle.subtotal
        # Obtener la tarifa IVA del producto (por defecto 15%)
        tarifa_iva = detalle.producto.tarifa_iva if hasattr(detalle.producto, 'tarifa_iva') else 15
        iva_item = (detalle.subtotal * Decimal(str(tarifa_iva))) / Decimal('100')
        iva_total += iva_item
    
    # Si no hay detalles, usar cálculo alternativo (retro-compatibilidad)
    if not detalles:
        total_decimal = Decimal(str(venta.total))
        subtotal = total_decimal / Decimal('1.15')
        iva_total = total_decimal - subtotal
    
    # Obtener configuración de la empresa
    config_empresa = obtener_configuracion_empresa(request.user)
    
    context = {
        'venta': venta, 
        'formato_ticket': True,
        'subtotal': round(subtotal, 2),
        'iva': round(iva_total, 2),
        'config_empresa': config_empresa,
    }
    return render(request, 'ventas/impresion/ticket_template.html', context)


@login_required
def generar_factura_sri(request, pk):
    """Genera el HTML/PDF para la factura formal con requisitos SRI."""
    from decimal import Decimal
    from possitema.services import obtener_configuracion_empresa
    
    if request.user.is_staff or request.user.is_superuser:
        venta = get_object_or_404(Venta, pk=pk)
    else:
        venta = get_object_or_404(Venta, pk=pk, owner=request.user)
    
    # Calcular subtotal e IVA basándose en los detalles de venta
    detalles = venta.detalles.all()
    subtotal = Decimal('0.00')
    iva_total = Decimal('0.00')
    
    # Iterar por cada detalle para obtener el IVA real usado
    for detalle in detalles:
        subtotal += detalle.subtotal
        # Obtener la tarifa IVA del producto (por defecto 15%)
        tarifa_iva = detalle.producto.tarifa_iva if hasattr(detalle.producto, 'tarifa_iva') else 15
        iva_item = (detalle.subtotal * Decimal(str(tarifa_iva))) / Decimal('100')
        iva_total += iva_item
    
    # Si no hay detalles, usar cálculo alternativo (retro-compatibilidad)
    if not detalles:
        total_decimal = Decimal(str(venta.total))
        subtotal = total_decimal / Decimal('1.15')
        iva_total = total_decimal - subtotal
    
    # Obtener configuración de la empresa
    config_empresa = obtener_configuracion_empresa(request.user)
    
    context = {
        'venta': venta, 
        'formato_sri': True,
        'subtotal': round(subtotal, 2),
        'iva': round(iva_total, 2),
        'config_empresa': config_empresa,
    }
    return render(request, 'ventas/impresion/factura_sri_template.html', context)


# --- VISTA AJAX PARA ENVIAR EMAIL ---

@login_required
def enviar_venta_email(request, pk):
    """
    Vista AJAX para enviar la venta por correo electrónico con PDF adjunto.
    Retorna JSON con el estado del envío.
    """
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.conf import settings
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)
    
    try:
        if request.user.is_staff or request.user.is_superuser:
            venta = get_object_or_404(Venta, pk=pk)
        else:
            venta = get_object_or_404(Venta, pk=pk, owner=request.user)
        
        # Verificar si el cliente tiene email
        if not venta.cliente or not venta.cliente.email:
            return JsonResponse({
                'success': False, 
                'message': 'El cliente no tiene correo registrado'
            })
        
        # Preparar datos para el email
        from decimal import Decimal
        from possitema.services import obtener_configuracion_empresa
        
        total_decimal = Decimal(str(venta.total))
        subtotal = total_decimal / Decimal('1.12')
        iva = total_decimal - subtotal
        config_empresa = obtener_configuracion_empresa(request.user)
        
        # Verificar que la empresa tenga email configurado
        if not config_empresa or not config_empresa.email:
            return JsonResponse({
                'success': False, 
                'message': 'No hay email de empresa configurado. Configúralo en Configuración de Empresa.'
            })
        
        # Verificar que tenga la contraseña de Gmail configurada
        if not config_empresa.gmail_app_password:
            return JsonResponse({
                'success': False, 
                'message': 'No hay contraseña de Gmail configurada. Configúrala en Configuración de Empresa > Configuración de Email.'
            })
        
        # Renderizar el template del email
        html_message = render_to_string('ventas/email_venta.html', {
            'venta': venta,
            'subtotal': round(subtotal, 2),
            'iva': round(iva, 2),
            'config_empresa': config_empresa,
        })
        
        plain_message = strip_tags(html_message)
        
        # Generar PDF usando ReportLab (con tarifa IVA de 12%)
        tarifa_iva = 12
        pdf_bytes = generar_pdf_comprobante(venta, subtotal, iva, config_empresa, tarifa_iva)
        
        # Usar el email de la empresa configurada
        subject = f'Comprobante de Venta #{venta.id_venta} - {config_empresa.nombre_empresa}'
        from_email = config_empresa.email
        to = [venta.cliente.email]
        
        # Crear mensaje con soporte para UTF-8
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=to
        )
        msg.attach_alternative(html_message, "text/html; charset=utf-8")
        
        # Adjuntar PDF
        msg.attach(
            f'comprobante_venta_{venta.id_venta}.pdf',
            pdf_bytes,
            'application/pdf'
        )
        
        # Usar la contraseña de Gmail configurada
        import smtplib
        from django.core.mail.backends.smtp import EmailBackend
        
        # Crear una conexión SMTP con las credenciales de la configuración
        connection = EmailBackend(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=config_empresa.email,  # Usar el email de la empresa
            password=config_empresa.gmail_app_password,  # Usar la contraseña guardada
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False,
        )
        
        msg.connection = connection
        msg.send(fail_silently=False)
        
        # Marcar como enviado
        venta.email_enviado = True
        venta.save(update_fields=['email_enviado'])
        
        return JsonResponse({
            'success': True,
            'message': f'Email con PDF enviado a {venta.cliente.email}',
            'email_enviado': True
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error al enviar email: {str(e)}'
        }, status=500)


# --- FUNCIÓN AUXILIAR PARA GENERAR PDF CON REPORTLAB ---

def generar_pdf_comprobante(venta, subtotal, iva, config_empresa, tarifa_iva=12):
    """
    Genera un PDF del comprobante de venta usando ReportLab.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from io import BytesIO
    
    buffer = BytesIO()
    
    # Crear el PDF
    pdf = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Titulo con nombre de la empresa si está disponible
    if config_empresa and config_empresa.nombre_empresa:
        elements.append(Paragraph(f'COMPROBANTE DE VENTA - {config_empresa.nombre_empresa}', title_style))
    else:
        elements.append(Paragraph('COMPROBANTE DE VENTA', title_style))
    elements.append(Paragraph(f'Venta #{venta.id_venta}', styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Información de la empresa
    if config_empresa:
        company_data = [
            [f'<b>{config_empresa.nombre_empresa}</b>'],
            [f'RUC: {config_empresa.ruc}'],
        ]
        if config_empresa.direccion:
            company_data.append([f'Direccion: {config_empresa.direccion}'])
        if config_empresa.telefono_celular:
            company_data.append([f'Celular: {config_empresa.telefono_celular}'])
        if config_empresa.email:
            company_data.append([f'Email: {config_empresa.email}'])
        
        company_table = Table(company_data, colWidths=[7*inch])
        company_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(company_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Detalles de la venta
    details_data = [
        ['Cliente:', venta.cliente.nombre if venta.cliente else 'Consumidor Final'],
        ['Fecha:', venta.fecha_venta.strftime('%d/%m/%Y %H:%M')],
        ['Metodo de Pago:', venta.get_metodo_pago_display()],
        ['Atendido por:', venta.antendido_por.get_full_name() if venta.antendido_por else 'N/A'],
    ]
    
    details_table = Table(details_data, colWidths=[2*inch, 5*inch])
    details_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.grey),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Tabla de productos
    products_data = [['Producto', 'Cantidad', 'Precio', 'Subtotal']]
    for detalle in venta.detalles.all():
        products_data.append([
            detalle.producto.nombre,
            str(detalle.cantidad),
            f'${detalle.precio_unitario:.2f}',
            f'${detalle.subtotal:.2f}'
        ])
    
    products_table = Table(products_data, colWidths=[3.5*inch, 1*inch, 1.25*inch, 1.25*inch])
    products_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(products_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Totales
    totals_data = [
        ['Subtotal:', f'${float(subtotal):.2f}'],
        [f'IVA ({tarifa_iva}%):', f'${float(iva):.2f}'],
        ['TOTAL:', f'${float(venta.total):.2f}'],
    ]
    
    totals_table = Table(totals_data, colWidths=[5.5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 10),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#667eea')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f0f0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#667eea')),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Pie de página
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    elements.append(Paragraph('Gracias por tu compra', footer_style))
    elements.append(Paragraph('Comprobante generado automaticamente', footer_style))
    
    # Generar el PDF
    pdf.build(elements)
    
    # Retornar los bytes del PDF
    buffer.seek(0)
    return buffer.getvalue()


# --- VISTA PARA DESCARGAR COMPROBANTE EN PDF ---

@login_required
def descargar_comprobante_pdf(request, pk):
    """
    Descarga el comprobante de venta como PDF.
    """
    from decimal import Decimal
    from possitema.services import obtener_configuracion_empresa
    
    if request.user.is_staff or request.user.is_superuser:
        venta = get_object_or_404(Venta, pk=pk)
    else:
        venta = get_object_or_404(Venta, pk=pk, owner=request.user)
    
    # Obtener configuración de la empresa
    config_empresa = obtener_configuracion_empresa(request.user)
    
    # Obtener tarifa de IVA por defecto (12%)
    tarifa_iva = 12  # Tarifa por defecto en Ecuador
    
    # Calcular subtotal e IVA
    total_decimal = Decimal(str(venta.total))
    tasa_iva = Decimal(str(tarifa_iva)) / Decimal('100')
    subtotal = total_decimal / (Decimal('1') + tasa_iva)
    iva = total_decimal - subtotal
    
    # Generar PDF
    pdf_bytes = generar_pdf_comprobante(venta, subtotal, iva, config_empresa, tarifa_iva)
    
    # Retornar como descarga
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="comprobante_venta_{venta.id_venta}.pdf"'
    
    return response


@login_required
def lista_detalles_venta(request):
    """Muestra el listado de todos los detalles de venta."""
    from django.core.paginator import Paginator
    if request.user.is_staff or request.user.is_superuser:
        detalles_list = DetalleVenta.objects.select_related('venta', 'producto').order_by('-venta__fecha_venta')
    else:
        detalles_list = DetalleVenta.objects.select_related('venta', 'producto').filter(venta__owner=request.user).order_by('-venta__fecha_venta')
    
    # Paginación
    paginator = Paginator(detalles_list, 15)
    page_number = request.GET.get('page')
    detalles = paginator.get_page(page_number)
    
    context = {
        'detalles': detalles,
        'paginator': paginator,
    }
    return render(request, 'ventas/lista_detalles_venta.html', context)