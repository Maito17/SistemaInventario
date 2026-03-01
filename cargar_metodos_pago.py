from inventario.models import MetodoPagoCompra

# Crea los métodos de pago más comunes si no existen
metodos = [
    ("EFECTIVO", "Efectivo"),
    ("TRANSFERENCIA", "Transferencia Bancaria"),
    ("CHEQUE", "Cheque"),
    ("CREDITO", "Crédito / A Plazo"),
    ("TARJETA", "Tarjeta de Crédito/Débito (Empresa)"),
    ("OTRO", "Otro")
]

for cod, nombre in metodos:
    MetodoPagoCompra.objects.get_or_create(nombre=cod)
print("Métodos de pago creados o ya existentes.")
