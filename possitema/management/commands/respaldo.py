"""
Comando Django para gestionar respaldos de la base de datos.

Uso:
    python manage.py respaldo                   # Respaldo completo (BD + media)
    python manage.py respaldo --db-only         # Solo BD
    python manage.py respaldo --media-only      # Solo media
    python manage.py respaldo --list            # Listar respaldos
    python manage.py respaldo --restore ARCHIVO # Restaurar un respaldo
"""

import sys
import os
from django.core.management.base import BaseCommand, CommandError

# Agregar la ruta del proyecto para importar los scripts de backup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


class Command(BaseCommand):
    help = 'Gestionar respaldos de la base de datos y archivos media'

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-only',
            action='store_true',
            help='Respaldar solo la base de datos'
        )
        parser.add_argument(
            '--media-only',
            action='store_true',
            help='Respaldar solo los archivos media'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Listar todos los respaldos disponibles'
        )
        parser.add_argument(
            '--restore',
            type=str,
            default=None,
            help='Restaurar un respaldo específico (nombre del archivo)'
        )
        parser.add_argument(
            '--restore-latest',
            action='store_true',
            help='Restaurar el respaldo más reciente'
        )

    def handle(self, *args, **options):
        
        if options['restore'] or options['restore_latest']:
            self._restaurar(options)
        elif options['list']:
            self._listar()
        else:
            self._respaldar(options)

    def _respaldar(self, options):
        """Ejecutar respaldo."""
        from backup.backup_database import RespaldoDatabase
        
        respaldo = RespaldoDatabase()
        
        if options['db_only']:
            self.stdout.write(self.style.WARNING('Respaldando solo base de datos...'))
            exito = respaldo.respaldar_base_datos()
        elif options['media_only']:
            self.stdout.write(self.style.WARNING('Respaldando solo archivos media...'))
            exito = respaldo.respaldar_media()
        else:
            self.stdout.write(self.style.WARNING('Respaldando base de datos y media...'))
            exito = respaldo.ejecutar_respaldo_completo()
        
        if exito:
            self.stdout.write(self.style.SUCCESS('✅ Respaldo completado exitosamente'))
        else:
            self.stdout.write(self.style.ERROR('❌ Hubo errores durante el respaldo'))

    def _listar(self):
        """Listar respaldos disponibles."""
        from backup.backup_database import RespaldoDatabase
        
        respaldo = RespaldoDatabase()
        respaldo.listar_respaldos()

    def _restaurar(self, options):
        """Restaurar un respaldo."""
        from backup.restore_database import RestaurarDatabase
        
        restaurador = RestaurarDatabase()
        
        if options['restore_latest']:
            archivo = restaurador.obtener_respaldo_mas_reciente()
            if not archivo:
                raise CommandError('No hay respaldos disponibles')
            self.stdout.write(f'Restaurando respaldo más reciente: {archivo}')
        else:
            archivo = options['restore']
        
        restaurador.restaurar_bd(archivo)
