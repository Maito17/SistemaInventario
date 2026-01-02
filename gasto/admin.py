from django.contrib import admin
from .models import TipoGasto, Gasto, DetalleGastoAdministracion, DetalleGastoVenta


class DetalleGastoAdministracionInline(admin.TabularInline):
    model = DetalleGastoAdministracion
    extra = 0
    fields = ['concepto', 'responsable']


class DetalleGastoVentaInline(admin.TabularInline):
    model = DetalleGastoVenta
    extra = 0
    fields = ['concepto', 'beneficiario', 'canal']


@admin.register(TipoGasto)
class TipoGastoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre', 'descripcion']


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ['id_gasto', 'descripcion', 'tipo_gasto', 'monto', 'fecha_gasto', 'estado']
    list_filter = ['tipo_gasto', 'estado', 'fecha_gasto']
    search_fields = ['descripcion', 'notas']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    fieldsets = (
        ('Información General', {
            'fields': ('tipo_gasto', 'descripcion', 'monto', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_gasto', 'fecha_pago')
        }),
        ('Documentación', {
            'fields': ('comprobante', 'notas')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    inlines = [DetalleGastoAdministracionInline, DetalleGastoVentaInline]
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Auto-crear detalles según el tipo de gasto
        if not change:  # Solo en creación
            if obj.tipo_gasto.nombre == 'ADMINISTRACION':
                if not hasattr(obj, 'detalle_admin'):
                    DetalleGastoAdministracion.objects.create(
                        gasto=obj,
                        concepto='OTROS'
                    )
            elif obj.tipo_gasto.nombre == 'VENTA':
                if not hasattr(obj, 'detalle_venta'):
                    DetalleGastoVenta.objects.create(
                        gasto=obj,
                        concepto='OTROS'
                    )


@admin.register(DetalleGastoAdministracion)
class DetalleGastoAdministracionAdmin(admin.ModelAdmin):
    list_display = ['gasto', 'concepto', 'responsable']
    list_filter = ['concepto']
    search_fields = ['gasto__descripcion', 'responsable']


@admin.register(DetalleGastoVenta)
class DetalleGastoVentaAdmin(admin.ModelAdmin):
    list_display = ['gasto', 'concepto', 'beneficiario', 'canal']
    list_filter = ['concepto']
    search_fields = ['gasto__descripcion', 'beneficiario', 'canal']
