#!/bin/bash
# Despliega la ultima version de main en el VPS: trae el codigo, reconstruye
# el frontend y/o reinicia el backend solo si hubo cambios en esa parte
# (evita rebuilds/reinicios innecesarios cuando el commit solo toco la otra
# mitad del stack). Se corre siempre desde /srv/medglobal:
#
#   cd /srv/medglobal && bash deploy/vps_deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_PIP="backend/venv/bin/pip"
SERVICE="medglobal-backend.service"

before="$(git rev-parse HEAD)"
git pull origin main
after="$(git rev-parse HEAD)"

if [ "$before" = "$after" ]; then
  echo "Ya estaba en el ultimo commit ($before). Nada que desplegar."
  exit 0
fi

echo "Actualizado $before -> $after"
changed="$(git diff --name-only "$before" "$after")"

if echo "$changed" | grep -q '^frontend/'; then
  echo "== Frontend cambio: reconstruyendo dist/ =="
  (cd frontend && npm install && npm run build)
fi

if echo "$changed" | grep -qE '^backend/(.*\.py|requirements\.txt)$'; then
  echo "== Backend cambio: actualizando dependencias y reiniciando servicio =="
  "$VENV_PIP" install -r backend/requirements.txt
  restart_backend=1
fi

chown -R medglobal:www-data .

if [ "${restart_backend:-0}" = "1" ]; then
  systemctl restart "$SERVICE"
  systemctl status "$SERVICE" --no-pager
fi

echo "Deploy completo."
