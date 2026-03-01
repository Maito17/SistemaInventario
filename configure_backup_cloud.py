#!/usr/bin/env python3
"""
Script para configurar almacenamiento cloud para respaldos.
Soporta: Google Drive, AWS S3

Uso:
    python configure_backup_cloud.py                  # Menú interactivo
    python configure_backup_cloud.py --google-drive   # Google Drive
    python configure_backup_cloud.py --aws-s3         # AWS S3
"""

import os
import sys
import json
import argparse
from pathlib import Path
from urllib.parse import quote

def print_banner():
    """Mostrar banner de bienvenida."""
    print("""
    ╔════════════════════════════════════════════╗
    ║    ☁️  CONFIGURAR ALMACENAMIENTO CLOUD    ║
    ║      Para Respaldos en Railway/Producción ║
    ╚════════════════════════════════════════════╝
    """)

def configure_google_drive():
    """Configurar Google Drive."""
    print("\\n📁 CONFIGURACIÓN DE GOOGLE DRIVE\\n")
    print("Este proceso te ayudará a configurar Google Drive para guardar respaldos.\\n")
    
    print("PASO 1: Crear Service Account")
    print("-" * 50)
    print("""
    1. Ve a: https://console.cloud.google.com
    2. Crea un proyecto nuevo: "Respaldos Sistema Inventario"
    3. Habilita Google Drive API:
       - Menu → API y servicios → Biblioteca
       - Busca "Google Drive API"
       - Click "Habilitar"
    4. Crea Service Account:
       - Menu → Credenciales
       - "Crear credenciales" → "Cuenta de servicio"
       - Nombre: "backup-system"
       - Crear
    5. Genera clave JSON:
       - Click en la cuenta creada
       - Tab "Claves"
       - "Agregar clave" → "Nueva clave" → "JSON"
       - Se descarga automáticamente
    """)
    
    service_account_path = input("\\n✓ Ruta al archivo JSON descargado (ej: ~/Downloads/...json): ").strip()
    
    if not Path(service_account_path).exists():
        print("❌ Error: Archivo no encontrado")
        return False
    
    # Copiar archivo a directorio seguro
    project_root = Path(__file__).parent
    creds_path = project_root / 'credenciales_drive.json'
    
    import shutil
    shutil.copy(service_account_path, creds_path)
    print(f"✅ Credencial copiada a: {creds_path}")
    
    # Obtener email del service account
    with open(creds_path) as f:
        creds = json.load(f)
        service_email = creds.get('client_email', '')
    
    print("\\nPASO 2: Crear carpeta en Google Drive")
    print("-" * 50)
    print("""
    1. Abre: https://drive.google.com
    2. Nueva carpeta → Nombre: "Respaldos SistemaInventario"
    3. Abre la carpeta
    4. La URL será algo como: https://drive.google.com/drive/folders/1ABC123XYZ...
    5. Copia la parte después de "folders/": 1ABC123XYZ...
    """)
    
    folder_id = input("\\n✓ ID de la carpeta (después de 'folders/'): ").strip()
    
    print("\\nPASO 3: Compartir carpeta con Service Account")
    print("-" * 50)
    print(f"""
    1. En tu carpeta de Google Drive (Respaldos SistemaInventario)
    2. Click derecho → Compartir
    3. Pega este email y dale permisos de "Editor":
    
       📧 {service_email}
    
    4. Click compartir
    """)
    
    input("\\n✓ Presiona Enter cuando hayas compartido la carpeta...")
    
    # Actualizar .env
    env_path = project_root / '.env'
    env_content = ""
    
    if env_path.exists():
        with open(env_path) as f:
            env_content = f.read()
    
    # Agregar/actualizar variables
    env_updates = {
        'GOOGLE_DRIVE_ENABLED': 'True',
        'GOOGLE_DRIVE_FOLDER_ID': folder_id,
        'GOOGLE_DRIVE_CREDENTIALS': '/app/credenciales_drive.json'
    }
    
    for key, value in env_updates.items():
        if key in env_content:
            # Reemplazar línea existente
            import re
            env_content = re.sub(f'{key}=.*', f'{key}={value}', env_content)
        else:
            # Agregar nueva línea
            env_content += f'\\n{key}={value}'
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"""
    ✅ CONFIGURACIÓN COMPLETADA
    
    Variables agregadas a .env:
    • GOOGLE_DRIVE_ENABLED=True
    • GOOGLE_DRIVE_FOLDER_ID={folder_id}
    • GOOGLE_DRIVE_CREDENTIALS=/app/credenciales_drive.json
    
    📝 IMPORTANTE PARA RAILWAY:
    1. Sube credenciales_drive.json a tu repositorio
       (asegúrate de que ESTÁ en .gitignore si es público)
    
    2. En Railway, agrega en Variables:
       GOOGLE_DRIVE_ENABLED=True
       GOOGLE_DRIVE_FOLDER_ID={folder_id}
    
    3. Deploy y prueba crear un respaldo
    
    4. Verifica que aparezca en:
       https://drive.google.com/drive/folders/{folder_id}
    """)
    
    return True

