#!/bin/sh
# Se ejecuta cada vez que arranca el contenedor en Render.
set -e

echo ">> Aplicando migraciones de gestion_it..."
python /app/gestion_it/manage.py migrate --noinput

echo ">> Arrancando todos los servicios con supervisord..."
exec supervisord -c /app/supervisord.conf