from django.contrib import admin
from .models import ConfiguracionEmpresa


@admin.register(ConfiguracionEmpresa)
class ConfiguracionEmpresaAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre_empresa', 'ruc')
        }),
        ('Contacto', {
            'fields': ('telefono_celular', 'telefono_convencional', 'email', 'sitio_web')
        }),
        ('Dirección e Información Fiscal', {
            'fields': ('direccion', 'iva_porcentaje')
        }),
        ('Branding', {
            'fields': ('logo', 'descripcion')
        }),
    )
    
    list_display = ('nombre_empresa', 'ruc', 'email', 'fecha_actualizacion')
    readonly_fields = ('fecha_actualizacion',)
    
    def has_add_permission(self, request):
        # Solo permite una única configuración
        return not ConfiguracionEmpresa.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Evita que se elimine la configuración
        return False