def configure_aws_s3():
    """Configurar AWS S3."""
    print("\\n☁️  CONFIGURACIÓN DE AWS S3\\n")
    print("""
    Este proceso configura AWS S3 para guardar respaldos.
    
    Requisitos:
    • Cuenta de AWS (aws.amazon.com)
    • Access Key y Secret Access Key de un usuario IAM
    """)
    
    print("\\nPASO 1: Crear bucket S3")
    print("-" * 50)
    print("""
    1. Abre: https://s3.console.aws.amazon.com
    2. "Create bucket"
    3. Nombre: sistema-inventario-respaldos
    4. Región: us-east-1 (o la más cercana)
    5. Create bucket
    """)
    
    bucket_name = input("\\n✓ Nombre del bucket (ej: sistema-inventario-respaldos): ").strip()
    region = input("✓ Región AWS (ej: us-east-1): ").strip() or 'us-east-1'
    
    print("\\nPASO 2: Crear usuario IAM con acceso a S3")
    print("-" * 50)
    print("""
    1. Abre: https://iam.console.aws.amazon.com
    2. "Users" → "Create user"
    3. Nombre: backup-system
    4. Skip password, Create user
    5. Click en el usuario creado
    6. "Security credentials" → "Create access key"
    7. Use case: Application running outside AWS
    8. Skip tags
    9. Create access key
    10. Descarga CSV (contiene Access Key ID y Secret Access Key)
    
    Luego agrega permisos:
    1. En el usuario, "Add inline policy"
    2. JSON, pega esto:
    
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::tu-bucket/*",
                    "arn:aws:s3:::tu-bucket"
                ]
            }
        ]
    }
    
    Reemplaza "tu-bucket" con tu nombre real de bucket.
    """)
    
    access_key = input("\\n✓ AWS Access Key ID (del CSV): ").strip()
    secret_key = input("✓ AWS Secret Access Key (del CSV): ").strip()
    
    # Actualizar .env
    project_root = Path(__file__).parent
    env_path = project_root / '.env'
    env_content = ""
    
    if env_path.exists():
        with open(env_path) as f:
            env_content = f.read()
    
    env_updates = {
        'AWS_S3_ENABLED': 'True',
        'AWS_S3_BUCKET': bucket_name,
        'AWS_REGION': region,
        'AWS_ACCESS_KEY_ID': access_key,
        'AWS_SECRET_ACCESS_KEY': secret_key
    }
    
    for key, value in env_updates.items():
        if key in env_content:
            import re
            env_content = re.sub(f'{key}=.*', f'{key}={value}', env_content)
        else:
            env_content += f'\\n{key}={value}'
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"""
    ✅ CONFIGURACIÓN COMPLETADA
    
    Variables agregadas a .env:
    • AWS_S3_ENABLED=True
    • AWS_S3_BUCKET={bucket_name}
    • AWS_REGION={region}
    • AWS_ACCESS_KEY_ID={access_key}
    • AWS_SECRET_ACCESS_KEY={secret_key}
    
    📝 IMPORTANTE:
    1. NUNCA hagas commit de .env (está en .gitignore)
    2. En Railway, copia estas variables en Settings
    3. Deploy y prueba crear un respaldo
    4. Verifica en AWS S3 que aparezca el archivo
    """)
    
    return True

def show_menu():
    """Mostrar menú interactivo."""
    print_banner()
    print("""
    ¿Qué servicio de almacenamiento deseas configurar?
    
    1⃣  Google Drive (Recomendado para empezar)
    2⃣  AWS S3 (Para empresas / mayor escala)
    3⃣  Salir
    """)
    
    choice = input("Escoge opción (1-3): ").strip()
    
    if choice == '1':
        return configure_google_drive()
    elif choice == '2':
        return configure_aws_s3()
    elif choice == '3':
        print("\\n✅ Adiós!")
        return False
    else:
        print("❌ Opción inválida")
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Configurar almacenamiento cloud para respaldos')
    parser.add_argument('--google-drive', action='store_true', help='Configurar Google Drive')
    parser.add_argument('--aws-s3', action='store_true', help='Configurar AWS S3')
    
    args = parser.parse_args()
    
    success = False
    
    if args.google_drive:
        success = configure_google_drive()
    elif args.aws_s3:
        success = configure_aws_s3()
    else:
        success = show_menu()
    
    sys.exit(0 if success else 1)
