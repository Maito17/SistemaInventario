# control/models.py
from django.db import models
from django.conf import settings  # Para referenciar el modelo de usuario de Django
from django.utils import timezone
from datetime import date

class RegistroAsistencia(models.Model):
    """Modelo unificado para registrar entrada/salida de empleados"""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Trabajador",
        related_name='registros_asistencia'
    )
    
    # Fecha del registro (auto-generada al crear)
    fecha = models.DateField(auto_now_add=True, verbose_name="Fecha")
    
    # Entrada
    hora_entrada = models.TimeField(null=True, blank=True, verbose_name="Hora Entrada")
    timestamp_entrada = models.DateTimeField(null=True, blank=True, verbose_name="Timestamp Entrada")
    ip_entrada = models.CharField(max_length=50, blank=True, null=True, verbose_name="IP Entrada")
    
    # Salida
    hora_salida = models.TimeField(null=True, blank=True, verbose_name="Hora Salida")
    timestamp_salida = models.DateTimeField(null=True, blank=True, verbose_name="Timestamp Salida")
    ip_salida = models.CharField(max_length=50, blank=True, null=True, verbose_name="IP Salida")
    
    class Meta:
        verbose_name = "Registro de Asistencia"
        verbose_name_plural = "Registros de Asistencia"
        ordering = ['-fecha', '-timestamp_entrada']
        # Un usuario solo puede tener un registro por día
        unique_together = ('usuario', 'fecha')
    
    def __str__(self):
        entrada = self.hora_entrada.strftime('%H:%M:%S') if self.hora_entrada else 'Sin entrada'
        salida = self.hora_salida.strftime('%H:%M:%S') if self.hora_salida else 'Pendiente'
        return f"{self.usuario.username} - {self.fecha} - {entrada} / {salida}"
    
    @classmethod
    def get_or_create_today(cls, usuario):
        """Obtiene o crea el registro de hoy para un usuario"""
        hoy = date.today()
        registro, created = cls.objects.get_or_create(
            usuario=usuario,
            fecha=hoy
        )
        return registro
    
    def tiene_entrada(self):
        return self.hora_entrada is not None
    
    def tiene_salida(self):
        return self.hora_salida is not None
    
    def esta_activo(self):
        """Retorna True si el usuario tiene entrada pero no salida"""
        return self.tiene_entrada() and not self.tiene_salida()