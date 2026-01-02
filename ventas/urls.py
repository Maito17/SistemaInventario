# ventas/urls.py
from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    # URL para la interfaz del Punto de Venta (POS)
    path('nueva/', views.nueva_venta, name='nueva_venta'),
    
    # URL para la tabla de registro de ventas
    path('historial/', views.historial_ventas, name='historial_ventas'),
    path('detalles/', views.lista_detalles_venta, name='lista_detalles_venta'),
    
    # Rutas AJAX
    path('buscar_nombre/', views.buscar_por_nombre_ajax, name='buscar_nombre_ajax'),
    path('buscar_codigo/', views.buscar_por_codigo_ajax, name='buscar_codigo_ajax'),
    path('buscar_productos_vivo/', views.buscar_productos_vivo, name='buscar_productos_vivo'),
    path('buscar_clientes_vivo/', views.buscar_clientes_vivo, name='buscar_clientes_vivo'),
    path('procesar_venta/', views.procesar_venta_ajax, name='procesar_venta_ajax'),
    
    # RUTAS DE CAJA
    path('apertura_caja/', views.apertura_caja, name='apertura_caja'),
    path('caja/estado/<int:pk>/', views.estado_caja, name='estado_caja'),
    path('cierre_caja/<int:pk>/', views.cierre_caja, name='cierre_caja'),
    
    # Reportes
    path('reportes/periodo/', views.reportes_ventas_periodo, name='reportes_ventas_periodo'),
    path('reportes/ranking/', views.ranking_productos, name='ranking_productos'),

    #Ruta de impresion de venta 
    path('ticket/<int:pk>/', views.generar_ticket, name='generar_ticket'),
    path('factura_sri/<int:pk>/', views.generar_factura_sri, name='generar_factura_sri'),
    path('comprobante_pdf/<int:pk>/', views.descargar_comprobante_pdf, name='descargar_comprobante_pdf'),
    path('enviar_email/<int:pk>/', views.enviar_venta_email, name='enviar_email'),
]