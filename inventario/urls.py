# inventario/urls.py
from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [

    
    
    # API para búsqueda de productos en solicitud de crédito
    path('api/productos/buscar/', views.buscar_productos_api, name='buscar_productos_api'),
    
    # URL para la búsqueda AJAX
    path('buscar_producto/', views.buscar_producto_ajax, name='buscar_producto_ajax'),
    
    # Productos (Lista y Creación)
    path('', views.productos_lista, name='lista'), 
    path('crear/', views.producto_crear, name='crear'),
    path('inventario/', views.productos_lista, name='lista_redundante'), 
    
    # Exportar e Importar Excel
    path('exportar-excel/', views.exportar_productos_excel, name='exportar_excel'),
    path('importar-excel/', views.importar_productos_excel, name='importar_excel'),
    
    # Rutas CRUD de Productos (Usan <str:pk> y nombres de vistas definidos en views.py)
    path('producto/<str:pk>/editar/', views.editar_producto, name='editar'),
    path('producto/<str:pk>/eliminar/', views.eliminar_producto, name='eliminar'),
    path('producto/<str:pk>/detalle/', views.detalle_producto, name='detalle'),
    
    # Ruta de QR
    path('producto/<str:pk>/qr/', views.generar_qr_producto, name='producto_qr_imprimir'),
    
    # Proveedores
    path('proveedores/', views.proveedores_lista, name='proveedores_lista'),
    path('proveedores/crear/', views.proveedor_crear, name='proveedor_crear'),
    
    # Categorías
    path('categorias/', views.categorias_lista, name='categorias_lista'),
    path('categorias/crear/', views.categoria_crear, name='categoria_crear'),

    # [ AÑADIR ] RUTA DE EDICIÓN
    path('proveedor/<str:pk>/editar/', views.editar_proveedor, name='editar_proveedor'), 
    
    # [ AÑADIR ] RUTA DE ELIMINACIÓN
    path('proveedor/<str:pk>/eliminar/', views.eliminar_proveedor, name='eliminar_proveedor'),
    # Categorías CRUD
    path('categoria/<str:pk>/editar/', views.editar_categoria, name='editar_categoria'),
    path('categoria/<str:pk>/eliminar/', views.eliminar_categoria, name='eliminar_categoria'),
    path('categoria/<str:pk>/detalle/', views.detalle_categoria, name='detalle_categoria'),
    #path('categoria/check-caducidad/<int:pk>/', views.check_categoria_caducidad, name='check_categoria_caducidad'),

    #notficacio de producto por vencer
    path('productos_por_vencer/', views.get_productos_por_vencer, name='productos_por_vencer'),
    
    # Alertas de caducidad AJAX
    path('alertas_caducidad_ajax/', views.get_alertas_caducidad_ajax, name='alertas_caducidad_ajax'),
    
    # Alertas de compras pendientes AJAX
    path('alertas_compras_ajax/', views.get_alertas_compras_ajax, name='alertas_compras_ajax'),
    
    # Alertas de bajo stock AJAX
    path('alertas_bajo_stock_ajax/', views.get_alertas_bajo_stock_ajax, name='alertas_bajo_stock_ajax'),
    
    # Compras
    path('compras/', views.lista_compras, name='lista_compras'),
    path('compras/crear/', views.crear_compra, name='crear_compra'),
    path('compras/<int:pk>/editar/', views.editar_compra, name='editar_compra'),
    path('compras/<int:pk>/qr/', views.generar_qr_compra, name='generar_qr_compra'),
    path('detalles-compras/', views.lista_detalles_compra, name='lista_detalles_compra'),
]
