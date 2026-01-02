# usuarios/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import logging

from .models import RegistroAcceso, EstadoCaja

logger = logging.getLogger(__name__)


def obtener_ip_cliente(request):
    """Obtiene la IP del cliente desde la request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def obtener_user_agent(request):
    """Obtiene el User-Agent del cliente"""
    return request.META.get('HTTP_USER_AGENT', 'No especificado')


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    """
    Señal que se dispara cuando un usuario inicia sesión.
    Registra automáticamente la entrada en RegistroAcceso
    """
    try:
        ip = obtener_ip_cliente(request)
        user_agent = obtener_user_agent(request)
        
        # Intentar obtener el último logout para calcular duración
        ultimo_logout = RegistroAcceso.objects.filter(
            user=user,
            tipo_evento='LOGOUT'
        ).order_by('-fecha_hora').first()
        
        RegistroAcceso.objects.create(
            user=user,
            tipo_evento='LOGIN',
            ip_address=ip,
            user_agent=user_agent,
            notas=f'Login exitoso desde {ip}'
        )
        logger.info(f"Login registrado para usuario: {user.username} desde IP: {ip}")
        
    except Exception as e:
        logger.error(f"Error registrando login para {user.username}: {str(e)}")


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
    """
    Señal que se dispara cuando un usuario cierra sesión.
    Registra automáticamente la salida en RegistroAcceso
    """
    try:
        ip = obtener_ip_cliente(request)
        user_agent = obtener_user_agent(request)
        
        # Encontrar el último login para calcular la duración de la sesión
        ultimo_login = RegistroAcceso.objects.filter(
            user=user,
            tipo_evento='LOGIN'
        ).order_by('-fecha_hora').first()
        
        duracion = None
        duracion_formateada = None
        
        if ultimo_login:
            duracion = timezone.now() - ultimo_login.fecha_hora
            
            # Convertir a horas y minutos
            total_segundos = int(duracion.total_seconds())
            horas = total_segundos // 3600
            minutos = (total_segundos % 3600) // 60
            
            if horas > 0:
                duracion_formateada = f"{horas}h {minutos}m"
            else:
                duracion_formateada = f"{minutos}m"
        
        registro = RegistroAcceso.objects.create(
            user=user,
            tipo_evento='LOGOUT',
            ip_address=ip,
            user_agent=user_agent,
            duracion_sesion=duracion,
            notas=f'Logout desde {ip} - Duración: {duracion_formateada if duracion_formateada else "Sin registro"}'
        )
        logger.info(f"Logout registrado para usuario: {user.username} desde IP: {ip} - Duración: {duracion_formateada}")
        
    except Exception as e:
        logger.error(f"Error registrando logout para {user.username}: {str(e)}")


# =========================================================================
# SINCRONIZACIÓN ENTRE APERTURA DE CAJA (ventas.Caja) Y ESTADO DE CAJA
# =========================================================================
@receiver(post_save, sender='ventas.Caja')
def sincronizar_apertura_caja(sender, instance, created, **kwargs):
    """
    Señal que sincroniza cuando se abre una caja en ventas.Caja
    con el registro en usuarios.EstadoCaja
    """
    try:
        if created and instance.abierta:  # Si es una nueva caja abierta
            from datetime import date
            
            hoy = date.today()
            
            # Crear o actualizar el registro en EstadoCaja
            estado_caja, created_estado = EstadoCaja.objects.get_or_create(
                user=instance.usuario_apertura,
                fecha=hoy,
                defaults={
                    'estado': 'ABIERTA',
                    'monto_inicial': instance.monto_inicial,
                    'timestamp_apertura': instance.fecha_apertura,
                }
            )
            
            # Si ya existía, actualizar sus datos
            if not created_estado:
                estado_caja.estado = 'ABIERTA'
                estado_caja.monto_inicial = instance.monto_inicial
                estado_caja.timestamp_apertura = instance.fecha_apertura
                estado_caja.save()
            
            logger.info(f"Caja sincronizada para usuario: {instance.usuario_apertura.username}")
    
    except Exception as e:
        logger.error(f"Error sincronizando caja: {str(e)}")


@receiver(post_save, sender='ventas.Caja')
def sincronizar_cierre_caja(sender, instance, **kwargs):
    """
    Señal que sincroniza cuando se cierra una caja en ventas.Caja
    con el registro en usuarios.EstadoCaja
    """
    try:
        if not instance.abierta and instance.fecha_cierre:  # Si la caja está cerrada
            from datetime import date
            
            hoy = date.today()
            
            # Buscar y actualizar el registro en EstadoCaja
            estado_caja = EstadoCaja.objects.filter(
                user=instance.usuario_apertura,
                fecha=hoy,
                estado='ABIERTA'
            ).first()
            
            if estado_caja:
                estado_caja.estado = 'CERRADA'
                estado_caja.monto_cierre = instance.monto_cierre_real
                estado_caja.timestamp_cierre = instance.fecha_cierre
                estado_caja.save()
                logger.info(f"Caja cerrada sincronizada para usuario: {instance.usuario_apertura.username}")
    
    except Exception as e:
        logger.error(f"Error sincronizando cierre de caja: {str(e)}")
