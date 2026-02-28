# reportes/urls.py
from django.urls import path
from . import views

app_name = 'reportes'
urlpatterns = [
    # Centro de reportes
    path('', views.inicio_reportes, name='inicio'),
    # Descarga de respaldos
    path('descargar-respaldo/<str:filename>/', views.descargar_respaldo, name='descargar_respaldo'),
    
    # Reportes de asistencia
    path('asistencia/', views.reporte_asistencia, name='asistencia'),
    
    # Reportes de caja
    path('caja/', views.reporte_caja, name='caja'),
    
    # Reportes de ventas
    path('ventas/', views.reporte_ventas, name='ventas'),
    
    # Reportes de clientes
    path('clientes/', views.reporte_clientes, name='clientes'),
    
    # Reportes de inventario
    path('inventario/', views.reporte_inventario, name='inventario'),
    
    # Reportes financieros
    path('financiero/', views.reporte_financiero, name='financiero'),
    
    # Productos bajo stock (mantener para compatibilidad)
    path('bajo-stock/', views.productos_bajo_stock, name='productos_bajo_stock'),
    
    # Exportaciones PDF
    path('exportar/ventas/pdf/', views.exportar_ventas_pdf, name='exportar_ventas_pdf'),
    path('exportar/inventario/pdf/', views.exportar_inventario_pdf, name='exportar_inventario_pdf'),
    
    # Exportaciones Excel
    path('exportar/ventas/excel/', views.exportar_ventas_excel, name='exportar_ventas_excel'),
    path('exportar/inventario/excel/', views.exportar_inventario_excel, name='exportar_inventario_excel'),
]
