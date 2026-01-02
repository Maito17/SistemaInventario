#usuario/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class PerfilUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=50)
    telefono = models.CharField(max_length=15, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='empleados', verbose_name="Propietario")

    def __str__(self):
        return self.user.username


class PerfilGrupo(models.Model):
    """Extensión de Group para asignar un propietario (owner)"""
    from django.contrib.auth.models import Group
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='perfil')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles_creados')

    def __str__(self):
        return f"{self.group.name} - Owner: {self.owner.username}"


class RegistroAcceso(models.Model):
    """Registro de entrada y salida de usuarios al sistema"""
    TIPO_EVENTO_CHOICES = [
        ('LOGIN', 'Entrada'),
        ('LOGOUT', 'Salida'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_acceso')
    tipo_evento = models.CharField(max_length=10, choices=TIPO_EVENTO_CHOICES)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    duracion_sesion = models.DurationField(null=True, blank=True, help_text="Duración de la sesión en minutos")
    ip_address = models.CharField(max_length=45, blank=True, null=True, help_text="IP del cliente")
    user_agent = models.TextField(blank=True, null=True, help_text="Información del navegador/cliente")
    notas = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Registro de Acceso"
        verbose_name_plural = "Registros de Acceso"
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['user', '-fecha_hora']),
            models.Index(fields=['tipo_evento', '-fecha_hora']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_tipo_evento_display()} - {self.fecha_hora}"
    
    def dias_desde_acceso(self):
        """Retorna cuántos días han pasado desde el acceso"""
        from django.utils import timezone
        delta = timezone.now() - self.fecha_hora
        return delta.days
    
    def duracion_formateada(self):
        """Retorna la duración de la sesión en formato 'Xh Ym'"""
        if not self.duracion_sesion:
            return "-"
        
        total_segundos = int(self.duracion_sesion.total_seconds())
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        
        if horas > 0:
            return f"{horas}h {minutos}m"
        else:
            return f"{minutos}m"


class EstadoCaja(models.Model):
    """Control del estado de apertura y cierre de cajas por usuario"""
    ESTADO_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='estados_caja')
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='CERRADA')
    monto_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_cierre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp_apertura = models.DateTimeField(null=True, blank=True)
    timestamp_cierre = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Estado de Caja"
        verbose_name_plural = "Estados de Caja"
        ordering = ['-fecha', '-timestamp_apertura']
    
    def __str__(self):
        return f"Caja {self.user.username} - {self.fecha} - {self.estado}"
