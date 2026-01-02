# usuarios/urls.py
from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),
    path('fix-permissions/', views.fix_my_permissions, name='fix_permissions'),
    
    # Gestión de usuarios
    path('lista/', views.lista_usuarios, name='lista_usuarios'),
    path('crear/', views.crear_usuario, name='crear_usuario'),
    path('editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),
    path('eliminar/<int:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),
    
    # Gestión de roles
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/crear/', views.crear_rol, name='crear_rol'),
    path('roles/editar/<int:group_id>/', views.editar_rol, name='editar_rol'),
    path('roles/eliminar/<int:group_id>/', views.eliminar_rol, name='eliminar_rol'),
    
    # Gestión de Personal
    path('personal/', views.lista_personal, name='lista_personal'),
    path('personal/dashboard/', views.dashboard_personal, name='dashboard_personal'),
    path('personal/entrada/', views.registrar_entrada, name='registrar_entrada'),
    path('personal/salida/', views.registrar_salida, name='registrar_salida'),
    path('personal/caja/abrir/', views.abrir_caja, name='abrir_caja'),
    path('personal/caja/cerrar/', views.cerrar_caja, name='cerrar_caja'),
    
    # Registro de Acceso (Entrada/Salida)
    path('acceso/', views.registro_acceso, name='registro_acceso'),
    path('acceso/usuario/<int:user_id>/', views.registro_acceso_usuario, name='registro_acceso_usuario'),
    path('acceso/estadisticas/', views.estadisticas_acceso, name='estadisticas_acceso'),
]
