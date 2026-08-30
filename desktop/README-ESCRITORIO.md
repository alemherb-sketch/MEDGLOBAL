# MEDGLOBAL Escritorio (ventana nativa de Windows)

Aplicacion **de escritorio**: se ejecuta como `.exe` con su propia ventana
(WebView2 embebido). **No se abre el navegador.** Mantiene las mismas pantallas
y logica de la version web, base local SQLite y sincronizacion con el VPS.

> No hace falta redesplegar GitHub/VPS para usar el escritorio. El VPS sigue
> sirviendo la web y recibe las sync de cada PC por `/sync/*`.

## Arquitectura

```
┌─────────────────────────────────────────┐
│  Ventana nativa Windows (pywebview)     │  ← lo que ve el usuario
│  misma UI React de la web               │
└─────────────────┬───────────────────────┘
                  │ http://127.0.0.1:puerto
┌─────────────────▼───────────────────────┐
│  Motor local (FastAPI + SQLite)         │  ← todas las funciones offline
│  Boton "Sincronizar ahora" ─────────────┼──► VPS (PostgreSQL web)
└─────────────────────────────────────────┘
```

No se reescribe en Flask: la web ya esta en FastAPI/React. Flask obligaria
a rehacer todas las APIs. La diferencia de "escritorio" es la **ventana
nativa**, no el framework del servidor local.

## Requisitos en cada PC

- Windows 10 u 11
- [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) (en Win11 ya viene)

## Que incluye

| Capacidad | Como |
|---|---|
| App completa (igual que web) | Mismo React + API embebidos |
| Ventana de escritorio | pywebview + Edge WebView2 |
| Offline | SQLite en `%LOCALAPPDATA%\MEDGLOBAL` |
| Sync VPS | Boton "Sincronizar ahora" |
| Licencias por N PCs | Codigo firmado por `machine_id` |

## 1. Claves de licencia (admin, una vez)

```powershell
cd backend
.\venv_fresh\Scripts\python.exe generar_claves_licencia.py
```

## 2. Sync hacia el VPS

`backend/.env` (desde `desktop/env.escritorio.ejemplo`):

```env
SYNC_SERVER_URL=https://api.medglobal.erpgest.com.pe
SYNC_USERNAME=...
SYNC_PASSWORD=...
```

## 3. Construir el .exe de escritorio

```powershell
powershell -ExecutionPolicy Bypass -File desktop\build_escritorio.ps1
```

Salida: `MEDGLOBAL_Instalador_Offline_YYYYMMDD\MEDGLOBAL.exe`

## 4. Probar en desarrollo (sin empaquetar)

```powershell
cd backend
.\venv_fresh\Scripts\pip.exe install -r requirements-desktop.txt
$env:MEDGLOBAL_ESCRITORIO="1"
$env:MEDGLOBAL_LICENCIA_BYPASS="1"   # solo desarrollo
.\venv_fresh\Scripts\python.exe app_desktop.py
```

Se abre **ventana de escritorio**, no el navegador.

## 5. Emitir licencias

```powershell
.\venv_fresh\Scripts\python.exe generar_licencia.py `
  --cliente "Clinica Norte" --machine-id ID_DE_LA_PC --dias 365
```

## Uso

1. Doble clic en `MEDGLOBAL.exe`
2. Activar licencia → login → trabajar
3. **Sincronizar ahora** con el VPS
4. Cerrar la ventana = salir de la app

Log de diagnostico: `%LOCALAPPDATA%\MEDGLOBAL\medglobal_escritorio.log`
