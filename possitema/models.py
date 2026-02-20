
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from inventario.models import Producto
from cliente.models import Cliente


class Plan(models.Model):
    NOMBRES_PLANES = [
        ("Bronce", "Bronce"),
        ("Plata", "Plata"),
        ("Oro", "Oro"),
    ]
    nombre = models.CharField(max_length=20, choices=NOMBRES_PLANES, unique=True)
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    duracion_dias = models.PositiveIntegerField(default=30)
    limite_usuarios = models.PositiveIntegerField(null=True, blank=True, help_text="Número máximo de usuarios permitidos")
    limite_productos = models.PositiveIntegerField(null=True, blank=True, help_text="Número máximo de productos permitidos")

    def __str__(self):
        return f"{self.nombre} (${self.precio})"


class Suscripcion(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="suscripcion")
    plan_actual = models.ForeignKey(Plan, on_delete=models.PROTECT)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_vencimiento = models.DateTimeField()
    esta_activa = models.BooleanField(default=True)


    def dias_vigentes(self):
        if self.fecha_vencimiento and timezone.now() < self.fecha_vencimiento:
            return (self.fecha_vencimiento - timezone.now()).days
        return 0

    def save(self, *args, **kwargs):
        if not self.fecha_vencimiento:
            self.fecha_vencimiento = self.fecha_inicio + timezone.timedelta(days=self.plan_actual.duracion_dias)
        self.esta_activa = timezone.now() <= self.fecha_vencimiento
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Suscripción de {self.user.username} - {self.plan_actual.nombre}"

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

class RegistroPago(models.Model):
    ESTADOS = [
        ("Pendiente", "Pendiente"),
        ("Aprobado", "Aprobado"),
        ("Rechazado", "Rechazado"),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pagos")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="pagos")
    numero_comprobante = models.CharField("Número de comprobante", max_length=50, unique=True, null=True, blank=True)
    # Identificador de referencia bancaria (p.ej. número de operación/transferencia)
    comprobante_id = models.CharField("Referencia bancaria", max_length=100, unique=True, null=True, blank=True)
    comprobante = models.ImageField(upload_to="comprobantes/")
    monto_reportado = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="Pendiente")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    # Datos del cliente
    nombre_cliente = models.CharField(max_length=100)
    email_cliente = models.EmailField(max_length=100)
    telefono_cliente = models.CharField(max_length=20)
    id_cliente = models.CharField("Cédula o RUC", max_length=20)

    def __str__(self):
        return f"Pago de {self.usuario.username} - {self.plan.nombre} - {self.estado}"
