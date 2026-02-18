from .models import Plan

from .models import Suscripcion
from django.contrib import messages

    # Vista planes_precios eliminada
from django.contrib.auth.decorators import login_required

@login_required
def plan_vencido(request):
    return render(request, 'plan_vencido.html')
from django.core.mail import send_mail
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count, F
from decimal import Decimal
from datetime import datetime, timedelta
import json
import google.generativeai as genai
import os

# Cargar la clave de Gemini desde el entorno
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
from django.views.decorators.csrf import csrf_exempt
# os y json ya los tienes importados según tu código previo
from possitema.forms import AperturaCajaForm, ConfiguracionEmpresaForm, RegistroPagoForm

from .models import RegistroPago
from .models import WebhookLog
import logging
from django.core.mail import mail_admins
from django.contrib.auth import get_user_model
from django.conf import settings

# Vista para registro de pago SaaS
from django.contrib.auth.decorators import login_required
@login_required
def solicitar_pago(request, plan_id=None):
    user = request.user
    plan = None
    if plan_id:
        from .models import Plan
        plan = Plan.objects.filter(id=plan_id).first()
    if request.method == 'POST':
        form = RegistroPagoForm(request.POST, request.FILES)
        if form.is_valid():
            registro = form.save(commit=False)
            registro.usuario = user
            registro.estado = 'Pendiente'
            # Rellenar datos del cliente desde el formulario (si vienen) o usar valores por defecto
            registro.nombre_cliente = request.POST.get('nombre_cliente') or (getattr(user, 'get_full_name', lambda: user.username)() or user.username)
            registro.email_cliente = request.POST.get('email_cliente') or (user.email or '')
            registro.telefono_cliente = request.POST.get('telefono_cliente') or ''
            registro.id_cliente = request.POST.get('id_cliente') or ''
            registro.save()
            messages.success(request, "Tu pago está siendo verificado por nuestra IA. En unos minutos se activará tu plan")
            return redirect('confirmacion_pago')
    else:
        initial = {'plan': plan.id} if plan else {}
        form = RegistroPagoForm(initial=initial)
    # Datos bancarios de ejemplo (puedes personalizar)
    datos_bancarios = [
        {"banco": "Pichincha", "cuenta": "1234567890", "titular": "SaaS Company S.A."},
        {"banco": "Guayaquil", "cuenta": "0987654321", "titular": "SaaS Company S.A."},
    ]
    return render(request, 'confirmacion_pago.html', {
        'form': form,
        'plan': plan,
        'datos_bancarios': datos_bancarios,
    })


