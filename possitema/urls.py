# possitema/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from .views import dashboardPOSView, configuracion_empresa_view, actualizar_ingresos_ajax

# Nota: El nombre del proyecto principal puede ser diferente.

urlpatterns = [
    # 0. Ruta raíz - redirige al dashboard
    path('', dashboardPOSView.as_view(), name='dashboard'),
    
    # 1. Configuración de Empresa (Segura, sin admin)
    path('configuracion/', configuracion_empresa_view, name='configuracion_empresa'),
    
    # 2. AJAX para actualizar ingresos en tiempo real
    path('ajax/actualizar-ingresos/', actualizar_ingresos_ajax, name='actualizar_ingresos_ajax'),
    
    # 3. Ruta del Administrador
    path('admin/', admin.site.urls),
    
    # 4. RUTA FALTANTE/CRÍTICA DE AUTENTICACIÓN
    # Esta línea mapea /usuarios/ a las rutas de la aplicación 'usuarios'.
    path('usuarios/', include('usuarios.urls', namespace='usuarios')), 
    
    # 5. Módulo POS (usa el archivo que acabas de enviar)
    path('pos/', include('possitema.pos_urls', namespace='pos')), 
    path('ventas/', include(('ventas.urls', 'ventas'), namespace='ventas')),
    
    # 6. Otros Módulos
    path('cliente/', include('cliente.urls', namespace='cliente')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('finanzas/', include('finanzas.urls', namespace='finanzas')),
    path('reportes/', include('reportes.urls', namespace='reportes')),
    path('gasto/', include('gasto.urls', namespace='gasto')),
    path('roles/', RedirectView.as_view(pattern_name='usuarios:lista_roles')),
    ]

# Configuración de archivos estáticos y media (si es aplicable)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)