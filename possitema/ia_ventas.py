import os
import json
import time
import logging
import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, F, Q, Avg
from decimal import Decimal
from datetime import timedelta, date


# ─── Funciones de extracción de datos reales del negocio ───

def _get_resumen_ventas(user):
    """Ventas diarias, semanales y mensuales con tendencias."""
    from ventas.models import Venta, DetalleVenta

    ahora = timezone.now()
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = inicio_dia - timedelta(days=ahora.weekday())
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)

    def _stats(qs):
        agg = qs.aggregate(total=Sum('total'), cantidad=Count('id_venta'))
        return {
            'cantidad': agg['cantidad'] or 0,
            'total': float(agg['total'] or 0),
        }

    ventas_hoy = _stats(Venta.objects.filter(antendido_por=user, fecha_venta__gte=inicio_dia))
    ventas_semana = _stats(Venta.objects.filter(antendido_por=user, fecha_venta__gte=inicio_semana))
    ventas_mes = _stats(Venta.objects.filter(antendido_por=user, fecha_venta__gte=inicio_mes))
    ventas_mes_anterior = _stats(Venta.objects.filter(
        antendido_por=user,
        fecha_venta__gte=inicio_mes_anterior,
        fecha_venta__lt=inicio_mes
    ))

    # Tendencia mes vs mes anterior
    if ventas_mes_anterior['total'] > 0:
        variacion = ((ventas_mes['total'] - ventas_mes_anterior['total']) / ventas_mes_anterior['total']) * 100
    else:
        variacion = 100.0 if ventas_mes['total'] > 0 else 0.0

    # Ventas últimos 7 días desglosadas
    ventas_7_dias = []
    for i in range(6, -1, -1):
        dia = (ahora - timedelta(days=i)).date()
        dia_inicio = timezone.make_aware(timezone.datetime.combine(dia, timezone.datetime.min.time()))
        dia_fin = dia_inicio + timedelta(days=1)
        agg = Venta.objects.filter(
            antendido_por=user, fecha_venta__gte=dia_inicio, fecha_venta__lt=dia_fin
        ).aggregate(total=Sum('total'), cantidad=Count('id_venta'))
        ventas_7_dias.append({
            'fecha': dia.strftime('%Y-%m-%d'),
            'total': float(agg['total'] or 0),
            'cantidad': agg['cantidad'] or 0,
        })

    return {
        'hoy': ventas_hoy,
        'semana': ventas_semana,
        'mes_actual': ventas_mes,
        'mes_anterior': ventas_mes_anterior,
        'variacion_porcentaje_mes': round(variacion, 1),
        'ultimos_7_dias': ventas_7_dias,
    }


def _get_productos_top(user, limite=10):
    """Productos más y menos vendidos."""
    from ventas.models import DetalleVenta

    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_qs = DetalleVenta.objects.filter(
        venta__antendido_por=user,
        venta__fecha_venta__gte=inicio_mes
    ).values('producto__nombre').annotate(
        total_vendido=Sum('cantidad'),
        ingresos=Sum('subtotal'),
        costo_total=Sum(F('costo_al_vender') * F('cantidad')),
    )

    mas_vendidos = list(base_qs.order_by('-total_vendido')[:limite].values(
        'producto__nombre', 'total_vendido', 'ingresos', 'costo_total'
    ))
    menos_vendidos = list(base_qs.order_by('total_vendido')[:5].values(
        'producto__nombre', 'total_vendido', 'ingresos', 'costo_total'
    ))

    # Calcular ganancia por producto
    for p in mas_vendidos + menos_vendidos:
        p['ingresos'] = float(p['ingresos'] or 0)
        p['costo_total'] = float(p['costo_total'] or 0)
        p['ganancia'] = round(p['ingresos'] - p['costo_total'], 2)
        if p['ingresos'] > 0:
            p['margen_pct'] = round((p['ganancia'] / p['ingresos']) * 100, 1)
        else:
            p['margen_pct'] = 0.0

    return {
        'mas_vendidos': mas_vendidos,
        'menos_vendidos': menos_vendidos,
    }


