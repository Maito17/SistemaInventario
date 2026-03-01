#!/usr/bin/env python3
"""
Script para crear respaldos de la base de datos PostgreSQL y archivos media.
Ubicación: /backup/backup_database.py

Uso:
    python backup_database.py                    # Respaldo completo
    python backup_database.py --db-only          # Solo base de datos
    python backup_database.py --media-only       # Solo archivos media
"""

import os
import sys
import subprocess
import gzip
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
import yaml

# Agregar el directorio padre al path para importar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'possitema.settings')
import django
django.setup()

from django.conf import settings


class RespaldoDatabase:
    """Clase para gestionar respaldos de BD PostgreSQL y archivos media."""
    
    def __init__(self):
        # Leer configuración YAML
        config_path = Path(__file__).resolve().parent.parent / 'backup_config.yaml'
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {}
        # Usar valores de YAML si existen, si no usar los de settings
        self.proyecto_root = Path(__file__).resolve().parent.parent
        self.backup_dir = Path(self.config.get('backup', {}).get('local_path', self.proyecto_root / 'backup' / 'respaldos'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        db_cfg = self.config.get('backup', {}).get('db', {})
        self.db_name = db_cfg.get('name', settings.DATABASES['default']['NAME'])
        self.db_user = db_cfg.get('user', settings.DATABASES['default']['USER'])
        self.db_password = db_cfg.get('password', settings.DATABASES['default']['PASSWORD'])
        self.db_host = db_cfg.get('host', settings.DATABASES['default']['HOST'])
        self.db_port = db_cfg.get('port', settings.DATABASES['default']['PORT'])
        self.media_root = Path(self.config.get('backup', {}).get('media_path', settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') else self.proyecto_root / 'media'))
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Almacena info del último respaldo para registro
        self.ultimo_checksum = None
        self.ultimo_archivo = None
        self.ultimo_tamaño = 0
    
    def calcular_checksum(self, ruta_archivo):
        """Calcular SHA256 de un archivo para verificación de integridad."""
        sha256 = hashlib.sha256()
        with open(ruta_archivo, 'rb') as f:
            for bloque in iter(lambda: f.read(8192), b''):
                sha256.update(bloque)
        return sha256.hexdigest()
    
    def validar_pg_dump(self):
        """Verificar que pg_dump está disponible."""
        try:
            subprocess.run(['which', 'pg_dump'], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            print("❌ ERROR: pg_dump no instalado. Instala: sudo apt-get install postgresql-client")
            return False
    
    def respaldar_base_datos(self):
        """Crear respaldo SQL de la BD con pg_dump. Si no está disponible, usar JSON."""
        if not self.validar_pg_dump():
            print("⚠️ pg_dump no disponible. Usando respaldo JSON.")
            return self.respaldar_base_datos_json()
        # Crear carpeta media si no existe
        if not self.media_root.exists():
            self.media_root.mkdir(parents=True, exist_ok=True)
        
        respaldo_sql = self.backup_dir / f'bd_{self.timestamp}.sql'
        
        try:
            print(f"⏳ Respaldando BD PostgreSQL '{self.db_name}'...")
            
            # Configurar password via variable de entorno (forma segura)
            env = os.environ.copy()
            env['PGPASSWORD'] = str(self.db_password)
            
            # Comando pg_dump
            cmd = [
                'pg_dump',
                f'--host={self.db_host}',
                f'--port={self.db_port}',
                f'--username={self.db_user}',
                f'--file={str(respaldo_sql)}',
                '--format=plain',
                '--no-owner',
                '--no-privileges',
                self.db_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                print(f"❌ Error en pg_dump: {result.stderr}")
                return False
            
            # Comprimir el archivo SQL
            respaldo_gz = respaldo_sql.with_suffix('.sql.gz')
            with open(respaldo_sql, 'rb') as f_in:
                with gzip.open(respaldo_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Eliminar SQL sin comprimir
            respaldo_sql.unlink()
            
            # Calcular checksum SHA256
            self.ultimo_checksum = self.calcular_checksum(respaldo_gz)
            self.ultimo_archivo = respaldo_gz.name
            self.ultimo_tamaño = respaldo_gz.stat().st_size / 1024 / 1024  # MB
            
            print(f"✅ Respaldo BD creado: {respaldo_gz.name} ({self.ultimo_tamaño:.2f} MB)")
            print(f"🔐 SHA256: {self.ultimo_checksum[:16]}...")
            return True
            
        except Exception as e:
            print(f"❌ Error respaldando BD: {str(e)}")
            return False
    
    def respaldar_base_datos_json(self):
        """Crear respaldo en formato JSON (portable, compatible con cualquier BD)."""
        try:
            from django.core.management import call_command
            from io import StringIO
            from django.db import connection
            print(f"⏳ Respaldando BD en formato JSON (portable)...")
            respaldo_json = self.backup_dir / f'bd_{self.timestamp}.json'
            respaldo_gz = self.backup_dir / f'bd_{self.timestamp}.json.gz'
            # Usar dumpdata de Django para exportar todos los datos
            output = StringIO()
            with connection.cursor():
                call_command(
                    'dumpdata',
                    '--natural-foreign',
                    '--natural-primary',
                    '--indent', '2',
                    '--exclude', 'contenttypes',
                    '--exclude', 'auth.permission',
                    '--exclude', 'sessions',
                    stdout=output
                )
            json_content = output.getvalue()
            with open(respaldo_json, 'w', encoding='utf-8') as f:
                f.write(json_content)
            with open(respaldo_json, 'rb') as f_in:
                with gzip.open(respaldo_gz, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            respaldo_json.unlink()
            self.ultimo_checksum = self.calcular_checksum(respaldo_gz)
            self.ultimo_archivo = respaldo_gz.name
            self.ultimo_tamaño = respaldo_gz.stat().st_size / 1024 / 1024  # MB
            print(f"✅ Respaldo BD JSON creado: {respaldo_gz.name} ({self.ultimo_tamaño:.2f} MB)")
            print(f"🔐 SHA256: {self.ultimo_checksum[:16]}...")
            return True
        except Exception as e:
            print(f"❌ Error respaldando BD en JSON: {str(e)}")
            return False
    
    def respaldar_media(self):
        """Crear respaldo de archivos media (certificados, logos, etc)."""
        if not self.media_root.exists():
            print(f"⚠️  Carpeta media no existe: {self.media_root}")
            return False
        
        try:
            print(f"⏳ Respaldando archivos media...")
            
            # make_archive agrega la extensión .tar.gz automáticamente
            base_name = str(self.backup_dir / f'media_{self.timestamp}')
            
            # Crear tar.gz de media
            archivo_creado = shutil.make_archive(
                base_name,
                'gztar',
                self.media_root.parent,
                self.media_root.name
            )
            
            # Calcular checksum SHA256
            archivo_path = Path(archivo_creado)
            self.ultimo_checksum = self.calcular_checksum(archivo_path)
            self.ultimo_archivo = archivo_path.name
            self.ultimo_tamaño = archivo_path.stat().st_size / 1024 / 1024  # MB
            
            print(f"✅ Respaldo media creado: {archivo_path.name} ({self.ultimo_tamaño:.2f} MB)")
            print(f"🔐 SHA256: {self.ultimo_checksum[:16]}...")
            return True
            
        except Exception as e:
            print(f"❌ Error respaldando media: {str(e)}")
            return False
    
    def limpiar_respaldos_antiguos(self, dias=30):
        """Eliminar respaldos más antiguos que X días (BD y media)."""
        try:
            import time
            ahora = time.time()
            dias_segundos = dias * 24 * 60 * 60
            
            eliminados = 0
            # Limpiar respaldos de BD
            for archivo in self.backup_dir.glob('bd_*.sql.gz'):
                if ahora - archivo.stat().st_mtime > dias_segundos:
                    archivo.unlink()
                    eliminados += 1
            
            # Limpiar respaldos de media
            for archivo in self.backup_dir.glob('media_*.tar.gz'):
                if ahora - archivo.stat().st_mtime > dias_segundos:
                    archivo.unlink()
                    eliminados += 1
            
            # Limpiar respaldos JSON
            for archivo in self.backup_dir.glob('bd_*.json.gz'):
                if ahora - archivo.stat().st_mtime > dias_segundos:
                    archivo.unlink()
                    eliminados += 1
            
            if eliminados > 0:
                print(f"🗑️  Eliminados {eliminados} respaldos antiguos (> {dias} días)")
            
            return True
        except Exception as e:
            print(f"⚠️  Error limpiando respaldos antiguos: {str(e)}")
            return True  # No es crítico
    
    def enviar_notificacion_error(self, tipo_respaldo, error_msg):
        """Enviar notificación por email cuando un respaldo falla."""
        try:
            from django.core.mail import send_mail
            from possitema.models import ConfiguracionEmpresa
            
            config = ConfiguracionEmpresa.objects.first()
            destinatario = config.email if config and config.email else None
            
            if not destinatario:
                print("⚠️  No hay email configurado para notificaciones de respaldo.")
                return
            
            send_mail(
                subject=f'❌ Respaldo {tipo_respaldo} FALLIDO - {datetime.now().strftime("%d/%m/%Y %H:%M")}',
                message=(
                    f'El respaldo automático de tipo "{tipo_respaldo}" ha fallado.\n\n'
                    f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n'
                    f'Base de datos: {self.db_name}\n'
                    f'Host: {self.db_host}:{self.db_port}\n\n'
                    f'Error: {error_msg}\n\n'
                    f'Por favor revisa el sistema lo antes posible.'
                ),
                from_email=None,  # Usa DEFAULT_FROM_EMAIL
                recipient_list=[destinatario],
                fail_silently=True,
            )
            print(f"📧 Notificación de error enviada a {destinatario}")
        except Exception as e:
            print(f"⚠️  No se pudo enviar notificación por email: {e}")
    
    def listar_respaldos(self):
        """Listar todos los respaldos disponibles."""
        archivos = sorted(self.backup_dir.glob('*_*.sql.gz'), reverse=True)
        
        if not archivos:
            print("No hay respaldos disponibles")
            return
        
        print("\n📋 RESPALDOS DISPONIBLES:")
        print("-" * 70)
        for i, archivo in enumerate(archivos[:10], 1):  # Últimos 10
            tamaño = archivo.stat().st_size / 1024 / 1024  # MB
            fecha = datetime.fromtimestamp(archivo.stat().st_mtime)
            print(f"{i}. {archivo.name:<40} ({tamaño:>6.2f} MB) - {fecha}")
        print("-" * 70)
    
    def subir_a_google_drive(self, archivo_path):
        """Sube el archivo de respaldo a Google Drive usando la API."""
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2 import service_account
            # Ruta al archivo de credenciales JSON de Google Service Account
            cred_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS', 'google_drive_credentials.json')
            if not os.path.exists(cred_path):
                print(f"⚠️  No se encontró el archivo de credenciales: {cred_path}")
                return False
            SCOPES = ['https://www.googleapis.com/auth/drive.file']
            creds = service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
            service = build('drive', 'v3', credentials=creds)
            file_metadata = {'name': os.path.basename(archivo_path)}
            media = MediaFileUpload(archivo_path, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            print(f"☁️  Respaldo subido a Google Drive con ID: {file.get('id')}")
            return True
        except Exception as e:
            print(f"❌ Error subiendo respaldo a Google Drive: {e}")
            return False

    def ejecutar_respaldo_completo(self):
        """Realizar respaldo completo de BD y media."""
        print("\n" + "="*70)
        print("🔄 INICIANDO RESPALDO COMPLETO")
        print("="*70)
        resultados = {
            'BD': self.respaldar_base_datos(),
            'Media': self.respaldar_media(),
        }
        # Subir último respaldo a Google Drive si fue exitoso
        if self.ultimo_archivo:
            archivo_path = str(self.backup_dir / self.ultimo_archivo)
            self.subir_a_google_drive(archivo_path)

        # Limpiar respaldos antiguos
        self.limpiar_respaldos_antiguos(dias=30)
        
        # Resumen
        print("\n" + "="*70)
        print("📊 RESUMEN DEL RESPALDO:")
        for tipo, exito in resultados.items():
            estado = "✅ Exitoso" if exito else "❌ Fallido"
            print(f"  {tipo}: {estado}")
        print(f"  Ubicación: {self.backup_dir}")
        if self.ultimo_checksum:
            print(f"  Último checksum: {self.ultimo_checksum[:16]}...")
        print("="*70 + "\n")
        # Enviar notificación si algo falló
        fallos = [tipo for tipo, exito in resultados.items() if not exito]
        if fallos:
            self.enviar_notificacion_error(
                ', '.join(fallos),
                f'Fallaron los siguientes componentes del respaldo: {", ".join(fallos)}'
            )
        return all(resultados.values())


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Respaldo de BD y archivos media')
    parser.add_argument('--db-only', action='store_true', help='Solo BD')
    parser.add_argument('--media-only', action='store_true', help='Solo media')
    parser.add_argument('--list', action='store_true', help='Listar respaldos')
    
    args = parser.parse_args()
    
    respaldo = RespaldoDatabase()
    
    if args.list:
        respaldo.listar_respaldos()
    elif args.db_only:
        respaldo.respaldar_base_datos()
    elif args.media_only:
        respaldo.respaldar_media()
    else:
        respaldo.ejecutar_respaldo_completo()


if __name__ == '__main__':
    main()
