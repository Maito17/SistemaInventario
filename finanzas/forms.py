from django import forms
from cliente.models import Cliente
from inventario.models import Compra

class NuevoCobroForm(forms.Form):
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.all(), label="Cliente")
    monto = forms.DecimalField(max_digits=10, decimal_places=2, label="Monto a cobrar")
    metodo_pago = forms.CharField(max_length=50, label="Método de pago")
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha")
    comentario = forms.CharField(widget=forms.Textarea, required=False, label="Comentario")

class NuevoPagoProveedorForm(forms.Form):
    proveedor = forms.ModelChoiceField(queryset=None, label="Proveedor")
    factura = forms.CharField(max_length=50, label="Número de Factura/Documento")
    monto = forms.DecimalField(max_digits=10, decimal_places=2, label="Monto a pagar")
    metodo_pago = forms.CharField(max_length=50, label="Método de pago")
    referencia = forms.CharField(max_length=100, required=False, label="Referencia (Comprobante)")
    notas = forms.CharField(widget=forms.Textarea, required=False, label="Notas")
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de Inicio")
    fecha_fin = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de Fin")

    def __init__(self, *args, **kwargs):
        from inventario.models import Proveedor
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.all()

class NuevoPagoClienteForm(forms.Form):
    cuenta = forms.ModelChoiceField(queryset=None, label="Cuenta por Cobrar")
    monto = forms.DecimalField(max_digits=10, decimal_places=2, label="Monto a cobrar")
    metodo_pago = forms.CharField(max_length=50, label="Método de pago")
    referencia = forms.CharField(max_length=100, required=False, label="Referencia (Comprobante)")
    notas = forms.CharField(widget=forms.Textarea, required=False, label="Notas")
    fecha_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de Inicio")
    fecha_fin = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de Fin")

    def __init__(self, *args, **kwargs):
        from .models import CuentaPorCobrar
        super().__init__(*args, **kwargs)
        self.fields['cuenta'].queryset = CuentaPorCobrar.objects.all()
