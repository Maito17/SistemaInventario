# Sistema de Ventas (pos)

Proyecto Django para gestión de punto de venta. Este repositorio está preparado para desplegar en Railway.

Rápido inicio local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edita .env y añade SECRET_KEY y DATABASE_URL si usas una DB remota
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Variables de entorno (añadir en Railway -> Settings -> Variables):

- `SECRET_KEY` (requerido)
- `DEBUG=false`
- `DATABASE_URL` (Railway pone esto automáticamente si añades un servicio DB)
- `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` (si usas email real)
- `GEMINI_API_KEY` (opcional)

Deploy en Railway (pasos básicos)

1. Subir este repo a GitHub (ya está conectado).
2. En Railway: New Project → Deploy from GitHub → selecciona este repo.
3. En Settings del proyecto en Railway, añade variables de entorno listadas arriba.
4. En Build/Release commands (opcional) añade:

Build:
```bash
pip install -r requirements.txt
```

Release (ejecutar migraciones y collectstatic):
```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Railway usará el `Procfile` para arrancar la aplicación:

```
web: gunicorn possitema.wsgi --bind 0.0.0.0:$PORT
```

Notas y recomendaciones

- Asegúrate de fijar `DEBUG=false` en producción.
- Usa backups automáticos de la base de datos en Railway.
- Considera usar almacenamiento externo para `MEDIA` (S3 u otro).
- Añade protección de branch (`main`) y despliegues controlados por PRs.

Si quieres, aplico los pasos finales (migrations automáticas en release, añadir GitHub Action para tests, o configurar almacenamiento para `MEDIA`).
# SistemaPOS — Webhook de Confirmación de Pagos

Se añadió un endpoint para recibir confirmaciones de pago desde n8n y activar suscripciones automáticamente.

## Endpoint

- URL: `/api/v1/pagos/confirmar-ia/`
- Método: `POST`
- Content-Type: `application/json`

### Payload esperado

```json
{
  "token_secreto": "<tu_token>",
  "usuario_id": 1,
  "monto_real": "10.00",
  "plan_id": 2,
  "referencia_bancaria": "REF-ABC-123"
}
```

- `token_secreto`: token compartido entre tu servidor y n8n (ver más abajo).
- `usuario_id`: ID del usuario en la BD Django.
- `monto_real`: monto recibido (string o número aceptable por DecimalField).
- `plan_id`: ID del `Plan` a activar.
- `referencia_bancaria`: identificador único de la transferencia (se guarda en `comprobante_id`).

## Seguridad

Define un token secreto para proteger el webhook. Puedes usar una variable de entorno o añadirlo en `settings.py`:

- Variable de entorno recomendada: `PAYMENT_WEBHOOK_TOKEN`

Ejemplo (Linux/macOS):

```bash
export PAYMENT_WEBHOOK_TOKEN="mi-token-seguro-ya123"
```

En despliegue (p.ej. Railway), configura `PAYMENT_WEBHOOK_TOKEN` en las variables de entorno del servicio.

## Respuestas

- 200: Pago procesado y suscripción activada
- 400: Error (token inválido, usuario/plan no encontrado o referencia duplicada)

## Pruebas locales

Usa `curl` para probar localmente (reemplaza `TU_TOKEN` y IDs):

```bash
curl -X POST http://localhost:8000/api/v1/pagos/confirmar-ia/ \
  -H "Content-Type: application/json" \
  -d '{"token_secreto":"TU_TOKEN","usuario_id":1,"monto_real":"10.00","plan_id":1,"referencia_bancaria":"REF-TEST-001"}'
```

También se añadieron tests en `possitema/tests.py` que validan el caso exitoso y el caso de referencia duplicada.

## Notas

- El modelo `RegistroPago` ahora tiene el campo `comprobante_id` (`unique=True`) para evitar duplicados.
- Asegúrate de ejecutar migraciones después de desplegar los cambios:

```bash
python manage.py makemigrations possitema
python manage.py migrate
```

¿Quieres que añada instrucciones específicas para configurar n8n (ejemplo de workflow)?
