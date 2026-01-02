from django.urls import path
from . import views

app_name = 'gasto'

urlpatterns = [
    # Gastos
    path('', views.lista_gastos, name='lista_gastos'),
    path('crear/', views.crear_gasto, name='crear_gasto'),
    path('<int:pk>/editar/', views.editar_gasto, name='editar_gasto'),
    path('<int:pk>/eliminar/', views.eliminar_gasto, name='eliminar_gasto'),
    path('<int:pk>/detalle/', views.detalle_gasto, name='detalle_gasto'),
    
    # Detalles y Tipos
    path('detalles/administracion/', views.lista_detalles_admin, name='lista_detalles_admin'),
    path('detalles/venta/', views.lista_detalles_venta, name='lista_detalles_venta'),
    path('tipos/', views.lista_tipos_gasto, name='lista_tipos'),
]
