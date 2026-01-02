# control/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models import RegistroAsistencia

def get_client_ip(request):
    """Obtiene la IP del cliente desde la request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Se dispara cuando un usuario inicia sesión (LOGIN)"""
    ip = get_client_ip(request)
    ahora = timezone.now()
    
    # Obtener o crear registro de hoy
    registro = RegistroAsistencia.get_or_create_today(user)
    
    # Registrar entrada si no la tiene
    if not registro.hora_entrada:
        registro.hora_entrada = ahora.time()
        registro.timestamp_entrada = ahora
        registro.ip_entrada = ip
        registro.save(update_fields=['hora_entrada', 'timestamp_entrada', 'ip_entrada'])

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Se dispara cuando un usuario cierra sesión (LOGOUT)"""
    ip = get_client_ip(request)
    ahora = timezone.now()
    
    # Obtener registro de hoy
    registro = RegistroAsistencia.get_or_create_today(user)
    
    # Registrar salida si no la tiene
    if not registro.hora_salida:
        registro.hora_salida = ahora.time()
        registro.timestamp_salida = ahora
        registro.ip_salida = ip
        registro.save(update_fields=['hora_salida', 'timestamp_salida', 'ip_salida'])
    