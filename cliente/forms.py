#cliente/forms.py
from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['id_cliente', 'nombre', 'apellido', 'ruc_cedula', 'email', 'telefono', 'direccion']
        widgets = {
            'id_cliente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: CLI-001'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el apellido'
            }),
            'ruc_cedula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1234567890001 o 0123456789 (opcional)',
                'required': False
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com (opcional)',
                'required': False
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+593 999 999 999'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ingrese la dirección completa'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer el email y RUC/Cédula opcionales
        self.fields['email'].required = False
        self.fields['ruc_cedula'].required = False
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Si el email está vacío, permitirlo
        if not email:
            return email
        
        # Si estamos editando, excluir el email del mismo cliente
        instance_id = self.instance.id_cliente if self.instance else None
        
        if Cliente.objects.filter(email=email).exclude(id_cliente=instance_id).exists():
            raise forms.ValidationError("Este email ya está registrado.")
        
        return email


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Seleccionar archivo Excel',
        help_text='Sube un archivo .xlsx para importar clientes.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'})
    )
