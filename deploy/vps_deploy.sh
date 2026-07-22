#!/bin/bash
# Despliega la ultima version de main en el VPS: trae el codigo, reconstruye
# el frontend y/o reinicia el backend solo si hubo cambios en esa parte
# desde el ultimo despliegue exitoso (evita rebuilds/reinicios innecesarios
# cuando el commit solo toco la otra mitad del stack). Se corre siempre
# desde /srv/medglobal:
#
#   cd /srv/medglobal && bash deploy/vps_deploy.sh
#
# Guarda el commit ya desplegado en un archivo local (no versionado) en vez
# de comparar solo contra el pull de esta misma corrida -- si alguien hizo
# "git pull" a mano antes de correr el script, comparar unicamente el antes
# y despues de ESE pull hace que el script crea que no hay nada que
# reconstruir aunque el codigo si haya cambiado desde el ultimo deploy real.
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_PIP="backend/venv/bin/pip"
SERVICE="medglobal-backend.service"
MARKER=".deploy_last_commit"

last_deployed=""
[ -f "$MARKER" ] && last_deployed="$(cat "$MARKER")"

git pull origin main
current="$(git rev-parse HEAD)"

if [ "$last_deployed" = "$current" ]; then
  echo "Ya esta desplegado el commit actual ($current). Nada que hacer."
  exit 0
fi

frontend_changed=1
backend_changed=1
if [ -n "$last_deployed" ] && git cat-file -e "$last_deployed" 2>/dev/null; then
  changed="$(git diff --name-only "$last_deployed" "$current")"
  echo "Desplegando $last_deployed -> $current"
  echo "$changed" | grep -q '^frontend/' || frontend_changed=0
  echo "$changed" | grep -qE '^backend/(.*\.py|requirements\.txt)$' || backend_changed=0
else
  echo "No hay registro de un despliegue previo valido -- se reconstruye todo."
fi

if [ "$frontend_changed" = "1" ]; then
  echo "== Frontend cambio: reconstruyendo dist/ =="
  (cd frontend && npm install && npm run build)
fi

if [ "$backend_changed" = "1" ]; then
  echo "== Backend cambio: actualizando dependencias y reiniciando servicio =="
  "$VENV_PIP" install -r backend/requirements.txt
  restart_backend=1
fi

chown -R medglobal:www-data .

if [ "${restart_backend:-0}" = "1" ]; then
  systemctl restart "$SERVICE"
  systemctl status "$SERVICE" --no-pager
fi

echo "$current" > "$MARKER"
echo "Deploy completo ($current)."
