# ventas/decorators.py

from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.http import Http404


def permission_required_message(perm_name, redirect_url='ventas:dashboard_view'):
    """
    Decorador personalizado para verificar un permiso de Django. 
    Muestra un mensaje de error si el usuario no tiene el permiso.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                # Si no está logueado, redirige a login
                return redirect('login')

            # Verifica si el usuario tiene el permiso específico
            if request.user.has_perm(perm_name):
                return view_func(request, *args, **kwargs)
            else:
                # Acceso denegado: Muestra el mensaje de error
                # Intentamos extraer el nombre corto del permiso (ej: 'can_anular_venta')
                short_perm_name = perm_name.split('.')[-1]
                messages.error(request, f"Acceso denegado: No tienes permiso ({short_perm_name}) para esta función.")

                # Redirige a una página segura (generalmente el dashboard)
                return redirect(redirect_url)
        return _wrapped_view
    return decorator
