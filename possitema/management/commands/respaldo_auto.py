"""
Comando Django para respaldos automáticos programados.
Este comando es llamado por cron según la configuración del usuario.

Uso:
    python manage.py respaldo_auto
"""

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Ejecutar respaldo automático programado (usado por cron)'

    def handle(self, *args, **options):
        from possitema.models import ConfiguracionRespaldo, RespaldoDB
        from backup.backup_database import RespaldoDatabase
        
        # Verificar configuración
        config = ConfiguracionRespaldo.objects.first()
        if not config or not config.activo:
            self.stdout.write('Respaldo automático no está configurado o está desactivado.')
            return
        
        self.stdout.write(f'\n[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] Iniciando respaldo automático...')
        self.stdout.write(f'Frecuencia: {config.get_frecuencia_display()}')
        self.stdout.write(f'Tipo: {config.get_tipo_respaldo_display()}')
        
        respaldo_engine = RespaldoDatabase()
        
        try:
            if config.tipo_respaldo == 'bd':
                exito = respaldo_engine.respaldar_base_datos()
                tipo_display = 'Base de Datos'
                tipo_key = 'bd'
            else:
                exito = respaldo_engine.ejecutar_respaldo_completo()
                tipo_display = 'Completo'
                tipo_key = 'completo'
            
            # Buscar archivo creado
            from pathlib import Path
            backup_dir = respaldo_engine.backup_dir
            archivos = sorted(backup_dir.glob(f'bd_{respaldo_engine.timestamp}*'), reverse=True)
            nombre = archivos[0].name if archivos else f'respaldo_{respaldo_engine.timestamp}'
            tamaño = archivos[0].stat().st_size / 1024 / 1024 if archivos else 0
            ruta_completa = str(archivos[0]) if archivos else ''
            checksum = respaldo_engine.ultimo_checksum or ''
            
            # Registrar en BD
            RespaldoDB.objects.create(
                nombre_archivo=nombre,
                tipo=tipo_key,
                estado='exitoso' if exito else 'fallido',
                tamaño_mb=round(tamaño, 2),
                checksum=checksum,
                ruta_archivo=ruta_completa,
                notas=f'Respaldo automático ({config.get_frecuencia_display()}) - {tipo_display}'
            )
            
            # Actualizar estadísticas
            config.ultimo_respaldo = timezone.now()
            if exito:
                config.respaldos_exitosos += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Respaldo automático completado: {nombre}'))
            else:
                config.respaldos_fallidos += 1
                self.stdout.write(self.style.ERROR(f'❌ Respaldo automático falló'))
            config.save()
            
        except Exception as e:
            # Registrar error
            RespaldoDB.objects.create(
                nombre_archivo=f'error_auto_{respaldo_engine.timestamp}',
                tipo=config.tipo_respaldo if config.tipo_respaldo in ['bd', 'media'] else 'completo',
                estado='fallido',
                notas=f'Error en respaldo automático: {str(e)}'
            )
            
            config.respaldos_fallidos += 1
            config.ultimo_respaldo = timezone.now()
            config.save()
            
            # Intentar notificar por email
            respaldo_engine.enviar_notificacion_error('Automático', str(e))
            
            self.stdout.write(self.style.ERROR(f'❌ Error en respaldo automático: {str(e)}'))
