from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplica un valor por un argumento"""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError):
        return 0

@register.filter
def calculate_iva(total):
    """Calcula el IVA (12%) a partir del total"""
    try:
        # Si el total ya incluye IVA, lo separamos
        # total = subtotal + (subtotal * 0.12)
        # total = subtotal * 1.12
        # subtotal = total / 1.12
        subtotal = Decimal(str(total)) / Decimal('1.12')
        iva = Decimal(str(total)) - subtotal
        return round(iva, 2)
    except (ValueError, TypeError):
        return 0

@register.filter
def calculate_subtotal(total):
    """Calcula el subtotal a partir del total (sin IVA)"""
    try:
        # total = subtotal * 1.12
        # subtotal = total / 1.12
        subtotal = Decimal(str(total)) / Decimal('1.12')
        return round(subtotal, 2)
    except (ValueError, TypeError):
        return 0
