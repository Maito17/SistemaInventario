# possitema/pos_urls.py 
from django.urls import path
from . import views
from ventas import views as ventas_views

app_name = 'possitema'

urlpatterns = [
    # Dashboard principal
    path('dashboard/', views.dashboardPOSView.as_view(), name='dashboard'),
    
    # Ventas
    path('nueva/', views.nueva_venta, name='nueva_venta'),
    path('historial/', ventas_views.historial_ventas, name='historial_ventas'),
    path('lista/', views.lista_ventas, name='lista_ventas'), 
    
    # Rutas AJAX
    path('buscar_nombre/', views.buscar_por_nombre_ajax, name='buscar_nombre_ajax'),
    path('buscar_codigo/', views.buscar_por_codigo_ajax, name='buscar_codigo_ajax'),
    path('procesar_venta/', views.procesar_venta_ajax, name='procesar_venta_ajax'),
]