def _get_clientes_info(user):
    """Clientes frecuentes, inactivos y con crédito."""
    from cliente.models import Cliente
    from ventas.models import Venta

    ahora = timezone.now()
    hace_30_dias = ahora - timedelta(days=30)
    hace_60_dias = ahora - timedelta(days=60)

    total_clientes = Cliente.objects.filter(user=user).count()

    # Clientes con compras en últimos 30 días
    clientes_activos_ids = Venta.objects.filter(
        antendido_por=user,
        fecha_venta__gte=hace_30_dias,
        cliente__isnull=False
    ).values_list('cliente_id', flat=True).distinct()
    clientes_activos = len(set(clientes_activos_ids))

    # Clientes que compraron hace 30-60 días pero no en últimos 30
    clientes_30_60_ids = Venta.objects.filter(
        antendido_por=user,
        fecha_venta__gte=hace_60_dias,
        fecha_venta__lt=hace_30_dias,
        cliente__isnull=False
    ).values_list('cliente_id', flat=True).distinct()
    clientes_riesgo = len(set(clientes_30_60_ids) - set(clientes_activos_ids))

    # Top 5 clientes por compras del mes
    top_clientes = list(Venta.objects.filter(
        antendido_por=user,
        fecha_venta__gte=ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        cliente__isnull=False
    ).values('cliente__nombre', 'cliente__apellido').annotate(
        total_compras=Sum('total'),
        num_compras=Count('id_venta')
    ).order_by('-total_compras')[:5])

    for c in top_clientes:
        c['total_compras'] = float(c['total_compras'] or 0)

    # Clientes inactivos (no compran hace más de 60 días, con nombre)
    todos_con_compra = Venta.objects.filter(
        antendido_por=user, cliente__isnull=False
    ).values_list('cliente_id', flat=True).distinct()

    recientes = Venta.objects.filter(
        antendido_por=user, fecha_venta__gte=hace_60_dias, cliente__isnull=False
    ).values_list('cliente_id', flat=True).distinct()

    inactivos_ids = set(todos_con_compra) - set(recientes)
    clientes_inactivos = Cliente.objects.filter(
        id_cliente__in=list(inactivos_ids)[:10]
    ).values('nombre', 'apellido', 'telefono', 'email')

    # Créditos pendientes de clientes
    clientes_con_credito = list(Cliente.objects.filter(
        user=user,
        credito_activo=True
    ).values('nombre', 'apellido', 'limite_credito', 'saldo_credito'))
    for c in clientes_con_credito:
        c['limite_credito'] = float(c['limite_credito'])
        c['saldo_credito'] = float(c['saldo_credito'])
        c['utilizado'] = round(c['limite_credito'] - c['saldo_credito'], 2)

    return {
        'total_clientes': total_clientes,
        'activos_30_dias': clientes_activos,
        'en_riesgo_inactividad': clientes_riesgo,
        'top_clientes_mes': top_clientes,
        'inactivos_60_dias': list(clientes_inactivos),
        'clientes_con_credito': clientes_con_credito,
    }


def _get_margenes_ganancia(user):
    """Rentabilidad del negocio: hoy, mes, margen."""
    from ventas.models import DetalleVenta

    ahora = timezone.now()
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)

    def _calc_ganancia(qs):
        datos = qs.aggregate(
            ingresos=Sum('subtotal'),
            costos=Sum(F('costo_al_vender') * F('cantidad')),
        )
        ingresos = float(datos['ingresos'] or 0)
        costos = float(datos['costos'] or 0)
        ganancia = round(ingresos - costos, 2)
        margen = round((ganancia / ingresos) * 100, 1) if ingresos > 0 else 0.0
        return {'ingresos': ingresos, 'costos': costos, 'ganancia': ganancia, 'margen_pct': margen}

    hoy = _calc_ganancia(DetalleVenta.objects.filter(
        venta__antendido_por=user, venta__fecha_venta__gte=inicio_dia, venta__estado='ACT'
    ))
    mes = _calc_ganancia(DetalleVenta.objects.filter(
        venta__antendido_por=user, venta__fecha_venta__gte=inicio_mes, venta__estado='ACT'
    ))
    mes_anterior = _calc_ganancia(DetalleVenta.objects.filter(
        venta__antendido_por=user,
        venta__fecha_venta__gte=inicio_mes_anterior,
        venta__fecha_venta__lt=inicio_mes,
        venta__estado='ACT'
    ))

    return {
        'hoy': hoy,
        'mes_actual': mes,
        'mes_anterior': mes_anterior,
    }


