# finanzas/models.py
from django.db import models
from django.utils import timezone
# Importamos la cabecera de la factura de la aplicación 'inventario'
from inventario.models import Compra 
from ventas.models import Venta
from decimal import Decimal

# --- Cuentas por Pagar (Crédito a Proveedores) ---
class CuentaPorPagar(models.Model):
    """Registro general de deuda con proveedores"""
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='cuentas_por_pagar', null=True, blank=True)
    compra = models.OneToOneField(
        Compra, 
        on_delete=models.CASCADE, 
        related_name='cuenta_por_pagar',
        verbose_name="Factura de Compra"
    )
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total")
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto Pagado")
    saldo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Pendiente")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    estado = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente'),
            ('PARCIAL', 'Pago Parcial'),
            ('PAGADA', 'Pagada'),
        ],
        default='PENDIENTE',
        verbose_name="Estado"
    )
    
    def __str__(self):
        return f"Deuda Compra #{self.compra.id_compra} - ${self.saldo}"
    
    def actualizar_saldo(self):
        """Actualiza automáticamente el saldo basado en los pagos realizados"""
        total_pagos = self.amortizaciones_proveedor.aggregate(
            total=models.Sum('monto_abonado')
        )['total'] or Decimal('0.00')
        self.monto_pagado = total_pagos
        self.saldo = self.monto_total - total_pagos
        
        # Actualizar estado
        if self.saldo <= 0:
            self.estado = 'PAGADA'
        elif total_pagos > 0:
            self.estado = 'PARCIAL'
        else:
            self.estado = 'PENDIENTE'
        
        self.save()
    
    class Meta:
        verbose_name = "Cuenta por Pagar"
        verbose_name_plural = "Cuentas por Pagar"
        ordering = ['-fecha_creacion']


class AmortizacionProveedor(models.Model):
    """Tabla de amortización: detalle de cada pago a proveedores"""
    cuenta = models.ForeignKey(
        CuentaPorPagar, 
        on_delete=models.CASCADE, 
        related_name='amortizaciones_proveedor',
        verbose_name="Cuenta por Pagar"
    )
    numero_cuota = models.IntegerField(verbose_name="Número de Cuota")
    monto_abonado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Abonado")
    saldo_anterior = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Anterior")
    saldo_nuevo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Nuevo")
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Pago")
    metodo_pago = models.CharField(
        max_length=20,
        choices=[
            ('efectivo', 'Efectivo'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
            ('cheque', 'Cheque'),
        ],
        default='efectivo',
        verbose_name="Método de Pago"
    )
    referencia = models.CharField(max_length=100, blank=True, verbose_name="Referencia (Comprobante)")
    notas = models.TextField(blank=True, verbose_name="Notas")
    
    def __str__(self):
        return f"Cuota {self.numero_cuota} - Compra #{self.cuenta.compra.id_compra} - ${self.monto_abonado}"
    
    class Meta:
        verbose_name = "Amortización a Proveedor"
        verbose_name_plural = "Amortizaciones a Proveedores"
        ordering = ['numero_cuota']
        unique_together = ('cuenta', 'numero_cuota')


# --- Cuentas por Cobrar (Crédito a Clientes) ---
class CuentaPorCobrar(models.Model):
    """Registro general de deuda de clientes"""
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='cuentas_por_cobrar', null=True, blank=True)
    venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name='cuenta_por_cobrar',
        verbose_name="Venta",
        null=True,
        blank=True
    )
    cliente = models.ForeignKey(
        'cliente.Cliente',
        on_delete=models.CASCADE,
        related_name='cuentas_por_cobrar',
        null=True,
        blank=True,
        verbose_name="Cliente"
    )
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Total")
    monto_cobrado = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto Cobrado")
    saldo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Pendiente")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    estado = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente'),
            ('PARCIAL', 'Pago Parcial'),
            ('PAGADA', 'Pagada'),
        ],
        default='PENDIENTE',
        verbose_name="Estado"
    )
    
    def __str__(self):
        if self.venta:
            cliente_nombre = self.venta.cliente.nombre if self.venta.cliente else "Sin cliente"
            return f"Deuda Venta #{self.venta.id_venta} - Cliente: {cliente_nombre} - ${self.saldo}"
        elif self.cliente:
            return f"Deuda Crédito Directo - Cliente: {self.cliente.nombre} - ${self.saldo}"
        else:
            return f"Deuda Crédito Directo - Sin cliente - ${self.saldo}"
    
    def actualizar_saldo(self):
        """Actualiza automáticamente el saldo basado en los cobros realizados"""
        total_cobros = self.amortizaciones_cliente.aggregate(
            total=models.Sum('monto_cobrado')
        )['total'] or Decimal('0.00')
        self.monto_cobrado = total_cobros
        self.saldo = self.monto_total - total_cobros
        
        # Actualizar estado
        if self.saldo <= 0:
            self.estado = 'PAGADA'
        elif total_cobros > 0:
            self.estado = 'PARCIAL'
        else:
            self.estado = 'PENDIENTE'
        
        self.save()
    
    class Meta:
        verbose_name = "Cuenta por Cobrar"
        verbose_name_plural = "Cuentas por Cobrar"
        ordering = ['-fecha_creacion']


