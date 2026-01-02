# reportes/admin.py
from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.urls import path
from .views import productos_bajo_stock

# Puedes crear una clase AdminSite personalizada si lo necesitas
class ReporteAdminSite(AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('productos-bajo-stock/', self.admin_view(productos_bajo_stock), name='productos_bajo_stock_reporte'),
        ]
        return urls + custom_urls

# Crea una instancia de tu sitio de administración
admin_site = ReporteAdminSite(name='reportes_admin')

# Luego, puedes registrar tus modelos si los tuvieras
# admin_site.register(TuModeloDeReporte)