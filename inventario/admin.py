#inventario/admin.py
from django.contrib import admin
from .models import DetalleCompra, Producto, Proveedor, Categoria, Compra, MetodoPagoCompra, DetalleCompra
from django import forms
from django.db import transaction

class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_venta','precio_costo', 'cantidad', 'categoria')
    search_fields = ('nombre', 'categoria')
    list_filter = ('categoria',)
    list_per_page = 10
    #agrupar los campos de fieldesets
    fieldsets = (
        ('Informacion General', {
            'fields': ('id_producto', 'nombre', 'descripcion' )
        }),
        ('Detalles de Inventario', {
            'fields': ('cantidad', 'precio_costo', 'precio_venta')
        }),
        ('Relaciones', {
            'fields': ('categoria',)
        }),
    )
    class Meta:
        model = Producto
        fields = '__all__'

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return cantidad

class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'contacto', 'telefono', 'email')
    search_fields = ('nombre', 'contacto')
    list_per_page = 10
    fieldsets = (
        ('Informacion del Proveedor', {
            'fields': ('id_proveedor', 'nombre', 'contacto', 'telefono', 'email')
        }),
    )

class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

class DetalleCompraInline(admin.TabularInline):
    # ¡Importante! Usamos TabularInline para un formato de tabla más compacto
    model = DetalleCompra
    extra = 1
    # Solo mostramos los campos relevantes para el producto y el stock
    fields = ('producto','cantidad_recibida', 'costo_unitario', 'fecha_caducidad')
class CompraAdmin(admin.ModelAdmin):
    list_display = ('id_compra', 'proveedor', 'fecha_compra', 'total', 'estado')
    search_fields = ('proveedor__nombre',)
    list_filter = ('fecha_compra','estado')
    
    readonly_fields = ('fecha_compra', 'total')
    fieldsets = (
        ('Información Principal de la Compra', {
            'fields': ('proveedor', 'numero_documento', 'estado', 'total')
        }),
    )
    inlines = [DetalleCompraInline]
    
    def save_model(self, request, obj, form, change):
        # 1. Guardar el estado anterior solo si es una edición (change=True)
        # Esto es clave para evitar dobles sumas de stock.
        if change:
            old_obj = Compra.objects.get(pk=obj.pk)
            old_estado = old_obj.estado
        else:
            old_estado = None

        # 2. Guardar la instancia de Compra
        super().save_model(request, obj, form, change)

        # 3. Solo actualizar stock si el estado ha cambiado a 'RECIBIDA' (o es nuevo y ya está 'RECIBIDA')
        if obj.estado == 'RECIBIDA' and old_estado != 'RECIBIDA':
            self.actualizar_stock(obj)

    @transaction.atomic
    def actualizar_inventario(self, compra):
        """
        Itera sobre los detalles de la compra para aumentar el stock y calcula el total.
        """
        compra_total = 0
        
        for detalle in compra.detalles.all():
            producto = detalle.producto
            
            # 1. Aumentar Stock
            producto.cantidad += detalle.cantidad_recibida
            
            # 2. Opcional: Actualizar el precio de costo del producto al último precio
            # Esto es una buena práctica para que el precio de costo en el Producto
            # siempre refleje el último precio pagado al proveedor.
            producto.precio_costo = detalle.costo_unitario 
            
            producto.save()
            
            # 3. Calcular el Subtotal para sumarlo al total de la Compra
            compra_total += detalle.subtotal

        # 4. Guardar el total calculado en la cabecera de la Compra
        compra.total = compra_total
        # Importante: Usar update_fields para evitar un bucle infinito
        # y guardar solo el total, ya que el estado se actualizó antes.
        compra.save(update_fields=['total'])



admin.site.register(Producto, ProductoAdmin)
admin.site.register(Proveedor, ProveedorAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Compra, CompraAdmin)
admin.site.register(MetodoPagoCompra)
admin.site.register(DetalleCompra)