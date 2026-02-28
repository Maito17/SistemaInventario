
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from inventario.models import Producto
from cliente.models import Cliente


class ConfiguracionEmpresa(models.Model):
    razon_social = models.CharField(max_length=200, blank=True, null=True, verbose_name="Razón Social")
    nombre_comercial = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre Comercial")
    direccion_establecimiento_matriz = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección del Establecimiento Matriz")
    direccion_establecimiento_emisor = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección del Establecimiento Emisor")
    codigo_establecimiento_emisor = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código del Establecimiento Emisor")
    codigo_punto_emision = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código del Punto de Emisión")
    contribuyente_especial = models.CharField(max_length=50, blank=True, null=True, verbose_name="Contribuyente Especial (Número de Resolución)")
    obligado_contabilidad = models.BooleanField(default=False, verbose_name="Obligado a Llevar Contabilidad")
    tipo_ambiente = models.CharField(max_length=20, blank=True, null=True, verbose_name="Tipo de Ambiente")
    tipo_emision = models.CharField(max_length=20, blank=True, null=True, verbose_name="Tipo de Emisión")
    servidor_correo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Servidor de Correo")
    puerto_servidor_correo = models.CharField(max_length=10, blank=True, null=True, verbose_name="Puerto del Servidor de Correo")
    username_servidor_correo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Username del Servidor de Correo")
    password_servidor_correo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Password del Servidor de Correo")
    clave_firma_electronica = models.FileField(
        upload_to="firmas_electronicas/",
        blank=True,
        null=True,
        verbose_name="Firma electrónica (Archivo P12/PFX)"
    )
    """
    Modelo para almacenar la configuración de la empresa/negocio
    """
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la Empresa")
    ruc = models.CharField(max_length=20, verbose_name="RUC/NIT", unique=True)
    telefono_celular = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono Celular")
    telefono_convencional = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono Convencional")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    sitio_web = models.URLField(blank=True, null=True, verbose_name="Sitio Web")
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=15.00, verbose_name="IVA (%)")
    logo = models.ImageField(upload_to='empresa/', blank=True, null=True, verbose_name="Logo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    # Configuración de Gmail para envío de emails
    gmail_app_password = models.CharField(max_length=100, blank=True, null=True, verbose_name="Contraseña de Aplicación Gmail", help_text="Contraseña de 16 caracteres generada en tu cuenta de Google")
    gmail_password_cifrado = models.CharField(max_length=500, blank=True, null=True, verbose_name="Gmail Password Cifrado")
    # Contraseña cifrada del certificado P12
    password_p12_cifrado = models.CharField(max_length=500, blank=True, null=True, verbose_name="Contraseña P12 Cifrada")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Usuario")

    class Meta:
        verbose_name = "Configuración de Empresa"
        verbose_name_plural = "Configuración de Empresa"
        unique_together = ('user',)  # Asegurar una configuración por usuario a nivel de BD

    def __str__(self):
        return f"Config: {self.nombre_empresa} ({self.user.username if self.user else 'Global'})"

    def save(self, *args, **kwargs):
        # Asegurar que solo existe una configuración POR USUARIO
        if self.user:
            existing = ConfiguracionEmpresa.objects.filter(user=self.user).first()
            if existing and self.pk != existing.pk:
                self.pk = existing.pk
        super().save(*args, **kwargs)
    
    @staticmethod
    def _obtener_clave_cifrado():
        """Obtiene la clave de cifrado desde Django settings"""
        from cryptography.fernet import Fernet
        from django.conf import settings
        import base64
        import hashlib
        
        # Usar Django SECRET_KEY para derivar una clave de Fernet
        secret_key = settings.SECRET_KEY.encode()
        # Crear una clave de 32 bytes (Fernet requiere 32 bytes base64-encoded)
        hash_key = hashlib.sha256(secret_key).digest()
        fernet_key = base64.urlsafe_b64encode(hash_key)
        return Fernet(fernet_key)
    
    def establecer_password_p12(self, password):
        """Cifra y guarda el password del certificado P12"""
        if password:
            fernet = self._obtener_clave_cifrado()
            password_bytes = password.encode() if isinstance(password, str) else password
            self.password_p12_cifrado = fernet.encrypt(password_bytes).decode()
        else:
            self.password_p12_cifrado = None
    
    def obtener_password_p12(self):
        """Desencripta y retorna el password del certificado P12"""
        if not self.password_p12_cifrado:
            return None
        try:
            fernet = self._obtener_clave_cifrado()
            password_bytes = fernet.decrypt(self.password_p12_cifrado.encode())
            return password_bytes.decode()
        except Exception as e:
            raise ValueError(f"Error desencriptando password P12: {str(e)}")

    def establecer_gmail_password(self, password):
        """Cifra y guarda la contraseña de aplicación de Gmail."""
        if password:
            fernet = self._obtener_clave_cifrado()
            password_bytes = password.encode() if isinstance(password, str) else password
            self.gmail_password_cifrado = fernet.encrypt(password_bytes).decode()
            self.gmail_app_password = ''  # Limpiar texto plano
        else:
            self.gmail_password_cifrado = None

    def obtener_gmail_password(self):
        """Desencripta y retorna la contraseña de aplicación de Gmail."""
        # Si hay cifrado, usarlo; si no, usar el texto plano (migración gradual)
        if self.gmail_password_cifrado:
            try:
                fernet = self._obtener_clave_cifrado()
                password_bytes = fernet.decrypt(self.gmail_password_cifrado.encode())
                return password_bytes.decode()
            except Exception as e:
                raise ValueError(f"Error desencriptando Gmail password: {str(e)}")
        return self.gmail_app_password or None


class RespaldoDB(models.Model):
    """Modelo para registrar y gestionar respaldos de la base de datos."""
    
    TIPO_CHOICES = [
        ('bd', 'Base de Datos'),
        ('media', 'Archivos Media'),
        ('completo', 'Completo (BD + Media)'),
    ]
    
    ESTADO_CHOICES = [
        ('exitoso', 'Exitoso'),
        ('fallido', 'Fallido'),
        ('en_proceso', 'En proceso'),
    ]
    
    nombre_archivo = models.CharField('Archivo', max_length=200, blank=True)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='completo')
    estado = models.CharField('Estado', max_length=20, choices=ESTADO_CHOICES, default='en_proceso')
    tamaño_mb = models.DecimalField('Tamaño (MB)', max_digits=10, decimal_places=2, default=0)
    checksum = models.CharField('Checksum SHA256', max_length=64, blank=True, help_text='Hash SHA256 para verificación de integridad')
    ruta_archivo = models.CharField('Ruta del archivo', max_length=500, blank=True, help_text='Ruta completa al archivo de respaldo')
    fecha_creacion = models.DateTimeField('Fecha de creación', auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Creado por')
    notas = models.TextField('Notas', blank=True)
    
    class Meta:
        verbose_name = 'Respaldo'
        verbose_name_plural = 'Respaldos de Base de Datos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_estado_display()}) - {self.fecha_creacion.strftime('%d/%m/%Y %H:%M')}"


class ConfiguracionRespaldo(models.Model):
    """Configuración de respaldos automáticos programados."""
    
    FRECUENCIA_CHOICES = [
        ('desactivado', '❌ Desactivado'),
        ('cada_12h', '⏱ Cada 12 horas'),
        ('diario', '📅 Diario'),
        ('semanal', '📆 Semanal'),
        ('mensual', '🗓 Mensual'),
    ]
    
    DIA_SEMANA_CHOICES = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    TIPO_RESPALDO_CHOICES = [
        ('completo', 'Completo (BD + Media)'),
        ('bd', 'Solo Base de Datos'),
    ]
    
    frecuencia = models.CharField(
        'Frecuencia de respaldo',
        max_length=20,
        choices=FRECUENCIA_CHOICES,
        default='desactivado'
    )
    hora = models.PositiveIntegerField(
        'Hora del respaldo',
        default=20,
        help_text='Hora del día (0-23) en que se ejecutará el respaldo. Ej: 20 = 8:00 PM'
    )
    minuto = models.PositiveIntegerField(
        'Minuto',
        default=0,
        help_text='Minuto (0-59). Ej: 30 = a la media hora'
    )
    dia_semana = models.PositiveIntegerField(
        'Día de la semana (para semanal)',
        choices=DIA_SEMANA_CHOICES,
        default=0,
        help_text='Solo aplica si la frecuencia es Semanal'
    )
    dia_mes = models.PositiveIntegerField(
        'Día del mes (para mensual)',
        default=1,
        help_text='Solo aplica si la frecuencia es Mensual (1-28)'
    )
    tipo_respaldo = models.CharField(
        'Tipo de respaldo',
        max_length=20,
        choices=TIPO_RESPALDO_CHOICES,
        default='completo'
    )
    ultimo_respaldo = models.DateTimeField(
        'Último respaldo automático',
        null=True,
        blank=True
    )
    respaldos_exitosos = models.PositiveIntegerField('Respaldos exitosos', default=0)
    respaldos_fallidos = models.PositiveIntegerField('Respaldos fallidos', default=0)
    activo = models.BooleanField('Programación activa', default=False)
    
    class Meta:
        verbose_name = 'Configuración de Respaldo Automático'
        verbose_name_plural = 'Configuración de Respaldo Automático'
    
    def __str__(self):
        if self.frecuencia == 'desactivado':
            return 'Respaldo automático: Desactivado'
        hora_str = f'{self.hora:02d}:{self.minuto:02d}'
        return f'Respaldo {self.get_frecuencia_display()} a las {hora_str}'
    
    def get_hora_display(self):
        """Retorna la hora en formato legible (12h)."""
        h = self.hora % 12 or 12
        ampm = 'PM' if self.hora >= 12 else 'AM'
        return f'{h}:{self.minuto:02d} {ampm}'
    
    def get_cron_expression(self):
        """Genera la expresión cron según la configuración."""
        if self.frecuencia == 'desactivado':
            return None
        elif self.frecuencia == 'cada_12h':
            # Cada 12 horas: a la hora configurada y 12 horas después
            hora2 = (self.hora + 12) % 24
            return f'{self.minuto} {self.hora},{hora2} * * *'
        elif self.frecuencia == 'diario':
            return f'{self.minuto} {self.hora} * * *'
        elif self.frecuencia == 'semanal':
            return f'{self.minuto} {self.hora} * * {self.dia_semana}'
        elif self.frecuencia == 'mensual':
            return f'{self.minuto} {self.hora} {self.dia_mes} * *'
        return None
    
    def save(self, *args, **kwargs):
        # Solo una configuración puede existir
        if not self.pk and ConfiguracionRespaldo.objects.exists():
            existing = ConfiguracionRespaldo.objects.first()
            self.pk = existing.pk
        
        self.activo = self.frecuencia != 'desactivado'
        super().save(*args, **kwargs)
