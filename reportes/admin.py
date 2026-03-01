# reportes/admin.py

from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.urls import path
from .views import productos_bajo_stock
from .models import RespaldoArchivo
from django.contrib import admin


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

@admin.register(RespaldoArchivo)
class RespaldoArchivoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "estado", "tamano", "checksum", "fecha_creacion", "creado_por")
    search_fields = ("nombre", "tipo", "estado", "creado_por")
    list_filter = ("tipo", "estado", "fecha_creacion")
