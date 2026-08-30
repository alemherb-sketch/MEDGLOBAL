# Mudar MEDGLOBAL a su propio VPS

Hoy MEDGLOBAL comparte servidor con el ERP (`200.97.170.230`). Este documento
es la receta para llevarlo a un VPS propio **sin romper las instalaciones
offline que ya están en campo**.

## Antes de empezar: rellena esto

```
IP_NUEVA        = ...
DOMINIO_NUEVO   = ...            # p. ej. medglobal.pe
API_NUEVO       = api.<DOMINIO_NUEVO>
```

## Lo que hay que saber del montaje actual

| | |
|---|---|
| Ruta | `/srv/medglobal` |
| Servicio | `medglobal-backend.service` |
| Backend | FastAPI + uvicorn en `127.0.0.1:8000` |
| venv | `backend/venv` (**no** `.venv`: `vps_deploy.sh` lo espera así) |
| Base de datos | **PostgreSQL**, base `medglobal` (vía `DATABASE_URL` del `.env`) |
| Usuario | `medglobal:www-data` |

> `database.py` cae a SQLite (`sqlite:///./medglobal.db`) **solo si no existe
> `DATABASE_URL`** — que es el caso del instalable de escritorio. En el VPS la
> variable sí está definida y los datos viven en PostgreSQL, en la misma
> instancia que aloja las bases del ERP.
| Frontend | `frontend/dist`, servido por nginx |

**Son dos subdominios, no uno:**

- `medglobal.erpgest.com.pe` → el frontend
- `api.medglobal.erpgest.com.pe` → el API

---

## Las dos trampas de esta migración

### 1. El frontend trae el API hardcodeado

En `frontend/src/config.js`, si no se define `VITE_API_URL` al compilar, la
build de producción cae a un valor fijo:

```js
: (import.meta.env.PROD
  ? 'https://api.medglobal.erpgest.com.pe'   // ← fallback fijo
  : 'http://localhost:8000');
```

Si compilas en el VPS nuevo sin definir la variable, el frontend seguirá
llamando al dominio viejo. **Siempre compilar así:**

```bash
cd /srv/medglobal/frontend
VITE_API_URL=https://<API_NUEVO> npm run build
```

### 2. Las instalaciones offline apuntan al servidor por `.env`

Cada instalación lleva su propio `.env` junto al ejecutable
(`MEDGLOBAL_Local_App/.env`) con `SYNC_SERVER_URL`, `SYNC_USERNAME` y
`SYNC_PASSWORD`. `app_desktop.py` lo lee al arrancar.

Cambiar de dominio **deja a esos equipos sin sincronizar** hasta que alguien
edite ese archivo o reinstale.

**La salida: servir los dos dominios a la vez.** nginx acepta varios
`server_name` y certbot emite un certificado para todos. Se re-apunta el DNS
viejo al VPS nuevo y los equipos en campo siguen funcionando sin tocar nada;
el dominio nuevo queda como el oficial y los clientes se migran con calma.

Si son dos o tres instalaciones que controlas tú, puedes saltarte esto y
actualizarles el `.env` a mano.

---

## Fase 1 — Respaldo (VPS actual)

`pg_dump` es consistente en caliente: **no hay que detener el servicio**.

```bash
sudo -u postgres pg_dump --create --clean --if-exists medglobal \
  | gzip > ~/medglobal-db-$(date +%F).sql.gz
sudo -u postgres pg_dumpall --globals-only > ~/medglobal-roles-$(date +%F).sql
sudo cp /srv/medglobal/backend/.env ~/medglobal-env-$(date +%F).bak
```

`--create` incluye el `CREATE DATABASE` con su dueño. Los roles van aparte
porque `pg_dump` no los trae, y sin ellos la restauración falla con
«role does not exist».

> **No uses `pg_dumpall` completo.** Esa instancia también aloja las 9 bases del
> ERP (`erp_control` y las de cada empresa): se llevaría todo mezclado.

Guarda también la configuración actual, que sirve de referencia:

```bash
sudo cp /etc/nginx/sites-available/medglobal* ~/ 2>/dev/null
sudo cp /etc/systemd/system/medglobal-backend.service ~/ 2>/dev/null
```

Bájatelo todo a tu PC:

```bash
scp usuario@200.97.170.230:~/medglobal-* .
```

Verifica que el volcado trae datos y no solo el esquema:

```bash
zcat ~/medglobal-db-*.sql.gz | grep -c "COPY public"
zcat ~/medglobal-db-*.sql.gz | tail -3
ls -lh ~/medglobal-*
```

El conteo debe ser mayor que cero y el final del archivo verse completo, no
cortado a media sentencia.

---

## Fase 2 — Montaje en el VPS nuevo

> **Atención con PostgreSQL.** El servidor actual corre **PostgreSQL 18.4** sobre
> Ubuntu 24.04, y los repositorios de Ubuntu traen la 16. Un `apt install
> postgresql` a secas instala la 16 y la restauración **falla**: un volcado de la
> 18 no entra en una 16. Hay que añadir el repositorio oficial PGDG.

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nginx git curl \
     ca-certificates gnupg
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs

# Repositorio oficial de PostgreSQL, para instalar la 18
sudo install -d /usr/share/postgresql-common/pgdg
sudo curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
     --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  | sudo tee /etc/apt/sources.list.d/pgdg.list
sudo apt update && sudo apt install -y postgresql-18
```

Confirma antes de restaurar que la versión es igual o mayor:

```bash
psql --version    # debe decir 18.x o superior
```

Usuario del sistema que espera `vps_deploy.sh`:

```bash
sudo useradd -r -s /usr/sbin/nologin medglobal 2>/dev/null || true
```

Código y dependencias:

```bash
sudo mkdir -p /srv/medglobal && sudo chown $USER /srv/medglobal
git clone https://github.com/alemherb-sketch/MEDGLOBAL.git /srv/medglobal
cd /srv/medglobal/backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Restaurar la base. **Primero los roles, después los datos**, o falla con
«role does not exist»:

```bash
scp ~/medglobal-roles-*.sql ~/medglobal-db-*.sql.gz ~/medglobal-env-*.bak \
    usuario@<IP_NUEVA>:~/
```

```bash
sudo -u postgres psql -f ~/medglobal-roles-*.sql
zcat ~/medglobal-db-*.sql.gz | sudo -u postgres psql
```

Comprueba que llegó completa:

```bash
sudo -u postgres psql -d medglobal -c "select count(*) from atenciones;"
sudo -u postgres psql -d medglobal -c "select count(*) from usuarios;"
```

Configuración:

```bash
cp ~/medglobal-env-*.bak /srv/medglobal/backend/.env
chmod 600 /srv/medglobal/backend/.env
```

El `DATABASE_URL` de ese `.env` apunta a `localhost`, así que sigue sirviendo
tal cual en el servidor nuevo: la contraseña del rol vino en el volcado de roles.

**Pero hay que editar `ALLOWED_ORIGINS`.** Hoy vale solo:

```
ALLOWED_ORIGINS=https://medglobal.erpgest.com.pe
```

Si no le agregas el dominio nuevo, el navegador bloqueará por CORS todas las
llamadas del frontend nuevo al API y el dashboard quedará en ceros:

```
ALLOWED_ORIGINS=https://<DOMINIO_NUEVO>,https://medglobal.erpgest.com.pe
```

El `.env` trae además una **tercera línea suelta**: 64 caracteres hexadecimales
sin nombre de variable. Al no tener la forma `CLAVE=valor` no la lee nadie, así
que es residuo — pero si corresponde a una clave de firma usada en otro sitio,
conviene rotarla y quitarla de aquí.

En ese `.env`, si `SYNC_SERVER_URL` apunta a este mismo servidor, actualízalo al
dominio nuevo.

Compilar el frontend **con la variable puesta** (ver trampa 1):

```bash
cd /srv/medglobal/frontend
npm install
VITE_API_URL=https://<API_NUEVO> npm run build
```

```bash
sudo chown -R medglobal:www-data /srv/medglobal
```

---

## Fase 3 — systemd

```ini
# /etc/systemd/system/medglobal-backend.service
[Unit]
Description=MEDGLOBAL API (FastAPI/uvicorn)
After=network.target

[Service]
Type=simple
User=medglobal
Group=www-data
WorkingDirectory=/srv/medglobal/backend
EnvironmentFile=/srv/medglobal/backend/.env
ExecStart=/srv/medglobal/backend/venv/bin/uvicorn main:app \
          --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`--host 127.0.0.1` no es opcional: el API solo debe ser accesible por nginx,
nunca directo desde internet.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now medglobal-backend
sudo systemctl status medglobal-backend --no-pager
```