@csrf_exempt
def webhook_activar_pago(request):
    """Endpoint para recibir confirmaciones de pago desde n8n y activar suscripciones.

    Espera JSON con: token_secreto, usuario_id, monto_real, plan_id, referencia_bancaria
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=400)

    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    token = payload.get('token_secreto')
    # Obtener token desde settings o variable de entorno
    secret = getattr(settings, 'PAYMENT_WEBHOOK_TOKEN', os.getenv('PAYMENT_WEBHOOK_TOKEN'))
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
    if not secret or token != secret:
        WebhookLog.objects.create(ip_address=ip, status='failed', detail='Token inválido')
        # Alertar admins si hay muchos intentos fallidos desde la misma IP
        try:
            one_hour_ago = timezone.now() - timedelta(hours=1)
            fails_last_hour = WebhookLog.objects.filter(ip_address=ip, status='failed', timestamp__gte=one_hour_ago).count()
            if fails_last_hour >= 5:
                subject = f"Alerta: {fails_last_hour} intentos fallidos de webhook desde {ip}"
                message = f"Se detectaron {fails_last_hour} intentos fallidos al webhook desde la IP {ip} en la última hora."
                try:
                    mail_admins(subject, message)
                except Exception:
                    logging.getLogger(__name__).warning('No se pudo enviar mail a admins para alertar sobre intentos fallidos')
        except Exception:
            pass
        return JsonResponse({'error': 'Token inválido'}, status=400)

    usuario_id = payload.get('usuario_id')
    monto_real = payload.get('monto_real')
    plan_id = payload.get('plan_id')
    referencia = payload.get('referencia_bancaria')

    if not all([usuario_id, monto_real, plan_id, referencia]):
        WebhookLog.objects.create(ip_address=ip, status='failed', detail='Faltan campos requeridos', referencia=referencia)
        return JsonResponse({'error': 'Faltan campos requeridos'}, status=400)

    User = get_user_model()
    try:
        user = User.objects.get(pk=usuario_id)
    except User.DoesNotExist:
        WebhookLog.objects.create(ip_address=ip, status='failed', detail='Usuario no encontrado', referencia=referencia)
        return JsonResponse({'error': 'Usuario no encontrado'}, status=400)

    # Verificar duplicados por referencia (comprobante_id o numero_comprobante)
    if RegistroPago.objects.filter(comprobante_id=referencia).exists() or RegistroPago.objects.filter(numero_comprobante=referencia).exists():
        WebhookLog.objects.create(ip_address=ip, status='failed', detail='Pago ya procesado', referencia=referencia)
        return JsonResponse({'error': 'Pago ya procesado'}, status=400)

    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        WebhookLog.objects.create(ip_address=ip, status='failed', detail='Plan no encontrado', referencia=referencia)
        return JsonResponse({'error': 'Plan no encontrado'}, status=400)

    ahora = timezone.now()
    suscripcion, created = Suscripcion.objects.get_or_create(
        user=user,
        defaults={
            'plan_actual': plan,
            'fecha_inicio': ahora,
            'fecha_vencimiento': ahora + timedelta(days=plan.duracion_dias),
            'esta_activa': True,
        }
    )
    if not created:
        suscripcion.plan_actual = plan
        suscripcion.fecha_inicio = ahora
        suscripcion.fecha_vencimiento = ahora + timedelta(days=plan.duracion_dias)
        suscripcion.esta_activa = True
        suscripcion.save()

    # Registrar pago aprobado
    try:
        registro = RegistroPago.objects.create(
            usuario=user,
            plan=plan,
            numero_comprobante=referencia,
            comprobante_id=referencia,
            comprobante='',
            monto_reportado=monto_real,
            estado='Aprobado',
            fecha_creacion=timezone.now(),
            nombre_cliente=getattr(user, 'get_full_name', lambda: user.username)() or user.username,
            email_cliente=user.email or '',
            telefono_cliente='',
            id_cliente=''
        )
    except Exception as e:
        WebhookLog.objects.create(ip_address=ip, status='failed', detail=f'Error registro: {str(e)}', referencia=referencia)
        return JsonResponse({'error': 'No se pudo registrar el pago', 'detail': str(e)}, status=400)

    # Log success
    WebhookLog.objects.create(ip_address=ip, status='success', detail='Pago aprobado y suscripción activada', referencia=referencia)

    # Detectar intentos fallidos repetidos desde la misma IP en la última hora y alertar
    try:
        one_hour_ago = timezone.now() - timedelta(hours=1)
        fails_last_hour = WebhookLog.objects.filter(ip_address=ip, status='failed', timestamp__gte=one_hour_ago).count()
        if fails_last_hour >= 5:
            subject = f"Alerta: {fails_last_hour} intentos fallidos de webhook desde {ip}"
            message = f"Se detectaron {fails_last_hour} intentos fallidos al webhook de pagos desde la IP {ip} en la última hora. Última referencia: {referencia}\nRevisar logs para más detalles."
            try:
                mail_admins(subject, message)
            except Exception:
                logging.getLogger(__name__).warning('No se pudo enviar mail a admins para alertar sobre intentos fallidos')
    except Exception:
        pass

    return JsonResponse({'message': 'Pago procesado y suscripción activada'}, status=200)

    return JsonResponse({'message': 'Pago procesado y suscripción activada'}, status=200)
@csrf_exempt
def registrar_pago_ia(request):
    """Endpoint simple para registro de pago desde n8n u otros webhooks.

    Espera JSON con: `usuario_id`, `plan_id`, `monto` y `referencia`.
    Crea un `RegistroPago` con estado `Pendiente`.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=400)

    try:
        payload = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    usuario_id = payload.get('usuario_id')
    plan_id = payload.get('plan_id')
    monto = payload.get('monto')
    referencia = payload.get('referencia')

    if not all([usuario_id, plan_id, monto, referencia]):
        return JsonResponse({'error': 'Faltan campos requeridos'}, status=400)

    User = get_user_model()
    try:
        user = User.objects.get(pk=usuario_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=400)

    try:
        plan = Plan.objects.get(pk=plan_id)
    except Plan.DoesNotExist:
        return JsonResponse({'error': 'Plan no encontrado'}, status=400)

    # Evitar duplicados por referencia
    if RegistroPago.objects.filter(comprobante_id=referencia).exists() or RegistroPago.objects.filter(numero_comprobante=referencia).exists():
        return JsonResponse({'error': 'Pago ya procesado'}, status=400)

    try:
        registro = RegistroPago.objects.create(
            usuario=user,
            plan=plan,
            numero_comprobante=referencia,
            comprobante_id=referencia,
            comprobante='',
            monto_reportado=monto,
            estado='Pendiente',
            nombre_cliente=getattr(user, 'get_full_name', lambda: user.username)() or user.username,
            email_cliente=user.email or '',
            telefono_cliente='',
            id_cliente=''
        )
    except Exception as e:
        return JsonResponse({'error': 'No se pudo registrar el pago', 'detail': str(e)}, status=400)

    return JsonResponse({'status': 'success', 'id': registro.id}, status=201)
