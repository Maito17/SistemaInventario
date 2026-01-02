# ventas/admin.py
from django.contrib import admin
from .models import Venta, DetalleVenta, MetodoPagoVenta, Caja


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    readonly_fields = ('subtotal',)


class MetodoPagoVentaInline(admin.TabularInline):
    model = MetodoPagoVenta
    extra = 1
    fields = ('metodo_pago', 'monto', 'referencia')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id_venta', 'fecha_venta', 'antendido_por', 'cliente', 'total', 'es_credito', 'estado_credito', 'caja')
    search_fields = ('id_venta', 'cliente__nombre', 'antendido_por__username')
    list_filter = ('fecha_venta', 'caja', 'es_credito', 'estado_credito', 'metodo_pago')
    readonly_fields = ('fecha_venta', 'total', 'ganancia_total', 'saldo_credito')
    inlines = [DetalleVentaInline, MetodoPagoVentaInline]
    fieldsets = (
        ('Información General', {
            'fields': ('cliente', 'antendido_por', 'fecha_venta', 'caja', 'metodo_pago', 'notas')
        }),
        ('Montos', {
            'fields': ('total', 'ganancia_total')
        }),
        ('Información de Crédito', {
            'fields': ('es_credito', 'monto_credito', 'monto_pagado', 'saldo_credito', 'estado_credito', 'fecha_vencimiento'),
            'classes': ('collapse',)
        }),
        ('Control de Email', {
            'fields': ('email_enviado',),
            'classes': ('collapse',)
        }),
    )


@admin.register(MetodoPagoVenta)
class MetodoPagoVentaAdmin(admin.ModelAdmin):
    list_display = ('venta', 'metodo_pago', 'monto', 'referencia', 'fecha_registro')
    list_filter = ('metodo_pago', 'fecha_registro')
    search_fields = ('venta__id_venta', 'referencia')
    readonly_fields = ('fecha_registro',)


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'usuario_apertura',
        'abierta', 
        'monto_inicial', 
        'monto_cierre_real', 
        'fecha_apertura', 
        'fecha_cierre',
        'get_diferencia',
    )
    search_fields = ('usuario_apertura__username', 'id')
    list_filter = ('abierta', 'fecha_apertura', 'fecha_cierre')
    readonly_fields = ('fecha_apertura', 'fecha_cierre')

    @admin.display(description='Diferencia')
    def get_diferencia(self, obj):
        dif = obj.calcular_diferencia()
        if dif is not None:
            return f"${dif:.2f}"
        return "-"

