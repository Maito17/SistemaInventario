#cliente/urls.py
from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    # API endpoints (deben ir antes de las rutas dinámicas)
    path('api/buscar/', views.buscar_clientes_api, name='buscar_api'),
    
    # Vistas principales
    path('', views.clientes_lista, name='lista'),
    path('exportar-excel/', views.exportar_clientes_excel, name='exportar_excel'),
    path('importar-excel/', views.importar_clientes_excel, name='importar_excel'),
    path('crear/', views.cliente_crear, name='crear'),
    path('<str:pk>/editar/', views.cliente_editar, name='editar'),
    path('<str:pk>/eliminar/', views.cliente_eliminar, name='eliminar'),
    path('<str:pk>/detalle/', views.cliente_detalle, name='detalle'),
    path('<str:pk>/actualizar-ruc/', views.cliente_actualizar_ruc, name='actualizar_ruc'),
]