from ventas.models import Venta, Caja, DetalleVenta
from inventario.models import Producto
from cliente.models import Cliente
from gasto.models import Gasto
from .models import ConfiguracionEmpresa
from .services import registrar_venta_completa, obtener_configuracion_empresa
import os


def enviar_correo_confirmacion(request):
    # This is dummy data, you would get this from a Venta object
    cliente_email = 'cliente@example.com' 
    cliente_nombre = 'Juan Pérez'
    venta_total = 50.00

    subject = 'Confirmación de tu compra en SistemaPOS'
    
    # Render the HTML template for the email body
    html_message = render_to_string('possitema/email_confirmacion.html', {
        'cliente_nombre': cliente_nombre,
        'venta_total': venta_total
    })
    
    # Create a plain text version for email clients that don't support HTML
    plain_message = strip_tags(html_message)
    from_email = 'tucorreo@gmail.com'
    to = [cliente_email]

    send_mail(subject, plain_message, from_email, to, html_message=html_message)

    return HttpResponse("Correo enviado exitosamente.")


@login_required
@permission_required('possitema.can_access_pos', raise_exception=True)
def pos_home(request):
    return render(request, 'dashboard/dashboard.html', {})


# =========================================================================
# VISTA DASHBOARD POS (Class-Based View)
# =========================================================================
class dashboardPOSView(View):
    """Vista principal del dashboard del sistema POS."""
    
    @method_decorator(login_required)
    # @method_decorator(permission_required('possitema.can_access_pos', raise_exception=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get(self, request):
        """Muestra el dashboard con estadísticas del POS."""
        from usuarios.models import EstadoCaja
        
        # Calcular estadísticas con rango de fechas timezone-aware
        ahora = timezone.now()
        hoy = ahora.date()
        
        # Inicio y fin del día actual (en UTC)
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = inicio_dia + timedelta(days=1)
        
        # Inicio del mes
        inicio_mes_dt = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Inicio de hace 7 días
        hace_7_dias_dt = ahora - timedelta(days=7)
        
        # Ventas del mes
        ventas_mes = Venta.objects.filter(
            antendido_por=request.user,
            fecha_venta__gte=inicio_mes_dt
        ).aggregate(
            total=Sum('total'),
            cantidad=Count('id_venta')
        )
        
        # Ventas del día
        ventas_dia = Venta.objects.filter(
            antendido_por=request.user,
            fecha_venta__gte=inicio_dia,
            fecha_venta__lt=fin_dia
        ).aggregate(
            total=Sum('total'),
            cantidad=Count('id_venta')
        )
        
        # Ventas últimos 7 días
        ventas_7dias = Venta.objects.filter(
            antendido_por=request.user,
            fecha_venta__gte=hace_7_dias_dt
        ).aggregate(
            total=Sum('total'),
            cantidad=Count('id_venta')
        )
        
        # Productos con stock bajo (usando 'cantidad' en lugar de 'stock_actual')
        productos_bajo_stock_list = Producto.objects.filter(
            user=request.user,
            cantidad__lte=10
        ).order_by('cantidad')
        
        productos_bajo_stock = productos_bajo_stock_list.count()
        
        # Total de productos
        total_productos = Producto.objects.filter(user=request.user).count()
        
        # Total de clientes
        total_clientes = Cliente.objects.filter(user=request.user).count()
        
        # Verificar si hay caja abierta
        caja_abierta = Caja.objects.filter(
            usuario_apertura=request.user, 
            abierta=True
        ).first()
        
        # Últimas 5 ventas
        ultimas_ventas = Venta.objects.filter(antendido_por=request.user).order_by('-fecha_venta')[:5]
        
        # Top 5 productos más vendidos
        productos_vendidos = DetalleVenta.objects.filter(venta__antendido_por=request.user).values(
            'producto__nombre'
        ).annotate(
            total_vendido=Sum('cantidad')
        ).order_by('-total_vendido')[:5]
        
        # ========== MARGEN DE GANANCIAS ==========
        # Ganancia = (precio_venta - precio_costo) × cantidad
        # Calculamos en Python en lugar de ORM debido a precisión decimal
        
        # Calcular ganancia de hoy
        detalles_dia = DetalleVenta.objects.filter(
            venta__antendido_por=request.user,
            venta__fecha_venta__gte=inicio_dia,
            venta__fecha_venta__lt=fin_dia
        )
        
        total_venta_dia = Decimal('0')
        ganancia_dia = Decimal('0')
        
        for detalle in detalles_dia:
            total_venta_dia += Decimal(str(detalle.subtotal))
            ganancia_unitaria = Decimal(str(detalle.precio_unitario)) - Decimal(str(detalle.costo_al_vender))
            ganancia_dia += ganancia_unitaria * Decimal(str(detalle.cantidad))
        
        # Calcular ganancia de mes
        detalles_mes = DetalleVenta.objects.filter(
            venta__antendido_por=request.user,
            venta__fecha_venta__gte=inicio_mes_dt
        )
        
        total_venta_mes = Decimal('0')
        ganancia_mes = Decimal('0')
        
        for detalle in detalles_mes:
            total_venta_mes += Decimal(str(detalle.subtotal))
            ganancia_unitaria = Decimal(str(detalle.precio_unitario)) - Decimal(str(detalle.costo_al_vender))
            ganancia_mes += ganancia_unitaria * Decimal(str(detalle.cantidad))
        
        # Calcular porcentaje de margen
        margen_porcentaje_dia = ((ganancia_dia / total_venta_dia) * 100) if total_venta_dia > 0 else Decimal('0')
        margen_porcentaje_mes = ((ganancia_mes / total_venta_mes) * 100) if total_venta_mes > 0 else Decimal('0')
        
        # ========== GASTOS DEL MES ==========
        gastos_mes = Gasto.objects.filter(
            owner=request.user,
            fecha_gasto__gte=inicio_mes_dt.date(),
            estado__in=['APROBADO', 'PAGADO']  # Solo contar gastos aprobados o pagados
        ).aggregate(
            total=Sum('monto')
        )
        total_gastos_mes = gastos_mes['total'] or Decimal('0')
        
        # ========== ESTADÍSTICAS DE PERSONAL ==========
        # Usuarios conectados hoy (con login pero sin logout o login más reciente que logout)
        from usuarios.models import RegistroAcceso
        from django.db.models import Q
        
        # Obtener la fecha de hoy en la zona horaria local
        ahora = timezone.now()
        inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = inicio_dia + timedelta(days=1)
        
        # Obtener todos los usuarios que hicieron login hoy (sin duplicados)
        usuarios_con_login = RegistroAcceso.objects.filter(
            tipo_evento='LOGIN',
            fecha_hora__gte=inicio_dia,
            fecha_hora__lt=fin_dia
        ).values_list('user_id', flat=True).distinct()
        
        # Contar usuarios conectados actualmente (tienen login pero no logout después)
        usuarios_conectados_set = set()
        for user_id in usuarios_con_login:
            ultimo_login = RegistroAcceso.objects.filter(
                user_id=user_id,
                tipo_evento='LOGIN',
                fecha_hora__gte=inicio_dia,
                fecha_hora__lt=fin_dia
            ).order_by('-fecha_hora').first()
            
            ultimo_logout = RegistroAcceso.objects.filter(
                user_id=user_id,
                tipo_evento='LOGOUT',
                fecha_hora__gte=inicio_dia,
                fecha_hora__lt=fin_dia
            ).order_by('-fecha_hora').first()
            
            # Si no hay logout o el login es más reciente que el logout, está conectado
            if ultimo_login and (not ultimo_logout or ultimo_login.fecha_hora > ultimo_logout.fecha_hora):
                usuarios_conectados_set.add(user_id)
        
        usuarios_conectados = len(usuarios_conectados_set)
        
        # Cajas abiertas hoy
        cajas_abiertas_hoy = Caja.objects.filter(
            fecha_apertura__date=hoy,
            abierta=True
        ).count()
        
        # Cajas cerradas hoy
        cajas_cerradas_hoy = Caja.objects.filter(
            fecha_apertura__date=hoy,
            abierta=False
        ).count()
        
        # Total de dinero en cajas abiertas hoy
        total_cajas_abiertas = Caja.objects.filter(
            fecha_apertura__date=hoy,
            abierta=True
        ).aggregate(total=Sum('monto_inicial'))['total'] or 0
        
        # ========== CUENTAS POR COBRAR/PAGAR ==========
        from finanzas.models import CuentaPorCobrar, CuentaPorPagar
        
        cuentas_pendientes = CuentaPorCobrar.objects.filter(estado='PENDIENTE').count()
        cuentas_pago_pendiente = CuentaPorPagar.objects.filter(estado='PENDIENTE').count()
        
        total_deuda_clientes = CuentaPorCobrar.objects.filter(
            estado__in=['PENDIENTE', 'PARCIAL']
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        # ========== DETERMINAR PERMISOS DEL USUARIO ==========
        # Verificar si el usuario es un trabajador (caja) o tiene acceso a información financiera
        from usuarios.models import PerfilUsuario
        
        es_trabajador = False
        try:
            perfil = PerfilUsuario.objects.get(user=request.user)
            # Si el rol es 'caja', 'cajero' o similar, es un trabajador
            es_trabajador = perfil.rol.lower() in ['caja', 'cajero', 'empleado', 'vendedor']
        except PerfilUsuario.DoesNotExist:
            pass
        
        context = {
            'nombre_usuario': request.user.get_full_name() or request.user.username,
            'total_ventas_hoy': ventas_dia['cantidad'] or 0,
            'ingresos_hoy': ventas_dia['total'] or 0,
            'total_ventas_mes': ventas_mes['cantidad'] or 0,
            'ingresos_mes': ventas_mes['total'] or 0,
            'total_ventas_7dias': ventas_7dias['cantidad'] or 0,
            'ingresos_7dias': ventas_7dias['total'] or 0,
            'productos_bajo_stock': productos_bajo_stock,
            'productos_bajo_stock_list': productos_bajo_stock_list,
            'total_productos': total_productos,
            'total_clientes': total_clientes,
            'caja_abierta': caja_abierta,
            'ultimas_ventas': ultimas_ventas,
            'productos_vendidos': productos_vendidos,
            'config_empresa': obtener_configuracion_empresa(request.user),
            # Margen de ganancias
            'ganancia_dia': ganancia_dia,
            'ganancia_mes': ganancia_mes,
            'margen_porcentaje_dia': margen_porcentaje_dia,
            'margen_porcentaje_mes': margen_porcentaje_mes,
            # Gastos
            'total_gastos_mes': total_gastos_mes,
            # Personal
            'usuarios_conectados_hoy': usuarios_conectados,
            'cajas_abiertas_hoy': cajas_abiertas_hoy,
            'cajas_cerradas_hoy': cajas_cerradas_hoy,
            'total_cajas_abiertas': total_cajas_abiertas,
            # Cuentas
            'cuentas_pendientes': cuentas_pendientes,
            'cuentas_pago_pendiente': cuentas_pago_pendiente,
            'total_deuda_clientes': total_deuda_clientes,
            # Permisos
            'es_trabajador': es_trabajador,
        }
        
        # Añadir info de suscripción para banner (si aplica)
        try:
            suscripcion_obj = Suscripcion.objects.filter(user=request.user).first()
            if suscripcion_obj:
                dias_restantes = (suscripcion_obj.fecha_vencimiento - timezone.now()).days
                context['suscripcion'] = suscripcion_obj
                context['dias_restantes'] = dias_restantes
            else:
                context['suscripcion'] = None
                context['dias_restantes'] = None
        except Exception:
            context['suscripcion'] = None
            context['dias_restantes'] = None

        return render(request, 'dashboard/dashboard.html', context)


@login_required
def nueva_venta(request):
    """
    Vista principal para el punto de venta (POS).
    Asegura que la PK de la caja abierta se envíe al template.
    Integra información de créditos de clientes.
    """
    from possitema.credit_utils import obtener_resumen_credito_cliente
    
    # Buscar la caja abierta del usuario
    caja_abierta = Caja.objects.filter(usuario_apertura=request.user, abierta=True).first()

    # Si se encuentra una caja, obtenemos su PK, sino, es None.
    caja_pk = caja_abierta.pk if caja_abierta else None
    
    context = {
        'titulo': 'Nueva Venta',
        'caja_pk': caja_pk,
        'caja': caja_abierta,  # Pasar la caja completa
    }
    return render(request, 'ventas/nueva_venta.html', context)



@login_required
@permission_required('possitema.can_view_lista_ventas', raise_exception=True)
def lista_ventas(request):
    """Vista para listar todas las ventas."""
    ventas = Venta.objects.filter(antendido_por=request.user).order_by('-fecha_venta')
    
    context = {
        'titulo': 'Lista de Ventas',
        'ventas': ventas,
    }
    return render(request, 'ventas/lista_ventas.html', context)


@login_required
def apertura_caja(request):
    """
    Gestiona la apertura de caja. Redirecciona a la caja abierta si ya existe.
    """
    # 1. Verificar si ya hay una caja abierta para este usuario
    caja_abierta = Caja.objects.filter(usuario_apertura=request.user, abierta=True).first()
    
    # Si hay una caja abierta, NO mostramos el formulario de apertura
    if caja_abierta:
        messages.info(request, f"Ya tienes una caja abierta (ID: {caja_abierta.pk}).")
        return redirect(reverse('ventas:estado_caja', kwargs={'pk': caja_abierta.pk}))

    # 2. Inicializar el contexto
    context = {
        'titulo': 'Abrir Caja',
        'form': AperturaCajaForm(),
    }

    # 3. Manejar el envío del formulario (POST)
    if request.method == 'POST':
        form = AperturaCajaForm(request.POST)
        if form.is_valid():
            nueva_caja = form.save(commit=False)
            nueva_caja.usuario_apertura = request.user
            nueva_caja.fecha_apertura = timezone.now()
            nueva_caja.abierta = True
            nueva_caja.save()
            
            messages.success(request, f"¡Caja abierta con éxito! Monto inicial: ${nueva_caja.monto_inicial}")
            return redirect(reverse('ventas:estado_caja', kwargs={'pk': nueva_caja.pk}))
        else:
            context['form'] = form 
            messages.error(request, "Error en el formulario de apertura.")

    return render(request, 'ventas/apertura_caja.html', context)


@login_required
def estado_caja(request, pk):
    """
    Muestra el estado actual de una caja abierta.
    """
    caja = get_object_or_404(Caja, pk=pk, usuario_apertura=request.user)

    # Calcular ventas totales
    ventas_totales = Decimal('0.00') 
    saldo_actual_estimado = caja.monto_inicial + ventas_totales

    context = {
        'caja': caja,
        'ventas_totales': ventas_totales,
        'saldo_actual_estimado': saldo_actual_estimado,
        'titulo': f'Estado de Caja ID: {caja.pk}',
    }
    return render(request, 'ventas/estado_caja.html', context)


@login_required
def cierre_caja(request, pk):
    """
    Procesa el cierre de caja.
    """
    caja = get_object_or_404(Caja, pk=pk, usuario_apertura=request.user, abierta=True)

    if request.method == 'POST':
        caja.abierta = False
        caja.fecha_cierre = timezone.now()
        caja.save()

        messages.success(request, f"Caja ID {caja.pk} cerrada con éxito.")
        return redirect(reverse('ventas:nueva_venta'))
    
    return redirect(reverse('ventas:estado_caja', kwargs={'pk': caja.pk}))


# =========================================================================
# VISTAS AJAX
# =========================================================================
@require_POST
@login_required
def buscar_por_nombre_ajax(request):
    """Busca productos por nombre vía AJAX."""
    try:
        data = json.loads(request.body)
        termino = data.get('termino', '').strip()
        
        if len(termino) < 2:
            return JsonResponse({'productos': []})
        
        productos = Producto.objects.filter(
            user=request.user,
        ).filter(
            Q(nombre__icontains=termino) | Q(descripcion__icontains=termino) # Fixed field name from descripcion_icontains to descripcion__icontains if it was wrong, but snippet said descripcion_icontains which is weird. Checking snippet again...
        )[:10]
        
        # FIXED: Usar campos correctos del modelo Producto
        resultados = [{
            'id': p.id_producto,
            'nombre': p.nombre,
            'codigo': p.id_producto,  # Usar id_producto como código
            'precio': str(p.precio),
            'stock': p.cantidad,
        } for p in productos]
        
        return JsonResponse({'productos': resultados})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
def buscar_por_codigo_ajax(request):
    """Busca un producto por código (id_producto) vía AJAX."""
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip()
        
        if not codigo:
            return JsonResponse({'error': 'Código vacío'}, status=400)
        
        try:
            # FIXED: Buscar por id_producto en lugar de 'codigo'
            producto = Producto.objects.get(id_producto=codigo, user=request.user)
            resultado = {
                'id': producto.id_producto,
                'nombre': producto.nombre,
                'codigo': producto.id_producto,
                'precio': str(producto.precio),
                'stock': producto.cantidad,
            }
            return JsonResponse({'producto': resultado})
        
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
@permission_required('possitema.can_access_pos', raise_exception=True)
def procesar_venta_ajax(request):
    """Procesa una venta completa vía AJAX, incluyendo ventas a crédito."""
    try:
        data = json.loads(request.body)
        
        # Obtener items del carrito
        carrito = data.get('carrito', [])
        if not carrito:
            return JsonResponse({'error': 'No hay productos en la venta'}, status=400)
        
        total = Decimal(str(data.get('total', 0)))
        cliente_id = data.get('cliente_id')
        metodo_pago = data.get('metodo_pago', 'efectivo')  # Obtener método de pago
        es_credito = metodo_pago == 'credito'  # Es crédito si el método es 'credito'
        credito_info = data.get('credito_info', {})
        
        # Obtener caja del usuario
        try:
            caja = Caja.objects.filter(usuario_apertura=request.user, abierta=True).latest('fecha_apertura')
        except Caja.DoesNotExist:
            return JsonResponse({'error': 'No hay caja abierta'}, status=400)
        
        # Obtener cliente si está especificado
        cliente = None
        if cliente_id:
            try:
                cliente = Cliente.objects.get(pk=cliente_id)
            except Cliente.DoesNotExist:
                return JsonResponse({'error': 'Cliente no válido'}, status=400)
        
        # Transacción atómica
        with transaction.atomic():
            # Crear venta
            venta = Venta.objects.create(
                caja=caja,
                antendido_por=request.user,
                cliente=cliente,
                total=total,
                metodo_pago=metodo_pago,  # Usar el método de pago seleccionado
                es_credito=es_credito,
                monto_credito=total if es_credito else Decimal('0.00'),
                monto_pagado=Decimal('0.00') if es_credito else total,
                estado_credito='PENDIENTE' if es_credito else 'PAGADO'
            )
            
            # Si es a crédito, registrar en CuentaPorCobrar
            if es_credito and cliente:
                from finanzas.models import CuentaPorCobrar
                from datetime import timedelta
                
                plazo_dias = credito_info.get('plazo', 30)
                fecha_vencimiento = timezone.now().date() + timedelta(days=plazo_dias)
                
                CuentaPorCobrar.objects.create(
                    cliente=cliente,
                    venta=venta,
                    monto_original=total,
                    saldo_pendiente=total,
                    fecha_vencimiento=fecha_vencimiento,
                    notas=f'Venta #{venta.id_venta}'
                )
            
            # Crear detalles de venta
            for item in carrito:
                try:
                    producto = Producto.objects.select_for_update().get(pk=item['id'])
                except Producto.DoesNotExist:
                    raise Exception(f"Producto {item['nombre']} no encontrado.")
                
                cantidad = item.get('cantidad')
                precio = Decimal(str(item.get('precio')))
                subtotal = Decimal(str(item.get('subtotal')))
                
                if producto.cantidad < cantidad:
                    raise Exception(f"Stock insuficiente para {producto.nombre}.")
                
                # Crear detalle
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal,
                    costo_al_vender=producto.precio_costo  # Guardar el costo del producto al momento de venta
                )
                
                # Actualizar stock
                producto.cantidad -= cantidad
                producto.save()
            
            return JsonResponse({
                'success': True,
                'venta_id': venta.id_venta,
                'total': str(venta.total),
                'es_credito': es_credito
            }, status=201)
    
    except Exception as e:
        return JsonResponse({'error': str(e), 'success': False}, status=400)