def _get_gastos_vs_ingresos(user):
    """Salud financiera: gastos vs ingresos."""
    from gasto.models import Gasto
    from ventas.models import Venta

    ahora = timezone.now()
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)

    def _periodo(fecha_desde, fecha_hasta=None):
        filtro_gastos = {'owner': user, 'fecha_gasto__gte': fecha_desde.date(), 'estado__in': ['APROBADO', 'PAGADO']}
        filtro_ventas = {'antendido_por': user, 'fecha_venta__gte': fecha_desde, 'estado': 'ACT'}
        if fecha_hasta:
            filtro_gastos['fecha_gasto__lt'] = fecha_hasta.date()
            filtro_ventas['fecha_venta__lt'] = fecha_hasta

        gastos = float(Gasto.objects.filter(**filtro_gastos).aggregate(t=Sum('monto'))['t'] or 0)
        ingresos = float(Venta.objects.filter(**filtro_ventas).aggregate(t=Sum('total'))['t'] or 0)
        utilidad = round(ingresos - gastos, 2)
        return {'ingresos': ingresos, 'gastos': gastos, 'utilidad_neta': utilidad}

    return {
        'mes_actual': _periodo(inicio_mes),
        'mes_anterior': _periodo(inicio_mes_anterior, inicio_mes),
    }


def _get_stock_alertas(user):
    """Stock bajo y productos próximos a caducar."""
    from inventario.models import Producto

    hoy = date.today()
    en_30_dias = hoy + timedelta(days=30)

    # Productos con stock bajo (≤10 unidades)
    bajo_stock = list(Producto.objects.filter(
        user=user, cantidad__lte=10, estado='ACTIVO'
    ).order_by('cantidad').values('nombre', 'cantidad', 'precio_venta')[:15])
    for p in bajo_stock:
        p['precio_venta'] = float(p['precio_venta'])

    # Productos próximos a caducar (en los próximos 30 días)
    por_caducar = list(Producto.objects.filter(
        user=user,
        fecha_caducidad__isnull=False,
        fecha_caducidad__lte=en_30_dias,
        fecha_caducidad__gte=hoy,
        estado='ACTIVO'
    ).order_by('fecha_caducidad').values('nombre', 'cantidad', 'fecha_caducidad')[:10])
    for p in por_caducar:
        p['fecha_caducidad'] = p['fecha_caducidad'].strftime('%Y-%m-%d')
        p['dias_restantes'] = (date.fromisoformat(p['fecha_caducidad']) - hoy).days

    # Productos ya vencidos
    vencidos = list(Producto.objects.filter(
        user=user,
        fecha_caducidad__isnull=False,
        fecha_caducidad__lt=hoy,
        estado='ACTIVO'
    ).values('nombre', 'cantidad', 'fecha_caducidad')[:10])
    for p in vencidos:
        p['fecha_caducidad'] = p['fecha_caducidad'].strftime('%Y-%m-%d')

    total_productos = Producto.objects.filter(user=user, estado='ACTIVO').count()
    sin_stock = Producto.objects.filter(user=user, cantidad=0, estado='ACTIVO').count()

    return {
        'total_productos_activos': total_productos,
        'sin_stock': sin_stock,
        'bajo_stock': bajo_stock,
        'por_caducar_30_dias': por_caducar,
        'vencidos': vencidos,
    }


def _get_creditos_pendientes(user):
    """Gestión de cuentas por cobrar (créditos a clientes)."""
    from ventas.models import Venta

    ahora = timezone.now()

    creditos = Venta.objects.filter(
        antendido_por=user,
        es_credito=True,
        estado_credito__in=['PENDIENTE', 'PARCIAL']
    ).select_related('cliente')

    total_por_cobrar = 0
    detalle_creditos = []
    vencidos = 0

    for v in creditos[:20]:
        saldo = float(v.saldo_credito)
        total_por_cobrar += saldo
        esta_vencido = v.fecha_vencimiento and v.fecha_vencimiento < ahora.date()
        if esta_vencido:
            vencidos += 1
        detalle_creditos.append({
            'venta_id': v.id_venta,
            'cliente': str(v.cliente) if v.cliente else 'Sin cliente',
            'total_venta': float(v.total),
            'monto_credito': float(v.monto_credito),
            'monto_pagado': float(v.monto_pagado),
            'saldo_pendiente': saldo,
            'fecha_vencimiento': v.fecha_vencimiento.strftime('%Y-%m-%d') if v.fecha_vencimiento else 'Sin fecha',
            'vencido': esta_vencido,
            'estado': v.estado_credito,
        })

    return {
        'total_por_cobrar': round(total_por_cobrar, 2),
        'cantidad_creditos_activos': len(detalle_creditos),
        'creditos_vencidos': vencidos,
        'detalle': detalle_creditos,
    }