---

## Fase 4 — nginx

Dos bloques. Fíjate en los `server_name`: llevan el dominio nuevo **y el viejo**,
que es lo que mantiene vivos a los clientes en campo.

```nginx
# Frontend
server {
    listen 80;
    server_name <DOMINIO_NUEVO> medglobal.erpgest.com.pe;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    http2 on;
    server_name <DOMINIO_NUEVO> medglobal.erpgest.com.pe;

    ssl_certificate     /etc/letsencrypt/live/<DOMINIO_NUEVO>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/<DOMINIO_NUEVO>/privkey.pem;

    root /srv/medglobal/frontend/dist;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
```

```nginx
# API
server {
    listen 80;
    server_name <API_NUEVO> api.medglobal.erpgest.com.pe;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    http2 on;
    server_name <API_NUEVO> api.medglobal.erpgest.com.pe;

    ssl_certificate     /etc/letsencrypt/live/<DOMINIO_NUEVO>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/<DOMINIO_NUEVO>/privkey.pem;

    client_max_body_size 25m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

El frontend y el API viven en orígenes distintos, así que el `ALLOWED_ORIGINS`
del backend debe incluir `https://<DOMINIO_NUEVO>` **y** el dominio viejo
mientras siga en uso.

---

## Fase 5 — DNS y certificados

Baja el TTL de los registros a 300 s **el día antes** (hoy están en 14400 = 4 h).

Apunta a la IP nueva:

```
<DOMINIO_NUEVO>                A  <IP_NUEVA>
<API_NUEVO>                    A  <IP_NUEVA>
medglobal.erpgest.com.pe       A  <IP_NUEVA>     ← re-apuntado
api.medglobal.erpgest.com.pe   A  <IP_NUEVA>     ← re-apuntado
```

Cuando resuelvan, un solo certificado para los cuatro nombres:

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
  -d <DOMINIO_NUEVO> -d <API_NUEVO> \
  -d medglobal.erpgest.com.pe -d api.medglobal.erpgest.com.pe
sudo systemctl reload nginx
```

---

## Fase 6 — Comprobar

```bash
curl -sI https://<DOMINIO_NUEVO>/            | head -1
curl -s   https://<API_NUEVO>/docs -o /dev/null -w "%{http_code}\n"
curl -sI https://medglobal.erpgest.com.pe/   | head -1    # el viejo sigue vivo
```

En el navegador, con el frontend abierto:

- [ ] Entra el login y se ve el dashboard **con datos**, no en ceros (si sale en
      ceros, el frontend se compiló sin `VITE_API_URL` y llama al dominio viejo).
- [ ] Las atenciones y el kardex muestran los registros que ya existían.

Y en un equipo con la instalación offline: fuerza una sincronización y confirma
que sube y baja sin conflictos de folios.

---

## Fase 7 — Retirar el servidor viejo

Con MEDGLOBAL ya sirviendo desde el VPS nuevo, en el **viejo**:

```bash
sudo systemctl disable --now medglobal-backend
```

No borres `/srv/medglobal` todavía. Déjalo **al menos 7 días** por si aparece
algo. Después de eso, el VPS viejo queda solo con el ERP y se puede reinstalar
en un datacenter cercano sin llevarse nada por delante.

El orden importa: **primero muda MEDGLOBAL, después reinstala el del ERP.**

---

## Lo que más se rompe

| Síntoma | Causa |
|---|---|
| Dashboard en ceros aunque hay datos | Se compiló sin `VITE_API_URL`: el frontend llama al dominio viejo |
| Los equipos en campo dejan de sincronizar | `SYNC_SERVER_URL` de su `.env` apunta a un dominio que ya no responde |
| Error de CORS en el navegador | Falta el dominio nuevo en `ALLOWED_ORIGINS` del backend |
| `502 Bad Gateway` | `medglobal-backend` caído; revisar `journalctl -u medglobal-backend -n 50` |
| `role "..." does not exist` al restaurar | Se restauró la base sin cargar antes `medglobal-roles-*.sql` |
| La app arranca pero sin datos | El backend cayó al SQLite por defecto: falta `DATABASE_URL` en el `.env` |
| `vps_deploy.sh` falla | Espera `backend/venv` (sin punto) y el usuario `medglobal` |
