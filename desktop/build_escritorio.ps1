# Build del instalable de escritorio MEDGLOBAL
# NO toca el repositorio remoto ni el VPS. Solo genera artefactos locales.
#
# Requisitos:
#   - Python + backend/venv con requirements + pyinstaller
#   - Node.js + npm en frontend/
#   - backend/licencia_publica.pem (python generar_claves_licencia.py)
#   - backend/.env con SYNC_SERVER_URL / SYNC_USERNAME / SYNC_PASSWORD
#   - backend/medglobal-inicial.db (seed para PCs nuevas)
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File desktop\build_escritorio.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Py = Join-Path $Backend "venv_fresh\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    $Py = Join-Path $Backend "venv\Scripts\python.exe"
}

if (-not (Test-Path $Py)) {
    Write-Error "No se encontro $Py. Cree el venv e instale requirements.txt"
}

Write-Host "==> 0/4 Dependencias de escritorio (pywebview + pyinstaller)"
& $Py -m pip install -q pywebview "pyinstaller>=6.11.1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> 1/4 Frontend (API relativa vacia para offline)"
Push-Location $Frontend
$env:VITE_API_URL = ""
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "==> 2/4 Copiar dist a backend/static"
$Static = Join-Path $Backend "static"
if (Test-Path $Static) { Remove-Item $Static -Recurse -Force }
Copy-Item (Join-Path $Frontend "dist") $Static -Recurse

if (-not (Test-Path (Join-Path $Backend "licencia_publica.pem"))) {
    Write-Warning "Falta licencia_publica.pem. Ejecute: python generar_claves_licencia.py"
}
if (-not (Test-Path (Join-Path $Backend ".env"))) {
    Write-Warning "Falta backend/.env con la configuracion de sincronizacion al VPS."
}
if (-not (Test-Path (Join-Path $Backend "medglobal-inicial.db"))) {
    Write-Warning "Falta medglobal-inicial.db (base semilla)."
}

Write-Host "==> 3/4 PyInstaller (ventana de escritorio, sin consola)"
Push-Location $Backend
$env:MEDGLOBAL_BUILD_CONSOLA = $env:MEDGLOBAL_BUILD_CONSOLA
& $Py -m PyInstaller --noconfirm medglobal.spec
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

$Exe = Join-Path $Backend "dist\MEDGLOBAL.exe"
if (-not (Test-Path $Exe)) {
    Write-Error "No se genero $Exe"
}

Write-Host "==> 4/4 Carpeta de distribucion"
$Out = Join-Path $Root ("MEDGLOBAL_Instalador_Offline_" + (Get-Date -Format "yyyyMMdd"))
if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Path $Out | Out-Null
Copy-Item $Exe (Join-Path $Out "MEDGLOBAL.exe")
@'
MEDGLOBAL — Aplicacion de Escritorio
====================================

NO se abre en el navegador: es una ventana nativa de Windows.

Requisitos en la PC:
  - Windows 10/11
  - Microsoft Edge WebView2 Runtime (viene en Windows 11;
    en Windows 10 se instala solo o desde Microsoft si falta)

1. Ejecute MEDGLOBAL.exe (doble clic).
2. Activar licencia con el ID de equipo que muestra la pantalla.
3. Inicie sesion con su usuario habitual.
4. Use "Sincronizar ahora" para subir/bajar datos del servidor VPS
   (el mismo de la version web).

Cerrar la ventana cierra la aplicacion.

Datos y logs locales:
  %LOCALAPPDATA%\MEDGLOBAL\
    medglobal.db
    licencia.mglic
    sync_cursor.json
    respaldos\
    medglobal_escritorio.log

Configuracion de sync (opcional, .env al lado del .exe o en la carpeta de datos):
  SYNC_SERVER_URL=https://api.medglobal.erpgest.com.pe
  SYNC_USERNAME=...
  SYNC_PASSWORD=...
'@ | Set-Content -Path (Join-Path $Out "LEEME.txt") -Encoding UTF8

Write-Host ""
Write-Host "Listo: $Out\MEDGLOBAL.exe  (ventana de escritorio, no navegador)"
Write-Host "No suba esta carpeta a GitHub."
