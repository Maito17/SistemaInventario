from django.db import models
from inventario.models import Producto
from cliente.models import Cliente
from django.contrib.auth.models import User

class ConfiguracionEmpresa(models.Model):
    """
    Modelo para almacenar la configuración de la empresa/negocio
    """
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la Empresa")
    ruc = models.CharField(max_length=20, verbose_name="RUC/NIT", unique=True)
    telefono_celular = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono Celular")
    telefono_convencional = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono Convencional")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    sitio_web = models.URLField(blank=True, null=True, verbose_name="Sitio Web")
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=12.00, verbose_name="IVA (%)")
    logo = models.ImageField(upload_to='empresa/', blank=True, null=True, verbose_name="Logo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    # Configuración de Gmail para envío de emails
    gmail_app_password = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contraseña de Aplicación Gmail", help_text="Contraseña de 16 caracteres generada en tu cuenta de Google")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuario")
    
    class Meta:
        verbose_name = "Configuración de Empresa"
        verbose_name_plural = "Configuración de Empresa"
        unique_together = ('user',)  # Asegurar una configuración por usuario a nivel de BD
    
    def __str__(self):
        return f"Config: {self.nombre_empresa} ({self.user.username if self.user else 'Global'})"
    
    def save(self, *args, **kwargs):
        # Asegurar que solo existe una configuración POR USUARIO
        if self.user:
            existing = ConfiguracionEmpresa.objects.filter(user=self.user).first()
            if existing and self.pk != existing.pk:
                self.pk = existing.pk
        super().save(*args, **kwargs)

class ControlAcceso(models.Model):
    nombre = models.CharField(max_length=100, default='Control de Acceso')
    class Meta:
        managed = False
        permissions = [
            ("can_view_dashboard_admin", "Puede ver el panel de administración"),
            ("can_view_lista_ventas", "Puede ver la lista de ventas"),
            ("can_access_inventario", "Puede acceder al inventario"),
            ("can_access_pos", "Puede acceder al punto de venta"),
        ]
        verbose_name = "Permiso de Acceso"
        verbose_name_plural = "Permisos de Acceso"
    def __str__(self):
        return self.nombre