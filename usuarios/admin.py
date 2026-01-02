# usuarios/admin.py
from django.contrib import admin
from .models import PerfilUsuario, RegistroAcceso, EstadoCaja


class RegistroAccesoAdmin(admin.ModelAdmin):
    """Configuración del admin para RegistroAcceso"""
    list_display = ('user', 'tipo_evento', 'fecha_hora', 'ip_address', 'duracion_sesion')
    list_filter = ('tipo_evento', 'fecha_hora', 'user')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('fecha_hora', 'ip_address', 'user_agent')
    
    fieldsets = (
        ('Información del Usuario', {
            'fields': ('user', 'tipo_evento')
        }),
        ('Detalles del Evento', {
            'fields': ('fecha_hora', 'ip_address', 'user_agent', 'duracion_sesion')
        }),
        ('Observaciones', {
            'fields': ('notas',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # No permitir crear registros manualmente desde el admin
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Solo superusuarios pueden eliminar
        return request.user.is_superuser


admin.site.register(PerfilUsuario)
admin.site.register(RegistroAcceso, RegistroAccesoAdmin)

