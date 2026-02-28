# inventario/models.py
from datetime import date
from django.db import models
from django.contrib.auth.models import User



#modelos y detalles de los productos en inventario
class Categoria(models.Model):
    
    nombre = models.CharField(max_length=50)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    descripcion = models.TextField(default='', blank=True, null=True)
    requiere_caducidad = models.BooleanField(default=False,
                        verbose_name="Requiere Fecha de Caducidad",
                        help_text="Indica si los productos en esta categoría requieren una fecha de caducidad.")
    
    def __str__(self):
        return self.nombre
    
class Producto(models.Model):
    TARIFAS_IVA = [
        ('0', '0%'),
        ('5', '5%'),
        ('15', '15%'),
        ('NO_OBJETO', 'NO OBJETO IMPUESTO'),
        ('EXENTO', 'EXENTO IVA'),
    ]
    
    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
        ('DESCONTINUADO', 'Descontinuado'),
    ]
    
    id_producto = models.CharField(max_length=100, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField(default=0, verbose_name="Stock Actual")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='productos')
    tarifa_iva = models.CharField(max_length=20, choices=TARIFAS_IVA, default='15', verbose_name="Tarifa IVA")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVO', verbose_name="Estado del Producto")

    #campo de producto con fecha de caduicadad
    fecha_caducidad = models.DateField(blank=True, null=True, verbose_name="Fecha de Caducidad", help_text="Fecha de caducidad del producto, si aplica.")
    
    @property
    def estado_caducidad(self):
        """Retorna el estado de caducidad con información detallada."""
        if not self.fecha_caducidad:
            return {
                'estado': 'No Aplica',
                'dias_restantes': None,
                'badge': 'secondary'
            }
        
        dias_restantes = (self.fecha_caducidad - date.today()).days
        
        if dias_restantes < 0:
            return {
                'estado': 'VENCIDO',
                'dias_restantes': abs(dias_restantes),
                'badge': 'danger'
            }
        elif dias_restantes == 0:
            return {
                'estado': 'VENCE HOY',
                'dias_restantes': 0,
                'badge': 'danger'
            }
        elif dias_restantes <= 7:
            return {
                'estado': f'VENCE EN {dias_restantes} DÍAS',
                'dias_restantes': dias_restantes,
                'badge': 'danger'
            }
        elif dias_restantes <= 30:
            return {
                'estado': f'VENCE EN {dias_restantes} DÍAS',
                'dias_restantes': dias_restantes,
                'badge': 'warning'
            }
        else:
            return {
                'estado': f'VIGENTE ({dias_restantes} DÍAS)',
                'dias_restantes': dias_restantes,
                'badge': 'info'
            }
    
    def __str__(self):
        return self.nombre
    
# modelo de proveedor a quien estas comprando los productos
class Proveedor(models.Model):
    id_proveedor = models.CharField(max_length=20, primary_key=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    contacto = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    email = models.EmailField()
    
    def __str__(self):
        return self.nombre
    
# para el ingreso de porductos nuevos al inventario
# inventario/models.py (Revisión del modelo Compra)

class Compra(models.Model):
    id_compra = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    numero_documento = models.CharField(max_length=50, blank=True, null=True, 
                                        verbose_name="Número de Factura/Documento")
    proveedor = models.ForeignKey(Proveedor, on_delete=models.SET_NULL, null=True)
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.ForeignKey(
        'MetodoPagoCompra', 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Método de Pago" 
    )
    fecha_pago_proveedor = models.DateField(
        blank=True, 
        null=True, 
        verbose_name="Fecha de Pago a Proveedor",
        help_text="Fecha en que se debe pagar al proveedor (si es a crédito)"
    )
    fecha_recibida = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name="Fecha de Recepción",
        help_text="Fecha y hora en que se recibió la compra"
    )
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('RECIBIDA', 'Recibida'),
        ('PAGADA', 'Pagada'),
        ('CANCELADA', 'Cancelada'),
    ]
    estado = models.CharField(max_length=10, choices=ESTADOS, default='PENDIENTE')

    def __str__(self):
        # f-string mejorado para mayor claridad
        return f"Compra #{self.id_compra} - {self.proveedor.nombre} - {self.fecha_compra.strftime('%Y-%m-%d')}"

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT) 
    cantidad_recibida = models.IntegerField(verbose_name="Cantidad Recibida")
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, 
                                        verbose_name="Costo Unitario de Compra")
    fecha_caducidad = models.DateField(blank=True, null=True, verbose_name="Fecha de Caducidad del Lote")
    metodo_pago = models.ForeignKey(
        'MetodoPagoCompra', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Método de Pago"
    )
    stock_actualizado = models.BooleanField(
        default=False, 
        verbose_name="Stock Actualizado",
        help_text="Indica si el stock del producto ya fue actualizado cuando la compra pasó a RECIBIDA"
    )
    
    # Propiedad para calcular el subtotal
    @property
    def subtotal(self):
        return self.cantidad_recibida * self.costo_unitario

    def __str__(self):
        return f"Detalle de Compra #{self.compra.id_compra} - Producto: {self.producto.nombre}"
# inventario/models.py (Nuevo modelo DetalleCompra)

class MetodoPagoCompra(models.Model):
    # Opciones comunes de pago a proveedores
    METODOS = [
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('CHEQUE', 'Cheque'),
        ('CREDITO', 'Crédito / A Plazo'), # Si la compra es a crédito con el proveedor
        ('TARJETA', 'Tarjeta de Crédito/Débito (Empresa)'),
        ('OTRO', 'Otro')
    ]
    nombre = models.CharField(
        max_length=50, 
        choices=METODOS, 
        unique=True,
        verbose_name="Método de Pago"
    )
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.get_nombre_display() # Muestra el valor legible
    
    class Meta:
        verbose_name = "Método de Pago de Compra"
        verbose_name_plural = "Métodos de Pago de Compras"
