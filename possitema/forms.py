from django import forms
from .models import RegistroPago, Plan

# Formulario para registro de pago de SaaS
class RegistroPagoForm(forms.ModelForm):
    class Meta:
        model = RegistroPago
        fields = ['plan', 'numero_comprobante', 'comprobante', 'monto_reportado', 'nombre_cliente', 'email_cliente', 'telefono_cliente', 'id_cliente']
        widgets = {
            'plan': forms.Select(attrs={'class': 'form-control'}),
            'numero_comprobante': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder': 'Ej: 1234567890', 'required': True}),
            'comprobante': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'monto_reportado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'nombre_cliente': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '100', 'placeholder': 'Tu nombre completo'}),
            'email_cliente': forms.EmailInput(attrs={'class': 'form-control', 'maxlength': '100', 'placeholder': 'tucorreo@email.com'}),
            'telefono_cliente': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '20', 'placeholder': '0999999999'}),
            'id_cliente': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '20', 'placeholder': 'Cédula o RUC'}),
        }
        labels = {
            'plan': 'Selecciona tu plan',
            'numero_comprobante': 'Número de comprobante',
            'comprobante': 'Comprobante de transferencia',
            'monto_reportado': 'Monto transferido ($)',
        }
from inventario.models import Categoria
from ventas.models import Caja
from .models import ConfiguracionEmpresa
from decimal import Decimal



class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
class AperturaCajaForm(forms.ModelForm):
    """
    Formulario para la apertura de una nueva caja.
    Solo pide el monto inicial de la caja.
    """
    # Sobreescribimos el campo para añadir etiquetas y widgets de Bootstrap/Tailwind
    monto_inicial = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        min_value=Decimal('0.00'),
        label='Monto Inicial en Caja ($)',
        widget=forms.NumberInput(attrs={
            'class': 'form-input mt-1 block w-full rounded-md border-gray-300 shadow-sm', 
            'placeholder': 'Ej: 100.00',
            'step': '0.01'
        })
    )

    class Meta:
        model = Caja
        # Solo necesitamos este campo para el formulario de apertura
        fields = ['monto_inicial']

# Formulario para Cierre de Caja
class CierreCajaForm(forms.ModelForm):
    class Meta:
        model = Caja
        fields = ['monto_cierre_real']
        widgets = {
            'monto_cierre_real': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Monto real contado al cierre', 
                'min': '0.00', 
                'step': '0.01'
            }),
        }
        labels = {
            'monto_cierre_real': 'Monto Real Contado',
        }


class ConfiguracionEmpresaForm(forms.ModelForm):
    """
    Formulario para editar la configuración de la empresa.
    Seguro y restringido solo a superusuarios.
    """
    class Meta:
        model = ConfiguracionEmpresa
        fields = [
            'nombre_empresa',
            'ruc',
            'telefono_celular',
            'telefono_convencional',
            'email',
            'direccion',
            'sitio_web',
            'iva_porcentaje',
            'logo',
            'descripcion',
            'gmail_app_password',
        ]
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de tu empresa',
                'required': True,
            }),
            'ruc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RUC/NIT de la empresa',
                'required': True,
            }),
            'telefono_celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0979014551',
            }),
            'telefono_convencional': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '042977557',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contacto@empresa.com',
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección física de la empresa',
            }),
            'sitio_web': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.miempresa.com',
            }),
            'iva_porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción de tu negocio',
            }),
            'gmail_app_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresa tu contraseña de 16 caracteres',
            }),
        }
        labels = {
            'nombre_empresa': 'Nombre de la Empresa',
            'ruc': 'RUC/NIT',
            'telefono_celular': 'Teléfono Celular',
            'telefono_convencional': 'Teléfono Convencional',
            'email': 'Email de Contacto',
            'direccion': 'Dirección',
            'sitio_web': 'Sitio Web',
            'iva_porcentaje': 'IVA (%)',
            'logo': 'Logo de la Empresa',
            'descripcion': 'Descripción',
            'gmail_app_password': 'Contraseña de Aplicación Gmail',
        }
