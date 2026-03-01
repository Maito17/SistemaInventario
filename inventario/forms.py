# inventario/forms.py
from django import forms
from .models import Producto, Proveedor, Categoria, Compra, DetalleCompra, MetodoPagoCompra

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        # Incluir todos los campos necesarios
        fields = ['id_producto', 'nombre', 'descripcion', 'precio_costo', 'precio_venta', 'cantidad', 'categoria', 'tarifa_iva', 'estado', 'fecha_caducidad']
        
        # Opcional: Personalizar etiquetas
        labels = {
            'id_producto': 'ID Producto/SKU',
            'nombre': 'Nombre del Producto',
            'descripcion': 'Descripción',
            'precio_costo': 'Precio de Costo',
            'precio_venta': 'Precio de Venta',
            'cantidad': 'Cantidad en Stock',
            'categoria': 'Categoría',
            'tarifa_iva': 'Tarifa IVA',
            'estado': 'Estado del Producto',
            'fecha_caducidad': 'Fecha de Caducidad',
        }
        
        # Opcional: Personalizar widgets (para usar clases de AdminLTE)
        widgets = {
            'id_producto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: PROD-001'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción detallada...'}),
            'precio_costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'tarifa_iva': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'fecha_caducidad': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean_precio_venta(self):
        precio = self.cleaned_data.get('precio_venta')
        if precio is not None and precio < 0:
            raise forms.ValidationError("El precio de venta no puede ser negativo.")
        return precio
    
    def clean_precio_costo(self):
        precio = self.cleaned_data.get('precio_costo')
        if precio is not None and precio < 0:
            raise forms.ValidationError("El precio de costo no puede ser negativo.")
        return precio
    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad is not None and cantidad < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return cantidad

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['id_proveedor', 'nombre', 'contacto', 'telefono', 'email']
        
        widgets = {
            'id_proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'contacto': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CompraForm(forms.ModelForm):
    """Formulario para crear/editar una compra a proveedor"""
    class Meta:
        model = Compra
        fields = ['numero_documento', 'proveedor', 'metodo_pago', 'estado']
        
        labels = {
            'numero_documento': 'Número de Factura/Documento',
            'proveedor': 'Proveedor',
            'metodo_pago': 'Método de Pago',
            'estado': 'Estado de la Compra',
        }
        
        widgets = {
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: FAC-2024-001'
            }),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }


class DetalleCompraForm(forms.ModelForm):
    """Formulario para agregar detalles de compra (productos)"""
    class Meta:
        model = DetalleCompra
        fields = ['producto', 'cantidad_recibida', 'costo_unitario', 'fecha_caducidad', 'metodo_pago']
        
        labels = {
            'producto': 'Producto',
            'cantidad_recibida': 'Cantidad Recibida',
            'costo_unitario': 'Costo Unitario',
            'fecha_caducidad': 'Fecha de Caducidad del Lote',
            'metodo_pago': 'Método de Pago',
        }
        
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control'}),
            'cantidad_recibida': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': '0'
            }),
            'costo_unitario': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'fecha_caducidad': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'metodo_pago': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_cantidad_recibida(self):
        cantidad = self.cleaned_data.get('cantidad_recibida')
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0.")
        return cantidad

    def clean_costo_unitario(self):
        costo = self.cleaned_data.get('costo_unitario')
        if costo is not None and costo < 0:
            raise forms.ValidationError("El costo no puede ser negativo.")
        return costo


class MetodoPagoCompraForm(forms.ModelForm):
    """Formulario para crear métodos de pago de compra"""
    class Meta:
        model = MetodoPagoCompra
        fields = ['nombre', 'descripcion']
        
        labels = {
            'nombre': 'Método de Pago',
            'descripcion': 'Descripción',
        }
        
        widgets = {
            'nombre': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detalles adicionales del método de pago'
            }),
        }

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Seleccionar archivo Excel',
        help_text='Sube un archivo .xlsx para importar productos.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx, .xls'})
    )
