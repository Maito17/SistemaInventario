# finanzas/admin.py
from django.contrib import admin
from .models import (
    CuentaPorPagar, AmortizacionProveedor,
    CuentaPorCobrar, AmortizacionCliente,
    SolicitudCredito
)

# ========== PROVEEDORES (Cuentas por Pagar) ==========

class AmortizacionProveedorInline(admin.TabularInline):
    """Inline para mostrar amortizaciones dentro de CuentaPorPagar"""
    model = AmortizacionProveedor
    fields = ('numero_cuota', 'monto_abonado', 'saldo_anterior', 'saldo_nuevo', 'fecha_pago', 'metodo_pago', 'referencia')
    readonly_fields = ('numero_cuota', 'saldo_anterior', 'saldo_nuevo', 'fecha_pago')
    extra = 0

class CuentaPorPagarAdmin(admin.ModelAdmin):
    list_display = ('compra', 'monto_total', 'monto_pagado', 'saldo', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion', 'fecha_vencimiento')
    search_fields = ('compra__id_compra', 'compra__proveedor__nombre')
    readonly_fields = ('monto_pagado', 'saldo', 'fecha_creacion')
    inlines = [AmortizacionProveedorInline]
    fieldsets = (
        ('Información de la Deuda', {
            'fields': ('compra', 'monto_total', 'monto_pagado', 'saldo', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_vencimiento')
        }),
    )

class AmortizacionProveedorAdmin(admin.ModelAdmin):
    list_display = ('cuenta', 'numero_cuota', 'monto_abonado', 'saldo_nuevo', 'fecha_pago', 'metodo_pago')
    list_filter = ('fecha_pago', 'metodo_pago', 'cuenta__compra__proveedor__nombre')
    search_fields = ('cuenta__compra__id_compra', 'referencia')
    readonly_fields = ('fecha_pago',)
    fieldsets = (
        ('Información de la Cuota', {
            'fields': ('cuenta', 'numero_cuota', 'monto_abonado')
        }),
        ('Saldos', {
            'fields': ('saldo_anterior', 'saldo_nuevo')
        }),
        ('Detalles del Pago', {
            'fields': ('fecha_pago', 'metodo_pago', 'referencia', 'notas')
        }),
    )

# ========== CLIENTES (Cuentas por Cobrar) ==========

class AmortizacionClienteInline(admin.TabularInline):
    """Inline para mostrar amortizaciones dentro de CuentaPorCobrar"""
    model = AmortizacionCliente
    fields = ('numero_cuota', 'monto_cobrado', 'saldo_anterior', 'saldo_nuevo', 'fecha_cobro', 'metodo_pago', 'referencia')
    readonly_fields = ('numero_cuota', 'saldo_anterior', 'saldo_nuevo', 'fecha_cobro')
    extra = 0

class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ('venta', 'monto_total', 'monto_cobrado', 'saldo', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion', 'fecha_vencimiento')
    search_fields = ('venta__id_venta', 'venta__cliente__nombre')
    readonly_fields = ('monto_cobrado', 'saldo', 'fecha_creacion')
    inlines = [AmortizacionClienteInline]
    fieldsets = (
        ('Información de la Deuda', {
            'fields': ('venta', 'monto_total', 'monto_cobrado', 'saldo', 'estado')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_vencimiento')
        }),
    )

class AmortizacionClienteAdmin(admin.ModelAdmin):
    list_display = ('cuenta', 'numero_cuota', 'monto_cobrado', 'saldo_nuevo', 'fecha_cobro', 'metodo_pago')
    list_filter = ('fecha_cobro', 'metodo_pago', 'cuenta__venta__cliente__nombre')
    search_fields = ('cuenta__venta__id_venta', 'referencia')
    readonly_fields = ('fecha_cobro',)
    fieldsets = (
        ('Información de la Cuota', {
            'fields': ('cuenta', 'numero_cuota', 'monto_cobrado')
        }),
        ('Saldos', {
            'fields': ('saldo_anterior', 'saldo_nuevo')
        }),
        ('Detalles del Cobro', {
            'fields': ('fecha_cobro', 'metodo_pago', 'referencia', 'notas')
        }),
    )


# ========== SOLICITUDES DE CRÉDITO ==========

class SolicitudCreditoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'monto_solicitado', 'estado', 'fecha_solicitud', 'aprobado_por')
    list_filter = ('estado', 'fecha_solicitud', 'plazo_dias')
    search_fields = ('cliente__nombre', 'cliente__email')
    readonly_fields = ('fecha_solicitud', 'fecha_respuesta')
    fieldsets = (
        ('Información del Cliente', {
            'fields': ('cliente', 'monto_solicitado', 'plazo_dias')
        }),
        ('Detalle de la Solicitud', {
            'fields': ('productos_detalle', 'motivo')
        }),
        ('Evaluación', {
            'fields': ('estado', 'aprobado_por', 'observaciones')
        }),
        ('Auditoría', {
            'fields': ('fecha_solicitud', 'fecha_respuesta'),
            'classes': ('collapse',)
        }),
    )


# Registrar modelos
admin.site.register(CuentaPorPagar, CuentaPorPagarAdmin)
admin.site.register(AmortizacionProveedor, AmortizacionProveedorAdmin)
admin.site.register(CuentaPorCobrar, CuentaPorCobrarAdmin)
admin.site.register(AmortizacionCliente, AmortizacionClienteAdmin)
admin.site.register(SolicitudCredito, SolicitudCreditoAdmin)