# =========================================================================
# VISTAS DE CONFIGURACIÓN DE EMPRESA (Segura, sin Django Admin)
# =========================================================================
@login_required
def user_is_superuser(user):
    """Verifica que el usuario sea superusuario."""
    return user.is_superuser


@login_required
def configuracion_empresa_view(request):
    """
    Vista para ver y editar la configuración de la empresa.
    Accesible para todos los usuarios (cada uno tiene su propia config).
    """    
    # Obtener o crear la configuración para el usuario actual
    config = ConfiguracionEmpresa.objects.filter(user=request.user).first()
    
    if request.method == 'POST':
        if config:
            # Editar existente
            form = ConfiguracionEmpresaForm(request.POST, request.FILES, instance=config)
        else:
            # Crear nuevo
            form = ConfiguracionEmpresaForm(request.POST, request.FILES)
        
        if form.is_valid():
            config = form.save(commit=False)
            config.user = request.user
            config.save()
            messages.success(request, f"✅ Configuración de '{config.nombre_empresa}' guardada con éxito.")
            return redirect('configuracion_empresa')
        else:
            messages.error(request, "❌ Error al guardar la configuración. Por favor verifica los datos.")
    else:
        if config:
            form = ConfiguracionEmpresaForm(instance=config)
        else:
            form = ConfiguracionEmpresaForm()
    
    context = {
        'form': form,
        'config': config,
        'titulo': 'Configuración de Empresa',
        'config_empresa': obtener_configuracion_empresa(request.user),
    }
    
    return render(request, 'possitema/configuracion_empresa.html', context)


