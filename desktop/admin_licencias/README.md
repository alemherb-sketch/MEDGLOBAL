# Generador y gestión remota de licencias MEDGLOBAL

## Recomendación (mejor práctica)

| Pieza | Dónde | Qué guarda |
|-------|--------|------------|
| **Panel admin** (este servicio) | VPS o PC de sistemas con HTTPS | **Clave privada** + registro de licencias/cupos |
| **App escritorio** en clínicas | Cada PC | Solo **clave pública** + código activado local |
| **App web** | VPS principal | Sin licencias (no aplican) |

Las PCs **no necesitan internet** para validar una licencia ya emitida (firma offline).  
El panel remoto sirve para **emitir, listar, copiar de nuevo y revocar**.  
Si configura `MEDGLOBAL_LICENCIAS_URL` en el `.env` del escritorio, la activación también se **registra por cupo** y se puede **revocar online**.

```
Admin (navegador)
      │  token
      ▼
┌─────────────────────────────┐
│  admin_licencias :8010      │  ← clave privada + SQLite
│  Emite códigos firmados     │
│  Lista / revoca / cupos     │
└─────────────┬───────────────┘
              │ código firmado
              ▼
┌─────────────────────────────┐
│  MEDGLOBAL.exe en clínica   │  ← solo clave pública
│  Activar licencia           │
└─────────────────────────────┘
```

No hace falta modificar el repositorio desplegado de la web (`main.py`).  
Nginx puede exponer solo este servicio en un subdominio cerrado.

## Arranque

```powershell
cd desktop\admin_licencias
# copiar claves generadas:
#   backend\generar_claves_licencia.py  → privada y publica
copy ..\..\backend\licencia_privada.pem .
copy ..\..\backend\licencia_publica.pem .

$env:LICENCIAS_ADMIN_TOKEN = "un-token-largo-secreto"
$env:LICENCIA_PRIVADA = (Resolve-Path .\licencia_privada.pem).Path
$env:LICENCIA_PUBLICA = (Resolve-Path .\licencia_publica.pem).Path

..\..\backend\venv_fresh\Scripts\pip.exe install -r requirements.txt
..\..\backend\venv_fresh\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8010
```

Abra: http://127.0.0.1:8010  
Entre con el token.

## Flujo diario

1. En la PC de la clínica: pantalla **Activar licencia** → copiar `machine_id`.
2. En el panel: cliente + pegar machine_id + días → **Generar licencia**.
3. Copiar el código → pegarlo en la PC → Activar.
4. Si pierde el código: botón **Código** en la tabla.
5. Si una clínica deja de tener derecho: **Revocar**.

### Cupo sin lista de IDs

Ponga `max_pcs = 5` y deje machines vacío.  
En cada PC con el mismo código (y con `MEDGLOBAL_LICENCIAS_URL` apuntando aquí) el servicio registra hasta 5 activaciones.

## Escritorio con chequeo remoto

En el `.env` de la app de escritorio:

```env
MEDGLOBAL_LICENCIAS_URL=https://licencias.su-dominio.com
```

(O `http://127.0.0.1:8010` en pruebas.)

## Nginx (ejemplo)

```nginx
server {
    server_name licencias.su-dominio.com;
    # TLS con certbot...
    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Restrinja por VPN o IP de confianza si el panel es solo interno.

## CLI (misma criptografía, sin panel)

```powershell
cd backend
.\venv_fresh\Scripts\python.exe generar_licencia.py --cliente "X" --machine-id ID --dias 365
```

El panel es preferible cuando hay varias clínicas o se necesita revocar a distancia.