def _recopilar_datos_negocio(user):
    """Recopila todos los datos del negocio para el contexto de la IA."""
    try:
        datos = {
            'ventas': _get_resumen_ventas(user),
            'productos_top': _get_productos_top(user),
            'clientes': _get_clientes_info(user),
            'margenes': _get_margenes_ganancia(user),
            'finanzas': _get_gastos_vs_ingresos(user),
            'stock': _get_stock_alertas(user),
            'creditos': _get_creditos_pendientes(user),
        }
        return datos
    except Exception as e:
        return {'error_recopilacion': str(e)}


# ─── Prompt del sistema con datos reales ───

PROMPT_SISTEMA = """Eres un asistente de inteligencia artificial experto en análisis de negocios, ventas y estrategias comerciales.
Tienes acceso a los DATOS REALES del negocio del usuario. Usa estos datos para dar respuestas concretas, específicas y accionables.

REGLAS:
1. Siempre basa tus respuestas en los datos reales proporcionados.
2. Usa cifras y números concretos del negocio cuando estén disponibles.
3. Da recomendaciones prácticas y accionables.
4. Si detectas problemas (stock bajo, caducidad, clientes inactivos, créditos vencidos), alerta proactivamente.
5. Responde SIEMPRE en español.
6. Sé conciso pero completo. Usa viñetas para listas.
7. Si la pregunta no tiene relación con ventas, negocio, finanzas o gestión comercial, indica amablemente que solo puedes ayudar en esos temas.
8. No inventes datos que no estén en el contexto proporcionado.
9. Cuando compares períodos, indica si hay mejora o deterioro con porcentajes.
10. Formatea los montos con el símbolo $ y dos decimales.

DATOS ACTUALES DEL NEGOCIO:
{datos_negocio}
"""


@login_required
@require_POST
def ia_ventas(request):
    """Vista principal del chatbot IA con datos reales del negocio."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    pregunta = data.get('pregunta', '').strip()
    if not pregunta:
        return JsonResponse({'error': 'Pregunta vacía'}, status=400)

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        return JsonResponse({'error': 'La IA no está configurada. Contacte al administrador.'}, status=500)

    # Recopilar datos reales del negocio
    datos = _recopilar_datos_negocio(request.user)
    datos_json = json.dumps(datos, ensure_ascii=False, indent=2, default=str)

    # Construir prompt con contexto real
    prompt_completo = PROMPT_SISTEMA.format(datos_negocio=datos_json)
    prompt_completo += f"\n\nPREGUNTA DEL USUARIO: {pregunta}\n\nRESPUESTA:"

    # Lista de modelos a intentar (si uno falla por cuota, prueba el siguiente)
    MODELOS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    ]

    genai.configure(api_key=GEMINI_API_KEY)
    last_error = None

    for modelo in MODELOS:
        # Intentar hasta 2 veces por modelo (con espera si hay rate limit por minuto)
        for intento in range(2):
            try:
                model = genai.GenerativeModel(modelo)
                response = model.generate_content(prompt_completo)
                respuesta = response.text.strip()
                return JsonResponse({'respuesta': respuesta})
            except Exception as e:
                last_error = str(e)
                es_cuota = '429' in last_error or 'quota' in last_error.lower()

                if es_cuota and intento == 0 and 'PerMinute' in last_error:
                    # Rate limit por minuto: esperar y reintentar el mismo modelo
                    logging.getLogger(__name__).info('Rate limit por minuto en %s, esperando 60s...', modelo)
                    time.sleep(60)
                    continue
                elif es_cuota:
                    # Cuota diaria agotada: pasar al siguiente modelo
                    logging.getLogger(__name__).info('Cuota agotada en %s, intentando siguiente modelo...', modelo)
                    break
                else:
                    # Error no relacionado con cuota
                    logging.getLogger(__name__).error('Error IA Gemini (%s): %s', modelo, last_error)
                    return JsonResponse({'error': f'Error al consultar la IA: {last_error}'}, status=500)

    return JsonResponse({
        'error': 'La cuota gratuita de IA se agotó por hoy. Opciones: 1) Espera unos minutos e intenta de nuevo, '
                 '2) Genera una nueva API key en https://aistudio.google.com/apikey (nuevo proyecto), '
                 '3) Activa facturación en Google AI Studio para cuota ilimitada.'
    }, status=429)