# =========================================================================
# AJAX PARA ACTUALIZAR INGRESOS EN TIEMPO REAL
# =========================================================================
@login_required
def actualizar_ingresos_ajax(request):
    """
    Vista AJAX que retorna los ingresos actualizados de hoy y del mes.
    Se ejecuta periódicamente desde el dashboard para reflejar cambios en tiempo real.
    """
    ahora = timezone.now()
    
    # Rango de hoy
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = inicio_dia + timedelta(days=1)
    hoy = ahora.date()
    
    # Rango del mes
    inicio_mes_dt = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Consultar ventas completadas de hoy
    ventas_hoy = Venta.objects.filter(
        antendido_por=request.user,
        fecha_venta__gte=inicio_dia,
        fecha_venta__lt=fin_dia
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_venta')
    )
    
    # Consultar ventas completadas del mes
    ventas_mes = Venta.objects.filter(
        antendido_por=request.user,
        fecha_venta__gte=inicio_mes_dt
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_venta')
    )
    
    # ========== ESTADÍSTICAS DE PERSONAL (Usuarios Conectados) ==========
    from usuarios.models import RegistroAcceso
    
    # Obtener todos los usuarios que hicieron login hoy (sin duplicados)
    usuarios_con_login = RegistroAcceso.objects.filter(
        tipo_evento='LOGIN',
        fecha_hora__gte=inicio_dia,
        fecha_hora__lt=fin_dia
    ).values_list('user_id', flat=True).distinct()
    
    # Contar usuarios conectados actualmente (tienen login pero no logout después)
    usuarios_conectados = 0
    for user_id in usuarios_con_login:
        ultimo_login = RegistroAcceso.objects.filter(
            user_id=user_id,
            tipo_evento='LOGIN',
            fecha_hora__gte=inicio_dia,
            fecha_hora__lt=fin_dia
        ).order_by('-fecha_hora').first()
        
        ultimo_logout = RegistroAcceso.objects.filter(
            user_id=user_id,
            tipo_evento='LOGOUT',
            fecha_hora__gte=inicio_dia,
            fecha_hora__lt=fin_dia
        ).order_by('-fecha_hora').first()
        
        # Si no hay logout o el login es más reciente que el logout, está conectado
        if ultimo_login and (not ultimo_logout or ultimo_login.fecha_hora > ultimo_logout.fecha_hora):
            usuarios_conectados += 1
    
    # ========== ESTADÍSTICAS DE CAJAS ==========
    # Cajas abiertas hoy
    cajas_abiertas_hoy = Caja.objects.filter(
        fecha_apertura__date=hoy,
        abierta=True
    ).count()
    
    # Cajas cerradas hoy
    cajas_cerradas_hoy = Caja.objects.filter(
        fecha_apertura__date=hoy,
        abierta=False
    ).count()
    
    # Preparar respuesta JSON
    data = {
        'success': True,
        'ingresos_hoy': float(ventas_hoy['total'] or 0),
        'total_ventas_hoy': ventas_hoy['cantidad'] or 0,
        'ingresos_mes': float(ventas_mes['total'] or 0),
        'total_ventas_mes': ventas_mes['cantidad'] or 0,
        'usuarios_conectados': usuarios_conectados,
        'cajas_abiertas': cajas_abiertas_hoy,
        'cajas_cerradas': cajas_cerradas_hoy,
    }
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
