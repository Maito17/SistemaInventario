from django import forms
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
    # Campo especial para la contraseña del P12 (no se guarda en la BD, se encripta)
    password_p12 = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña del certificado P12/PFX'
        }),
        help_text='Se almacenará cifrada. Requerido si cambias el certificado.'
    )
    
    class Meta:
        model = ConfiguracionEmpresa
        fields = [
            'nombre_empresa',
            'ruc',
            'razon_social',
            'nombre_comercial',
            'telefono_celular',
            'telefono_convencional',
            'email',
            'sitio_web',
            'direccion',
            'direccion_establecimiento_matriz',
            'direccion_establecimiento_emisor',
            'codigo_establecimiento_emisor',
            'codigo_punto_emision',
            'contribuyente_especial',
            'obligado_contabilidad',
            'tipo_ambiente',
            'tipo_emision',
            'iva_porcentaje',
            'clave_firma_electronica',
            'password_p12',  # Campo especial (no en modelo, se maneja en save())
            'gmail_app_password',
            'servidor_correo',
            'puerto_servidor_correo',
            'username_servidor_correo',
            'password_servidor_correo',
            'logo',
            'descripcion',
        ]
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa',
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
            # ...otros widgets...
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clave_firma_electronica'].widget.attrs.update({'accept': '.p12,.pfx'})
        # IVA con valor por defecto y no requerido (usa 15% si vacío)
        self.fields['iva_porcentaje'].required = False
        self.fields['iva_porcentaje'].initial = Decimal('15.00')
        # Cargar el password encriptado si existe
        if self.instance and self.instance.password_p12_cifrado:
            self.fields['password_p12'].initial = self.instance.obtener_password_p12()
        
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
            'password_p12': 'Contraseña del Certificado P12',
        }
        for field, label in labels.items():
            if field in self.fields:
                self.fields[field].label = label
    
    def save(self, commit=True):
        """Guarda el formulario y encripta el password del P12"""
        instance = super().save(commit=False)
        
        # Si iva_porcentaje viene vacío, asignar valor por defecto
        if not instance.iva_porcentaje:
            instance.iva_porcentaje = Decimal('15.00')
        
        # Procesar el password_p12
        password_p12 = self.cleaned_data.get('password_p12')
        if password_p12:
            # Encriptar y guardar
            instance.establecer_password_p12(password_p12)
        
        # Procesar gmail_app_password (cifrar si se proporcionó)
        gmail_pwd = self.cleaned_data.get('gmail_app_password')
        if gmail_pwd:
            instance.establecer_gmail_password(gmail_pwd)
        
        if commit:
            instance.save()
        return instance
