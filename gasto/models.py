from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class TipoGasto(models.Model):
    """Categorías de gastos: Administración, Venta, etc."""
    CATEGORIAS = [
        ('ADMINISTRACION', 'Gastos de Administración'),
        ('VENTA', 'Gastos de Venta'),
        ('OTRO', 'Otros Gastos'),
    ]
    
    nombre = models.CharField(max_length=100, choices=CATEGORIAS, unique=False) # Removed unique=True to allow duplicates per user (handled in logic or compound index)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    descripcion = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Tipo de Gasto"
        verbose_name_plural = "Tipos de Gasto"
    
    def __str__(self):
        return self.get_nombre_display()


class Gasto(models.Model):
    """Modelo para registrar gastos de administración y venta."""
    
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
        ('PAGADO', 'Pagado'),
    ]
    
    id_gasto = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gastos', null=True, blank=True)
    tipo_gasto = models.ForeignKey(TipoGasto, on_delete=models.PROTECT, verbose_name="Tipo de Gasto")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción del Gasto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    fecha_gasto = models.DateField(default=timezone.now, verbose_name="Fecha del Gasto")
    fecha_pago = models.DateField(blank=True, null=True, verbose_name="Fecha de Pago")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    comprobante = models.FileField(upload_to='gastos/', blank=True, null=True, verbose_name="Comprobante")
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    
    # Auditoria
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ['-fecha_gasto']
        indexes = [
            models.Index(fields=['tipo_gasto', 'fecha_gasto']),
            models.Index(fields=['estado', 'fecha_gasto']),
        ]
    
    def __str__(self):
        return f"{self.descripcion} - ${self.monto}"


class DetalleGastoAdministracion(models.Model):
    """Detalles específicos para gastos de administración."""
    
    CONCEPTOS = [
        ('SALARIO', 'Salarios del Personal'),
        ('ALQUILER', 'Alquiler de Oficina'),
        ('SERVICIOS', 'Servicios Básicos (Luz, Agua, Internet)'),
        ('SEGUROS', 'Seguros'),
        ('IMPUESTOS', 'Impuestos y Licencias'),
        ('MANTENIMIENTO', 'Mantenimiento de Equipos'),
        ('CAPACITACION', 'Capacitación del Personal'),
        ('OTROS', 'Otros'),
    ]
    
    gasto = models.OneToOneField(Gasto, on_delete=models.CASCADE, related_name='detalle_admin')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='detalles_gasto_admin', null=True, blank=True)
    concepto = models.CharField(max_length=50, choices=CONCEPTOS)
    responsable = models.CharField(max_length=100, blank=True, null=True, verbose_name="Responsable")
    
    class Meta:
        verbose_name = "Detalle Gasto Administración"
        verbose_name_plural = "Detalles Gastos Administración"
    
    def __str__(self):
        return f"Admin: {self.get_concepto_display()}"


class DetalleGastoVenta(models.Model):
    """Detalles específicos para gastos de venta."""
    
    CONCEPTOS = [
        ('SALARIO_VENDEDOR', 'Salarios de Vendedores'),
        ('COMISION', 'Comisiones'),
        ('PUBLICIDAD', 'Publicidad y Marketing'),
        ('EMPAQUE', 'Material de Empaque'),
        ('TRANSPORTE', 'Transporte y Distribución'),
        ('PROMOCION', 'Promociones y Descuentos'),
        ('OTROS', 'Otros'),
    ]
    
    gasto = models.OneToOneField(Gasto, on_delete=models.CASCADE, related_name='detalle_venta')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='detalles_gasto_venta', null=True, blank=True)
    concepto = models.CharField(max_length=50, choices=CONCEPTOS)
    beneficiario = models.CharField(max_length=100, blank=True, null=True, verbose_name="Beneficiario")
    canal = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Canal (Redes Sociales, TV, Radio, etc.)"
    )
    
    class Meta:
        verbose_name = "Detalle Gasto Venta"
        verbose_name_plural = "Detalles Gastos Venta"
    
    def __str__(self):
        return f"Venta: {self.get_concepto_display()}"
