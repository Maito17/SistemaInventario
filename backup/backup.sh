#!/bin/bash
#
# Script de respaldo automático para Sistema de Ventas Casa
# Ubicación: /backup/backup.sh
#
# Uso manual:
#   bash backup.sh                          # Respaldo completo
#   bash backup.sh db                       # Solo BD
#   bash backup.sh media                    # Solo media
#
# Para automatizar con cron (respaldo diario a las 2:00 AM):
#   0 2 * * * cd /ruta/proyecto && bash backup/backup.sh >> backup/logs/cron.log 2>&1
#

set -e

# Obtener ruta del proyecto
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Crear carpeta de logs
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/backup_$(date +\%Y\%m\%d).log"

# Función para loguear
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "════════════════════════════════════════════"
log "Iniciando respaldo automático"
log "Proyecto: $PROJECT_ROOT"
log "════════════════════════════════════════════"

# Cambiar a directorio del proyecto
cd "$PROJECT_ROOT"

# Activar virtualenv si existe
if [ -f ".venv/bin/activate" ]; then
    log "Activando entorno virtual..."
    source .venv/bin/activate
fi

# Ejecutar según parámetro
case "${1:-all}" in
    db)
        log "Ejecutando respaldo SOLO BD..."
        python backup/backup_database.py --db-only
        ;;
    media)
        log "Ejecutando respaldo SOLO MEDIA..."
        python backup/backup_database.py --media-only
        ;;
    list)
        log "Listando respaldos..."
        python backup/backup_database.py --list
        ;;
    *)
        log "Ejecutando respaldo COMPLETO..."
        python backup/backup_database.py
        ;;
esac

log "════════════════════════════════════════════"
log "✅ Respaldo completado exitosamente"
log "════════════════════════════════════════════"
