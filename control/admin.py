# control/admin.py

from django.contrib import admin
from .models import RegistroAsistencia

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    # Lo que se ve en la lista
    list_display = ('usuario', 'fecha', 'hora_entrada', 'hora_salida', 'estado')
    list_filter = ('fecha', 'usuario')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    date_hierarchy = 'fecha'
    
    # Campos de solo lectura (todo es automático)
    readonly_fields = (
        'usuario', 'fecha', 'hora_entrada', 'hora_salida', 
        'timestamp_entrada', 'timestamp_salida', 'ip_entrada', 'ip_salida'
    )
    
    fieldsets = (
        ('Información del Empleado', {
            'fields': ('usuario', 'fecha')
        }),
        ('Entrada', {
            'fields': ('hora_entrada', 'timestamp_entrada', 'ip_entrada')
        }),
        ('Salida', {
            'fields': ('hora_salida', 'timestamp_salida', 'ip_salida')
        }),
    )
    
    def estado(self, obj):
        """Muestra el estado actual (Activo, Completado, Pendiente)"""
        if obj.tiene_entrada() and obj.tiene_salida():
            return '✓ Completado'
        elif obj.tiene_entrada() and not obj.tiene_salida():
            return '● Activo'
        else:
            return '- Pendiente'
    estado.short_description = 'Estado'
    
    # --- CONTROL DE ACCESO ---
    
    # 1. Quitar permiso para añadir o borrar registros manualmente (solo deben ser automáticos)
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
        
    # 2. Controla quién ve el módulo 'CONTROL'
    def has_module_permission(self, request):
        # El módulo solo es visible para el staff (administradores).
        return request.user.is_staff
        
    # 3. Controla quién ve el contenido del modelo 'RegistroAsistencia'
    def has_view_permission(self, request, obj=None):
        # SOLAMENTE el Superusuario puede ver el contenido de los registros.
        return request.user.is_superuser
    