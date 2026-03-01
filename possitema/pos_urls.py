# possitema/pos_urls.py 
from django.urls import path
from . import views
from ventas import views as ventas_views

app_name = 'possitema'

urlpatterns = [
    # Dashboard principal
    path('dashboard/', views.dashboardPOSView.as_view(), name='dashboard'),
    
    # Ventas — usar las vistas canónicas de ventas/ (evitar duplicados con possitema/views.py)
    path('nueva/', ventas_views.nueva_venta, name='nueva_venta'),
    path('historial/', ventas_views.historial_ventas, name='historial_ventas'),
    path('lista/', views.lista_ventas, name='lista_ventas'), 
    
    # Rutas AJAX — usar las vistas canónicas de ventas/
    path('buscar_nombre/', ventas_views.buscar_por_nombre_ajax, name='buscar_nombre_ajax'),
    path('buscar_codigo/', ventas_views.buscar_por_codigo_ajax, name='buscar_codigo_ajax'),
    path('procesar_venta/', ventas_views.procesar_venta_ajax, name='procesar_venta_ajax'),
    # Enviar comprobante por email
    path('enviar_email/<int:pk>/', ventas_views.enviar_venta_email, name='enviar_email'),
]