class AmortizacionCliente(models.Model):
    """Tabla de amortización: detalle de cada cobro a clientes"""
    cuenta = models.ForeignKey(
        CuentaPorCobrar, 
        on_delete=models.CASCADE, 
        related_name='amortizaciones_cliente',
        verbose_name="Cuenta por Cobrar"
    )
    numero_cuota = models.IntegerField(verbose_name="Número de Cuota")
    monto_cobrado = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Cobrado")
    saldo_anterior = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Anterior")
    saldo_nuevo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Saldo Nuevo")
    fecha_cobro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Cobro")
    metodo_pago = models.CharField(
        max_length=20,
        choices=[
            ('efectivo', 'Efectivo'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
            ('cheque', 'Cheque'),
        ],
        default='efectivo',
        verbose_name="Método de Pago"
    )
    referencia = models.CharField(max_length=100, blank=True, verbose_name="Referencia (Comprobante)")
    notas = models.TextField(blank=True, verbose_name="Notas")
    
    def __str__(self):
        return f"Cuota {self.numero_cuota} - Venta #{self.cuenta.venta.id_venta} - ${self.monto_cobrado}"
    
    class Meta:
        verbose_name = "Amortización a Cliente"
        verbose_name_plural = "Amortizaciones a Clientes"
        ordering = ['numero_cuota']
        unique_together = ('cuenta', 'numero_cuota')


# --- Solicitudes de Crédito ---
class SolicitudCredito(models.Model):
    """Solicitud de crédito de un cliente para comprar productos"""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Aprobación'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='solicitudes_credito', null=True, blank=True)
    cliente = models.ForeignKey(
        'cliente.Cliente',
        on_delete=models.CASCADE,
        related_name='solicitudes_credito',
        verbose_name="Cliente"
    )
    monto_solicitado = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Monto Solicitado"
    )
    plazo_dias = models.IntegerField(
        default=30,
        verbose_name="Plazo (días)"
    )
    motivo = models.TextField(
        blank=True,
        verbose_name="Motivo o Descripción"
    )
    productos_detalle = models.TextField(
        blank=True,
        verbose_name="Productos a Financiar"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name="Estado"
    )
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Solicitud"
    )
    fecha_respuesta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Respuesta"
    )
    aprobado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_aprobadas',
        verbose_name="Aprobado Por"
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones"
    )
    
    def __str__(self):
        return f"Solicitud #{self.id} - {self.cliente.nombre} - ${self.monto_solicitado}"
    
    class Meta:
        verbose_name = "Solicitud de Crédito"
        verbose_name_plural = "Solicitudes de Crédito"
        ordering = ['-fecha_solicitud']