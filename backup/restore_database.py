#!/usr/bin/env python3
"""
Script para restaurar respaldos de la base de datos PostgreSQL y archivos media.
Ubicación: /backup/restore_database.py

Uso:
    python restore_database.py bd_20260222_143022.sql.gz    # Restaurar BD específica
    python restore_database.py --list                        # Listar respaldos
    python restore_database.py --latest                      # Restaurar el más reciente
    python restore_database.py --media media_20260222.tar.gz # Restaurar archivos media
"""

import os
import sys
import subprocess
import gzip
import hashlib
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

# Agregar el directorio padre al path para importar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')
import django
django.setup()

from django.conf import settings


class RestaurarDatabase:
    """Clase para restaurar respaldos de BD PostgreSQL y archivos media."""
    
    def __init__(self):
        self.proyecto_root = Path(__file__).resolve().parent.parent
        self.backup_dir = self.proyecto_root / 'backup' / 'respaldos'
        
        # Obtener configuración de BD desde settings
        db_config = settings.DATABASES['default']
        self.db_name = db_config['NAME']
        self.db_user = db_config['USER']
        self.db_password = db_config['PASSWORD']
        self.db_host = db_config['HOST']
        self.db_port = db_config['PORT']
        
        # Carpeta media
        self.media_root = Path(settings.MEDIA_ROOT) if hasattr(settings, 'MEDIA_ROOT') else self.proyecto_root / 'media'
    
    def validar_psql(self):
        """Verificar que psql está disponible."""
        try:
            subprocess.run(['which', 'psql'], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            print("❌ ERROR: psql no instalado. Instala: sudo apt-get install postgresql-client")
            return False
    
    def calcular_checksum(self, ruta_archivo):
        """Calcular SHA256 de un archivo."""
        sha256 = hashlib.sha256()
        with open(ruta_archivo, 'rb') as f:
            for bloque in iter(lambda: f.read(8192), b''):
                sha256.update(bloque)
        return sha256.hexdigest()
    
    def verificar_checksum(self, archivo_respaldo):
        """Verificar integridad del respaldo comparando checksum con el modelo."""
        try:
            from possitema.models import RespaldoDB
            ruta_respaldo = self.backup_dir / archivo_respaldo
            
            registro = RespaldoDB.objects.filter(nombre_archivo=archivo_respaldo).first()
            if not registro or not registro.checksum:
                print("⚠️  No se encontró checksum registrado. Saltando verificación.")
                return True
            
            checksum_actual = self.calcular_checksum(ruta_respaldo)
            if checksum_actual != registro.checksum:
                print(f"❌ ERROR: Checksum no coincide!")
                print(f"   Esperado:  {registro.checksum}")
                print(f"   Calculado: {checksum_actual}")
                print(f"   El archivo puede estar corrupto.")
                return False
            
            print(f"✅ Checksum verificado correctamente: {checksum_actual[:16]}...")
            return True
        except Exception as e:
            print(f"⚠️  Error verificando checksum: {e}. Continuando...")
            return True
    
    def restaurar_bd(self, archivo_respaldo):
        """Restaurar BD PostgreSQL desde archivo respaldo."""
        
        ruta_respaldo = self.backup_dir / archivo_respaldo
        
        if not ruta_respaldo.exists():
            print(f"❌ ERROR: Archivo no encontrado: {ruta_respaldo}")
            return False
        
        if not self.validar_psql():
            return False
        
        # Verificar integridad
        if not self.verificar_checksum(archivo_respaldo):
            respuesta = input("¿Continuar de todos modos? (s/N): ")
            if respuesta.lower() != 's':
                print("❌ Restauración cancelada por checksum inválido.")
                return False
        
        # Confirmar antes de restaurar
        print("\n" + "="*70)
        print("⚠️  ADVERTENCIA: ESTO SOBRESCRIBIRÁ LA BASE DE DATOS ACTUAL")
        print("="*70)
        print(f"Respaldo: {ruta_respaldo.name}")
        print(f"BD: {self.db_name}")
        print(f"Host: {self.db_host}:{self.db_port}")
        print("\n⚠️  Esta acción NO se puede deshacer fácilmente")
        
        respuesta = input("\n¿Estás seguro? Escribe 'SÍ RESTAURAR' para confirmar: ")
        if respuesta != 'SÍ RESTAURAR':
            print("❌ Operación cancelada")
            return False
        
        try:
            print("\n⏳ Restaurando BD PostgreSQL...")
            
            # Descomprimir SQL
            with gzip.open(ruta_respaldo, 'rb') as f_in:
                sql_content = f_in.read().decode('utf-8')
            
            # Configurar password via variable de entorno (forma segura)
            env = os.environ.copy()
            env['PGPASSWORD'] = str(self.db_password)
            
            # Restaurar via psql
            cmd = [
                'psql',
                f'--host={self.db_host}',
                f'--port={str(self.db_port)}',
                f'--username={self.db_user}',
                '--dbname', self.db_name
            ]
            
            # Ejecutar comando
            result = subprocess.run(
                cmd,
                input=sql_content,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode != 0:
                print(f"❌ Error en psql: {result.stderr}")
                return False
            
            print(f"✅ BD restaurada exitosamente desde {ruta_respaldo.name}")
            print("\n⚠️  Recuerda reiniciar Django:")
            print("   python manage.py runserver")
            return True
            
        except Exception as e:
            print(f"❌ Error restaurando BD: {str(e)}")
            return False
    
    def listar_respaldos(self):
        """Listar todos los respaldos disponibles."""
        archivos = sorted(self.backup_dir.glob('bd_*.sql.gz'), reverse=True)
        
        if not archivos:
            print("No hay respaldos disponibles")
            return []
        
        print("\n📋 RESPALDOS DISPONIBLES:")
        print("-" * 80)
        print(f"{'#':<3}{'Archivo':<40}{'Tamaño':<12}{'Fecha':<20}")
        print("-" * 80)
        
        for i, archivo in enumerate(archivos, 1):
            tamaño = archivo.stat().st_size / 1024 / 1024  # MB
            fecha = datetime.fromtimestamp(archivo.stat().st_mtime)
            fecha_str = fecha.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{i:<3}{archivo.name:<40}{tamaño:>6.2f} MB    {fecha_str:<20}")
        
        print("-" * 80)
        return archivos
    
    def restaurar_media(self, archivo_media):
        """Restaurar archivos media desde respaldo tar.gz."""
        ruta_respaldo = self.backup_dir / archivo_media
        
        if not ruta_respaldo.exists():
            print(f"❌ ERROR: Archivo no encontrado: {ruta_respaldo}")
            return False
        
        if not tarfile.is_tarfile(str(ruta_respaldo)):
            print(f"❌ ERROR: El archivo no es un tar.gz válido: {archivo_media}")
            return False
        
        # Verificar integridad
        if not self.verificar_checksum(archivo_media):
            respuesta = input("¿Continuar de todos modos? (s/N): ")
            if respuesta.lower() != 's':
                print("❌ Restauración cancelada por checksum inválido.")
                return False
        
        # Confirmar
        print("\n" + "="*70)
        print("⚠️  ADVERTENCIA: ESTO SOBRESCRIBIRÁ LOS ARCHIVOS MEDIA ACTUALES")
        print("="*70)
        print(f"Respaldo: {ruta_respaldo.name}")
        print(f"Destino: {self.media_root}")
        
        respuesta = input("\n¿Estás seguro? Escribe 'SÍ RESTAURAR' para confirmar: ")
        if respuesta != 'SÍ RESTAURAR':
            print("❌ Operación cancelada")
            return False
        
        try:
            print("\n⏳ Restaurando archivos media...")
            
            # Crear backup del media actual antes de sobrescribir
            if self.media_root.exists():
                media_backup = self.media_root.parent / f'media_pre_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                shutil.copytree(self.media_root, media_backup)
                print(f"📁 Media actual respaldado en: {media_backup.name}")
            
            # Extraer tar.gz
            with tarfile.open(ruta_respaldo, 'r:gz') as tar:
                tar.extractall(path=self.media_root.parent)
            
            print(f"✅ Archivos media restaurados exitosamente desde {archivo_media}")
            return True
            
        except Exception as e:
            print(f"❌ Error restaurando media: {str(e)}")
            return False
    
    def obtener_respaldo_mas_reciente(self):
        """Retornar el nombre del respaldo más reciente."""
        archivos = sorted(self.backup_dir.glob('bd_*.sql.gz'), reverse=True)
        if archivos:
            return archivos[0].name
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Restaurar respaldo de BD PostgreSQL y archivos media')
    parser.add_argument('archivo', nargs='?', help='Nombre del archivo respaldo (ej: bd_20260222_143022.sql.gz)')
    parser.add_argument('--list', action='store_true', help='Listar respaldos disponibles')
    parser.add_argument('--latest', action='store_true', help='Restaurar respaldo más reciente')
    parser.add_argument('--media', metavar='ARCHIVO', help='Restaurar archivos media (ej: media_20260222_143022.tar.gz)')
    
    args = parser.parse_args()
    
    restaurador = RestaurarDatabase()
    
    if args.list:
        restaurador.listar_respaldos()
    elif args.media:
        restaurador.restaurar_media(args.media)
    elif args.latest:
        archivo = restaurador.obtener_respaldo_mas_reciente()
        if archivo:
            restaurador.restaurar_bd(archivo)
        else:
            print("❌ No hay respaldos disponibles")
    elif args.archivo:
        restaurador.restaurar_bd(args.archivo)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
