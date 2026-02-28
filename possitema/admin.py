from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.http import FileResponse, Http404
from .models import ConfiguracionEmpresa, RespaldoDB, ConfiguracionRespaldo
from .forms import ConfiguracionEmpresaForm


@admin.register(ConfiguracionEmpresa)
class ConfiguracionEmpresaAdmin(admin.ModelAdmin):
    form = ConfiguracionEmpresaForm
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre_empresa', 'nombre_comercial', 'razon_social', 'ruc')
        }),
        ('Contacto', {
            'fields': ('telefono_celular', 'telefono_convencional', 'email', 'sitio_web')
        }),
        ('Dirección e Información Fiscal', {
            'fields': (
                'direccion',
                'direccion_establecimiento_matriz',
                'direccion_establecimiento_emisor',
                'iva_porcentaje'
            )
        }),
        ('Configuración SRI Ecuador', {
            'fields': (
                'codigo_establecimiento_emisor',
                'codigo_punto_emision',
                'tipo_ambiente',
                'tipo_emision',
                'contribuyente_especial',
                'obligado_contabilidad'
            ),
            'description': 'Parámetros requeridos para emisión de comprobantes electrónicos'
        }),
        ('Firma Digital (Certificado P12)', {
            'fields': (
                'clave_firma_electronica',
                'password_p12'
            ),
            'description': 'Archivo P12/PFX y contraseña para firmar comprobantes'
        }),
        ('Configuración de Email', {
            'fields': (
                'servidor_correo',
                'puerto_servidor_correo',
                'username_servidor_correo',
                'password_servidor_correo',
                'gmail_app_password'
            )
        }),
        ('Branding', {
            'fields': ('logo', 'descripcion')
        }),
        ('Sistema', {
            'fields': ('user', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    list_display = ('nombre_empresa', 'ruc', 'tipo_ambiente', 'email', 'fecha_actualizacion')
    readonly_fields = ('fecha_actualizacion',)
    search_fields = ('nombre_empresa', 'ruc', 'email')
    
    def has_add_permission(self, request):
        # Solo permite una única configuración por usuario
        if request.user.is_superuser:
            return True
        return not ConfiguracionEmpresa.objects.filter(user=request.user).exists()
    
    def has_delete_permission(self, request, obj=None):
        # Evita que se elimine la configuración
        return False
    
    def get_queryset(self, request):
        # Superusuarios ven todo, otros usuarios solo su propia configuración
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)


@admin.register(RespaldoDB)
class RespaldoDBAdmin(admin.ModelAdmin):
    list_display = ('nombre_archivo', 'tipo_badge', 'estado_badge', 'tamaño_mb', 'checksum_corto', 'fecha_creacion', 'creado_por', 'descargar_link')
    list_filter = ('tipo', 'estado', 'fecha_creacion')
    readonly_fields = ('nombre_archivo', 'tipo', 'estado', 'tamaño_mb', 'checksum', 'ruta_archivo', 'fecha_creacion', 'creado_por')
    ordering = ('-fecha_creacion',)
    
    def tipo_badge(self, obj):
        colores = {'bd': '#3498db', 'media': '#e67e22', 'completo': '#27ae60'}
        color = colores.get(obj.tipo, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px; font-size:11px;">{}</span>',
            color, obj.get_tipo_display()
        )
    tipo_badge.short_description = 'Tipo'
    
    def estado_badge(self, obj):
        colores = {'exitoso': '#27ae60', 'fallido': '#e74c3c', 'en_proceso': '#f39c12'}
        color = colores.get(obj.estado, '#95a5a6')
        iconos = {'exitoso': '✅', 'fallido': '❌', 'en_proceso': '⏳'}
        icono = iconos.get(obj.estado, '')
        return format_html(
            '<span style="color:{}; font-weight:bold;">{} {}</span>',
            color, icono, obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def checksum_corto(self, obj):
        if obj.checksum:
            return format_html(
                '<span title="{}" style="font-family:monospace; font-size:11px; cursor:help;">{}…</span>',
                obj.checksum, obj.checksum[:12]
            )
        return '-'
    checksum_corto.short_description = 'Checksum'
    
    def descargar_link(self, obj):
        if obj.estado == 'exitoso' and obj.ruta_archivo:
            formato = 'JSON' if '.json' in obj.nombre_archivo else 'SQL'
            color = '#9b59b6' if formato == 'JSON' else '#3498db'
            return format_html(
                '<a href="{}" class="button" style="padding:2px 8px; font-size:11px; background:{}; color:white; border-radius:3px;">'
                '⬇ {} </a>',
                f'descargar-respaldo/{obj.pk}/',
                color,
                formato
            )
        return '-'
    descargar_link.short_description = 'Descargar'
    
    def has_add_permission(self, request):
        # No se agrega manualmente, se usa el botón "Crear Respaldo"
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return False
    
    change_list_template = 'admin/possitema/respaldodb/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('crear-respaldo/', self.admin_site.admin_view(self.crear_respaldo_view), name='crear_respaldo'),
            path('descargar-respaldo/<int:respaldo_id>/', self.admin_site.admin_view(self.descargar_respaldo_view), name='descargar_respaldo'),
            path('restaurar-respaldo/', self.admin_site.admin_view(self.restaurar_respaldo_view), name='restaurar_respaldo'),
        ]
        return custom_urls + urls
    
    def descargar_respaldo_view(self, request, respaldo_id):
        """Vista para descargar un archivo de respaldo."""
        from pathlib import Path
        
        try:
            respaldo = RespaldoDB.objects.get(pk=respaldo_id)
        except RespaldoDB.DoesNotExist:
            raise Http404('Respaldo no encontrado')
        
        if not respaldo.ruta_archivo:
            raise Http404('Archivo de respaldo no disponible')
        
        ruta = Path(respaldo.ruta_archivo)
        if not ruta.exists():
            messages.error(request, f'❌ Archivo no encontrado en disco: {respaldo.nombre_archivo}')
            return redirect('admin:possitema_respaldodb_changelist')
        
        response = FileResponse(
            open(ruta, 'rb'),
            as_attachment=True,
            filename=respaldo.nombre_archivo
        )
        return response
    
    def crear_respaldo_view(self, request):
        """Vista para crear respaldo desde el admin."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        
        from backup.backup_database import RespaldoDatabase
        
        tipo = request.GET.get('tipo', 'completo')
        formato = request.GET.get('formato', 'sql')  # sql o json
        respaldo_engine = RespaldoDatabase()
        
        try:
            if tipo == 'bd' and formato == 'json':
                exito = respaldo_engine.respaldar_base_datos_json()
                tipo_display = 'Base de Datos (JSON - Portable)'
            elif tipo == 'bd':
                exito = respaldo_engine.respaldar_base_datos()
                tipo_display = 'Base de Datos (SQL - PostgreSQL)'
            elif tipo == 'media':
                exito = respaldo_engine.respaldar_media()
                tipo_display = 'Archivos Media'
            else:
                exito = respaldo_engine.ejecutar_respaldo_completo()
                tipo_display = 'Completo'
            
            # Registrar en el modelo
            from pathlib import Path
            backup_dir = respaldo_engine.backup_dir
            
            # Buscar el archivo más reciente
            if formato == 'json' and tipo == 'bd':
                archivos = sorted(backup_dir.glob(f'bd_{respaldo_engine.timestamp}*.json.gz'), reverse=True)
            else:
                archivos = sorted(backup_dir.glob(f'bd_{respaldo_engine.timestamp}*'), reverse=True)
            
            if not archivos and tipo == 'media':
                archivos = sorted(backup_dir.glob(f'media_{respaldo_engine.timestamp}*'), reverse=True)
            
            nombre = archivos[0].name if archivos else f'respaldo_{respaldo_engine.timestamp}'
            tamaño = archivos[0].stat().st_size / 1024 / 1024 if archivos else 0
            ruta_completa = str(archivos[0]) if archivos else ''
            
            # Obtener checksum del engine
            checksum = respaldo_engine.ultimo_checksum or ''
            
            RespaldoDB.objects.create(
                nombre_archivo=nombre,
                tipo=tipo if tipo in ['bd', 'media'] else 'completo',
                estado='exitoso' if exito else 'fallido',
                tamaño_mb=round(tamaño, 2),
                checksum=checksum,
                ruta_archivo=ruta_completa,
                creado_por=request.user,
                notas=f'Respaldo {tipo_display} creado desde Django Admin'
            )
            
            if exito:
                messages.success(request, f'✅ Respaldo {tipo_display} creado exitosamente')
            else:
                messages.warning(request, f'⚠️ Respaldo {tipo_display} completado con advertencias')
                
        except Exception as e:
            RespaldoDB.objects.create(
                nombre_archivo=f'error_{respaldo_engine.timestamp}',
                tipo=tipo if tipo in ['bd', 'media'] else 'completo',
                estado='fallido',
                creado_por=request.user,
                notas=f'Error: {str(e)}'
            )
            messages.error(request, f'❌ Error al crear respaldo: {str(e)}')
        
        return redirect('admin:possitema_respaldodb_changelist')

    def restaurar_respaldo_view(self, request):
        """Vista para subir un archivo de respaldo y restaurar la BD."""
        import os
        import gzip
        import hashlib
        import subprocess
        from pathlib import Path
        from django.template.response import TemplateResponse
        
        if request.method == 'GET':
            # Mostrar formulario de subida
            context = {
                **self.admin_site.each_context(request),
                'title': 'Restaurar Base de Datos',
                'opts': self.model._meta,
            }
            return TemplateResponse(request, 'admin/possitema/respaldodb/restaurar.html', context)
        
        if request.method == 'POST':
            archivo = request.FILES.get('archivo_respaldo')
            confirmar = request.POST.get('confirmar') == 'si'
            
            if not archivo:
                messages.error(request, '❌ Debes seleccionar un archivo de respaldo (.sql.gz o .json.gz)')
                return redirect('admin:restaurar_respaldo')
            
            # Detectar formato
            es_json = archivo.name.endswith('.json.gz')
            es_sql = archivo.name.endswith('.sql.gz')
            
            if not es_json and not es_sql:
                messages.error(request, '❌ Formato no válido. Usa archivos .sql.gz (PostgreSQL) o .json.gz (portable/JSON)')
                return redirect('admin:restaurar_respaldo')
            
            if not confirmar:
                messages.error(request, '❌ Debes confirmar que deseas restaurar marcando la casilla de confirmación.')
                return redirect('admin:restaurar_respaldo')
            
            # Guardar archivo temporalmente en backup/respaldos/
            proyecto_root = Path(__file__).resolve().parent.parent
            backup_dir = proyecto_root / 'backup' / 'respaldos'
            backup_dir.mkdir(parents=True, exist_ok=True)
            ruta_destino = backup_dir / f'uploaded_{archivo.name}'
            
            try:
                # Guardar archivo subido
                with open(ruta_destino, 'wb') as f:
                    for chunk in archivo.chunks():
                        f.write(chunk)
                
                tamaño_mb = ruta_destino.stat().st_size / 1024 / 1024
                
                # Calcular checksum del archivo subido
                sha256 = hashlib.sha256()
                with open(ruta_destino, 'rb') as f:
                    for bloque in iter(lambda: f.read(8192), b''):
                        sha256.update(bloque)
                checksum_subido = sha256.hexdigest()
                
                # Descomprimir
                with gzip.open(ruta_destino, 'rb') as f_in:
                    contenido = f_in.read().decode('utf-8')
                
                if not contenido.strip():
                    messages.error(request, '❌ El archivo de respaldo está vacío.')
                    ruta_destino.unlink(missing_ok=True)
                    return redirect('admin:restaurar_respaldo')
                
                # Crear respaldo de seguridad ANTES de restaurar
                from backup.backup_database import RespaldoDatabase
                respaldo_engine = RespaldoDatabase()
                respaldo_engine.respaldar_base_datos()
                
                formato_display = 'JSON (portable)' if es_json else 'SQL (PostgreSQL)'
                
                if es_json:
                    # Restaurar via Django loaddata
                    import tempfile
                    from django.core.management import call_command
                    
                    # Guardar JSON temporal sin comprimir
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                        tmp.write(contenido)
                        tmp_path = tmp.name
                    
                    try:
                        call_command('loaddata', tmp_path, verbosity=0)
                    finally:
                        os.unlink(tmp_path)
                    
                else:
                    # Restaurar via psql
                    from django.conf import settings as django_settings
                    db_config = django_settings.DATABASES['default']
                    
                    env = os.environ.copy()
                    env['PGPASSWORD'] = str(db_config['PASSWORD'])
                    
                    cmd = [
                        'psql',
                        f'--host={db_config["HOST"]}',
                        f'--port={str(db_config["PORT"])}',
                        f'--username={db_config["USER"]}',
                        '--dbname', db_config['NAME']
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        input=contenido,
                        capture_output=True,
                        text=True,
                        env=env
                    )
                    
                    if result.returncode != 0:
                        RespaldoDB.objects.create(
                            nombre_archivo=archivo.name,
                            tipo='bd',
                            estado='fallido',
                            tamaño_mb=round(tamaño_mb, 2),
                            checksum=checksum_subido,
                            ruta_archivo=str(ruta_destino),
                            creado_por=request.user,
                            notas=f'Restauración FALLIDA ({formato_display}). Error: {result.stderr[:500]}'
                        )
                        messages.error(request, f'❌ Error al restaurar: {result.stderr[:200]}')
                        return redirect('admin:possitema_respaldodb_changelist')
                
                # Registrar restauración exitosa
                RespaldoDB.objects.create(
                    nombre_archivo=f'🔄 RESTAURADO: {archivo.name}',
                    tipo='bd',
                    estado='exitoso',
                    tamaño_mb=round(tamaño_mb, 2),
                    checksum=checksum_subido,
                    ruta_archivo=str(ruta_destino),
                    creado_por=request.user,
                    notas=f'BD restaurada ({formato_display}) desde archivo subido por {request.user.username}'
                )
                
                messages.success(request, f'✅ Base de datos restaurada exitosamente desde "{archivo.name}" ({formato_display}, {tamaño_mb:.2f} MB)')
                messages.info(request, '⚠️ Se recomienda reiniciar el servidor: python manage.py runserver')
                
            except gzip.BadGzipFile:
                messages.error(request, '❌ El archivo no es un .gz válido o está corrupto.')
                ruta_destino.unlink(missing_ok=True)
            except Exception as e:
                messages.error(request, f'❌ Error durante la restauración: {str(e)}')
                ruta_destino.unlink(missing_ok=True)
            
            return redirect('admin:possitema_respaldodb_changelist')


@admin.register(ConfiguracionRespaldo)
class ConfiguracionRespaldoAdmin(admin.ModelAdmin):
    list_display = ('frecuencia_display', 'hora_display', 'tipo_respaldo_display', 'estado_cron', 'ultimo_respaldo', 'estadisticas')
    readonly_fields = ('ultimo_respaldo', 'respaldos_exitosos', 'respaldos_fallidos', 'activo', 'preview_cron')
    
    fieldsets = (
        ('Programación de Respaldos', {
            'fields': ('frecuencia', 'tipo_respaldo'),
            'description': 'Configura la frecuencia y tipo de respaldo automático'
        }),
        ('Horario', {
            'fields': ('hora', 'minuto'),
            'description': 'Selecciona la hora del día para ejecutar el respaldo'
        }),
        ('Opciones adicionales (según frecuencia)', {
            'fields': ('dia_semana', 'dia_mes'),
            'classes': ('collapse',),
            'description': 'Solo aplica si la frecuencia es Semanal o Mensual'
        }),
        ('Expresión Cron', {
            'fields': ('preview_cron',),
            'description': 'Vista previa de la programación cron que se configurará'
        }),
        ('Estadísticas', {
            'fields': ('activo', 'ultimo_respaldo', 'respaldos_exitosos', 'respaldos_fallidos'),
            'classes': ('collapse',),
        }),
    )
    
    def frecuencia_display(self, obj):
        colores = {
            'desactivado': '#e74c3c',
            'cada_12h': '#9b59b6',
            'diario': '#27ae60',
            'semanal': '#3498db',
            'mensual': '#e67e22',
        }
        color = colores.get(obj.frecuencia, '#95a5a6')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; border-radius:4px; font-size:12px;">{}</span>',
            color, obj.get_frecuencia_display()
        )
    frecuencia_display.short_description = 'Frecuencia'
    
    def hora_display(self, obj):
        if obj.frecuencia == 'desactivado':
            return '-'
        extra = ''
        if obj.frecuencia == 'semanal':
            extra = f' ({obj.get_dia_semana_display()})'
        elif obj.frecuencia == 'mensual':
            extra = f' (día {obj.dia_mes})'
        return format_html(
            '<span style="font-weight:bold; font-size:13px;">⏰ {}{}</span>',
            obj.get_hora_display(), extra
        )
    hora_display.short_description = 'Horario'
    
    def tipo_respaldo_display(self, obj):
        colores = {'completo': '#27ae60', 'bd': '#3498db'}
        color = colores.get(obj.tipo_respaldo, '#95a5a6')
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color, obj.get_tipo_respaldo_display()
        )
    tipo_respaldo_display.short_description = 'Tipo'
    
    def estado_cron(self, obj):
        if obj.activo:
            return format_html(
                '<span style="color:#27ae60; font-weight:bold;">✅ Programado</span>'
            )
        return format_html(
            '<span style="color:#e74c3c;">❌ No programado</span>'
        )
    estado_cron.short_description = 'Estado'
    
    def estadisticas(self, obj):
        total = obj.respaldos_exitosos + obj.respaldos_fallidos
        if total == 0:
            return 'Sin respaldos aún'
        return format_html(
            '✅ {} exitosos | ❌ {} fallidos',
            obj.respaldos_exitosos, obj.respaldos_fallidos
        )
    estadisticas.short_description = 'Estadísticas'
    
    def preview_cron(self, obj):
        cron = obj.get_cron_expression()
        if not cron:
            return format_html('<span style="color:#e74c3c;">Respaldo automático desactivado</span>')
        
        desc = {
            'cada_12h': f'Cada 12 horas (a las {obj.get_hora_display()} y 12h después)',
            'diario': f'Todos los días a las {obj.get_hora_display()}',
            'semanal': f'Cada {obj.get_dia_semana_display()} a las {obj.get_hora_display()}',
            'mensual': f'El día {obj.dia_mes} de cada mes a las {obj.get_hora_display()}',
        }.get(obj.frecuencia, '')
        
        return format_html(
            '<div style="background:#1a2332; padding:10px; border-radius:5px; margin:5px 0;">'
            '<code style="color:#2ecc71; font-size:14px;">{}</code><br>'
            '<span style="color:#bdc3c7; font-size:12px; margin-top:5px; display:block;">📅 {}</span>'
            '</div>',
            cron, desc
        )
    preview_cron.short_description = 'Programación Cron'
    
    def has_add_permission(self, request):
        return not ConfiguracionRespaldo.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._configurar_cron(request, obj)
    
    def _configurar_cron(self, request, obj):
        """Instalar o desinstalar el cron job según la configuración."""
        import subprocess
        import os
        
        proyecto_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        marcador = '# RESPALDO_AUTO_SISTEMA_VENTAS'
        
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            crontab_actual = result.stdout if result.returncode == 0 else ''
            
            lineas = [l for l in crontab_actual.splitlines() if marcador not in l]
            
            if obj.frecuencia != 'desactivado':
                cron_expr = obj.get_cron_expression()
                venv_path = os.path.join(proyecto_root, '.venv', 'bin', 'python')
                manage_path = os.path.join(proyecto_root, 'manage.py')
                log_path = os.path.join(proyecto_root, 'backup', 'logs', 'cron_auto.log')
                
                os.makedirs(os.path.join(proyecto_root, 'backup', 'logs'), exist_ok=True)
                
                nueva_linea = f'{cron_expr} cd {proyecto_root} && {venv_path} {manage_path} respaldo_auto >> {log_path} 2>&1 {marcador}'
                lineas.append(nueva_linea)
                
                messages.success(request, f'✅ Respaldo automático programado: {obj.get_frecuencia_display()} a las {obj.get_hora_display()}')
            else:
                messages.info(request, '❌ Respaldo automático desactivado. Se eliminó la programación.')
            
            nuevo_crontab = '\\n'.join(lineas)
            if not nuevo_crontab.endswith('\\n'):
                nuevo_crontab += '\\n'
            
            process = subprocess.run(
                ['crontab', '-'],
                input=nuevo_crontab,
                capture_output=True,
                text=True
            )
            
            if process.returncode != 0:
                messages.warning(request, f'⚠️ No se pudo configurar cron automáticamente: {process.stderr}')
                
        except Exception as e:
            messages.warning(request, f'⚠️ Error configurando cron: {str(e)}. Puedes configurarlo manualmente.')
    
    change_list_template = 'admin/possitema/configuracionrespaldo/change_list.html'
