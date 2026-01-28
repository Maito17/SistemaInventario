from django.shortcuts import redirect
from django.utils import timezone
from possitema.models import Suscripcion

class SuscripcionActivaRequiredMiddleware:
    """
    Middleware que verifica si la suscripción del usuario está activa.
    Si está vencida, redirige a la página de plan vencido.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Rutas públicas a excluir del chequeo de suscripción
        rutas_excluidas = [
            '/plan-vencido/',
            '/planes-precios/',
            '/logout/',
            '/accounts/logout/',
            '/login/',
            '/accounts/login/',
            '/registro/',
            '/usuarios/login/',
            '/usuarios/logout/',
        ]
        if any(request.path.startswith(r) for r in rutas_excluidas):
            return self.get_response(request)
        if request.user.is_authenticated:
            # Permitir acceso total a superusuarios
            if request.user.is_superuser:
                return self.get_response(request)
            try:
                suscripcion = Suscripcion.objects.get(user=request.user)
                if not suscripcion.esta_activa or timezone.now() > suscripcion.fecha_vencimiento:
                    return redirect('plan_vencido')
            except Suscripcion.DoesNotExist:
                return redirect('plan_vencido')
        return self.get_response(request)
