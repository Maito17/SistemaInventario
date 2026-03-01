from django.urls import path
from . import views

app_name = 'finanzas'

urlpatterns = [
    # Pagos a Proveedores
    path('pagos-proveedores/', views.lista_cuentas_por_pagar, name='lista_cuentas_por_pagar'),
    path('pagos-proveedores/<int:pk>/', views.detalle_cuenta_por_pagar, name='detalle_cuenta_por_pagar'),
    path('pagos-proveedores/<int:pk>/registrar/', views.registrar_pago_proveedor, name='registrar_pago_proveedor'),
    
    # Cobros a Clientes
    path('cobros-clientes/', views.lista_cuentas_por_cobrar, name='lista_cuentas_por_cobrar'),
    path('cobros-clientes/<int:pk>/', views.detalle_cuenta_por_cobrar, name='detalle_cuenta_por_cobrar'),
    path('cobros-clientes/<int:pk>/registrar/', views.registrar_cobro_cliente, name='registrar_cobro_cliente'),
    path('cobros-clientes/nuevo/', views.nuevo_cobro, name='nuevo_cobro'),
    
    # Solicitudes de Crédito
    path('solicitudes-credito/', views.lista_solicitudes_credito, name='lista_solicitudes_credito'),
    path('solicitudes-credito/crear/', views.crear_solicitud_credito, name='crear_solicitud_credito'),
    path('solicitudes-credito/<int:pk>/', views.detalle_solicitud_credito, name='detalle_solicitud_credito'),
    path('solicitudes-credito/<int:pk>/aprobar/', views.aprobar_solicitud_credito, name='aprobar_solicitud_credito'),
    path('solicitudes-credito/<int:pk>/rechazar/', views.rechazar_solicitud_credito, name='rechazar_solicitud_credito'),
    
    # Amortizaciones a Proveedores
    path('amortizaciones-proveedores/', views.lista_amortizaciones_proveedor, name='lista_amortizaciones_proveedor'),
    path('amortizaciones-proveedores/nuevo/', views.nuevo_pago_proveedor, name='nuevo_pago_proveedor'),
    
    # Amortizaciones a Clientes
    path('amortizaciones-clientes/', views.lista_amortizaciones_cliente, name='lista_amortizaciones_cliente'),
    path('amortizaciones-clientes/nuevo/', views.nuevo_pago_cliente, name='nuevo_pago_cliente'),
]
