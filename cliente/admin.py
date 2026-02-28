#cliente/admin.py
from django.contrib import admin
from .models import Cliente

class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id_cliente', 'nombre', 'email', 'telefono', 'credito_activo', 'saldo_credito', 'fecha_registro')
    search_fields = ('nombre', 'email', 'telefono', 'id_cliente', 'ruc_cedula')
    list_filter = ('fecha_registro', 'credito_activo')
    list_editable = ('telefono',)
    readonly_fields = ('fecha_registro', 'saldo_credito')
    list_per_page = 20
    fieldsets = (
        ('Información Personal', {
            'fields': ('id_cliente', 'nombre', 'apellido', 'ruc_cedula')
        }),
        ('Información de Contacto', {
            'fields': ('email', 'telefono', 'direccion'),
        }),
        ('Información de Crédito', {
            'fields': ('credito_activo', 'limite_credito', 'saldo_credito', 'dias_plazo'),
            'description': 'Gestiona los créditos disponibles para este cliente',
        }),
        ('Detalles de Registro', {
            'fields': ('fecha_registro',),
        }),
    )

admin.site.register(Cliente, ClienteAdmin)