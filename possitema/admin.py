# possitema/admin.py
from django.contrib import admin
from .models import Plan, RegistroPago, Suscripcion
admin.site.register(Plan)
# Admin para Suscripcion
@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_actual', 'fecha_inicio', 'fecha_vencimiento', 'esta_activa', 'dias_vigentes')
    search_fields = ('user__username',)
    list_filter = ('plan_actual', 'esta_activa')
    readonly_fields = ('fecha_inicio', 'fecha_vencimiento', 'dias_vigentes')

    def dias_vigentes(self, obj):
        return obj.dias_vigentes()
    dias_vigentes.short_description = 'Días Vigentes'

# Admin personalizado para RegistroPago
from django.core.mail import send_mail

@admin.register(RegistroPago)
class RegistroPagoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nombre_cliente', 'email_cliente', 'telefono_cliente', 'id_cliente',
        'plan', 'monto_reportado', 'estado', 'fecha_creacion', 'usuario',
    )
    list_filter = ('estado', 'plan', 'fecha_creacion')
    search_fields = ('nombre_cliente', 'email_cliente', 'id_cliente', 'usuario__username')
    readonly_fields = ('fecha_creacion', 'comprobante')
    fieldsets = (
        ('Datos del Cliente', {
            'fields': ('nombre_cliente', 'email_cliente', 'telefono_cliente', 'id_cliente')
        }),
        ('Pago', {
            'fields': ('plan', 'monto_reportado', 'comprobante', 'estado', 'fecha_creacion', 'usuario')
        }),
    )

    def save_model(self, request, obj, form, change):
        # Si el estado cambia a Aprobado, enviar email de notificación
        if change:
            old_obj = RegistroPago.objects.get(pk=obj.pk)
            if old_obj.estado != 'Aprobado' and obj.estado == 'Aprobado':
                send_mail(
                    '¡Tu suscripción ha sido aprobada!',
                    f'Hola {obj.nombre_cliente}, tu pago para el plan {obj.plan} ha sido aprobado. ¡Ya puedes disfrutar de tu suscripción!',
                    'soporte@saascompany.com',
                    [obj.email_cliente],
                    fail_silently=True
                )
        super().save_model(request, obj, form, change)
# possitema/admin.py
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


