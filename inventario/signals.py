# inventario/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Compra, DetalleCompra

@receiver(post_save, sender=Compra)
def actualizar_stock_en_recepcion(sender, instance, created, **kwargs):
    """
    Signal que se dispara cuando se guarda una Compra.
    Si el estado es 'RECIBIDA', actualiza el stock de los productos.
    Solo incrementa una vez por detalle (usando el campo stock_actualizado).
    """
    # Solo procesar si la compra existe en la BD y está en estado RECIBIDA
    if instance.estado == 'RECIBIDA':
        # Obtener todos los detalles de esta compra que aún no hayan actualizado su stock
        detalles = DetalleCompra.objects.filter(compra=instance, stock_actualizado=False)
        
        for detalle in detalles:
            # Incrementar la cantidad del producto
            producto = detalle.producto
            producto.cantidad += detalle.cantidad_recibida
            producto.save()
            
            # Marcar este detalle como actualizado para evitar doble incremento
            detalle.stock_actualizado = True
            detalle.save()
            
            print(f"✅ Stock actualizado: {producto.nombre} (+{detalle.cantidad_recibida} unidades). Nuevo stock: {producto.cantidad}")
