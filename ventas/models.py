#ventas/models.py
from django.db import models
from inventario.models import Producto 
from cliente.models import Cliente
from django.contrib.auth.models import User
from django.db.models import Sum, F
from decimal import Decimal

class Venta(models.Model):
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('credito', 'Crédito'),
        ('mixto', 'Mixto'),
    ]
    
    ESTADO_CREDITO = [
        ('PENDIENTE', 'Pendiente'),
        ('PARCIAL', 'Pago Parcial'),
        ('PAGADA', 'Pagada'),
    ]
    
    id_venta = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ventas_owner', null=True, blank=True, verbose_name="Dueño/Superusuario")
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    antendido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Atendido por")
    fecha_venta = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='efectivo', verbose_name="Método de Pago Principal")
    
    # Campos para crédito
    es_credito = models.BooleanField(default=False, verbose_name="¿Es a Crédito?")
    monto_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto a Crédito")
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto Pagado")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    estado_credito = models.CharField(max_length=20, choices=ESTADO_CREDITO, default='PENDIENTE', verbose_name="Estado del Crédito")
    
    # Referencia a la caja en la que se realizó la venta
    caja = models.ForeignKey('Caja', on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas_realizadas')
    email_enviado = models.BooleanField(default=False, verbose_name="Email Enviado")
    notas = models.TextField(blank=True, verbose_name="Notas de Venta")

    @property
    def usuario(self):
        """Alias para compatibilidad con código que usa 'usuario' en lugar de 'antendido_por'"""
        return self.antendido_por

    @property
    def ganancia_total(self):
        resultado = self.detalles.aggregate(
            ganancia_sum=Sum(
                F('subtotal') - (F('costo_al_vender') * F('cantidad')),
                output_field=models.DecimalField()
        )
        )['ganancia_sum']
        return resultado if resultado is not None else Decimal('0.00')
    
    @property
    def saldo_credito(self):
        """Calcula el saldo pendiente de crédito"""
        if self.es_credito:
            return self.monto_credito - self.monto_pagado
        return Decimal('0.00')
        


    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"Venta #{self.id_venta} - Cliente: {self.cliente}"

class DetalleVenta(models.Model):
    id_detalle_venta = models.AutoField(primary_key=True)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    #Reporte de ganacias por producto vendido
    costo_al_vender = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo unitario registrado")
    #calcular la ganancia para este item especifico
    @property
    def ganancia_detalle(self):
        costo_total = self.cantidad * self.costo_al_vender
        return self.subtotal - costo_total

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        
    def __str__(self):
        return f"Detalle de Venta #{self.venta.id_venta} - Producto: {self.producto.nombre}"


class MetodoPagoVenta(models.Model):
    """Registro de métodos de pago utilizados en una venta (puede ser múltiple)"""
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='metodos_pago_usados')
    metodo_pago = models.CharField(
        max_length=20,
        choices=[
            ('efectivo', 'Efectivo'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
            ('cheque', 'Cheque'),
            ('credito', 'Crédito'),
        ],
        verbose_name="Método de Pago"
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Pagado")
    referencia = models.CharField(max_length=100, blank=True, verbose_name="Referencia (Nro. Tarjeta, Cheque, etc)")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Método de Pago de Venta"
        verbose_name_plural = "Métodos de Pago de Venta"
        ordering = ['-fecha_registro']
    
    def __str__(self):
        return f"Venta #{self.venta.id_venta} - {self.get_metodo_pago_display()}: ${self.monto}"
        
class Caja(models.Model):
    usuario_apertura = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, # Protege al usuario de ser eliminado si tiene cajas
        related_name='caja_aperturas'
    )
    fecha_apertura = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha de Apertura"
    )
    monto_inicial = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Monto Inicial"
    )
    fecha_cierre = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Fecha de Cierre"
    )
    monto_cierre_esperado = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Monto de Cierre Esperado"
    )
    monto_cierre_real = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="Monto Real Contado al Cierre"
    )
    diferencia = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Diferencia (Sobrante/Faltante)"
    )
    
    # Estado de la caja
    abierta = models.BooleanField(
        default=True, 
        verbose_name="Caja Abierta"
    )
    
    @property
    def monto_final(self):
        """Alias para compatibilidad con admin que usa 'monto_final'"""
        return self.monto_cierre_real

    class Meta:
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ['-fecha_apertura']
        
    def __str__(self):
        return f"Caja {self.id} - {self.usuario_apertura.username} ({'ABIERTA' if self.abierta else 'CERRADA'})"

    def calcular_diferencia(self):
        """Calcula la diferencia entre el monto real y el esperado."""
        if self.monto_cierre_real is not None:
            self.diferencia = self.monto_cierre_real - self.monto_cierre_esperado
        else:
            self.diferencia = 0.00
        return self.diferencia

    def calcular_total_ventas(self):
        """Calcula la suma total de las ventas asociadas a esta caja."""
        # Suma los totales de todas las ventas que tienen esta caja como FK
        total = self.ventas_realizadas.aggregate(total_sum=Sum('total'))['total_sum']
        return total if total is not None else Decimal('0.00')

# ControlAcceso se mantiene como un modelo de permisos
class ControlAcceso(models.Model):
    nombre = models.CharField(max_length=100, default='Control de Permiso POS')
    class Meta:
        managed = False
        permissions = [
            ("can_view_dashboard_admin", "Puede ver el Dashboard Administrativo completo (Reportes Críticos)"),
            ("can_view_lista_ventas", "Puede ver el historial y listado de todas las ventas"),
            ("can_access_inventario", "Puede acceder al módulo de inventario"),
            ("can_access_pos", "Puede acceder al módulo de Punto de Venta (POS)"),
        ]
        verbose_name = "Permiso de Acceso"
        verbose_name_plural = "Permisos de Acceso"
        
    def __str__(self):
        return self.nombre
    