#cliente/models.py
from django.db import models
from decimal import Decimal

from django.contrib.auth.models import User

class Cliente(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    id_cliente = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    ruc_cedula = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="RUC/Cédula")
    email = models.EmailField(unique=True, null=True, blank=True)
    telefono = models.CharField(max_length=15, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    # Campos de crédito
    credito_activo = models.BooleanField(default=False, verbose_name="¿Tiene Crédito?")
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Límite de Crédito")
    saldo_credito = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Saldo de Crédito Disponible")
    dias_plazo = models.IntegerField(default=30, verbose_name="Días de Plazo para Pago")

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.id_cliente})"
    
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def puede_comprar_credito(self):
        """Verifica si el cliente puede comprar a crédito"""
        return self.credito_activo and self.saldo_credito > 0
    
    @property
    def credito_disponible_formateado(self):
        """Retorna el crédito disponible formateado"""
        return f"${self.saldo_credito:,.2f}"
