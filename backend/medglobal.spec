# -*- mode: python ; coding: utf-8 -*-
"""Empaqueta MEDGLOBAL Escritorio como UN SOLO .exe (ventana nativa).

    cd backend && python -m PyInstaller medglobal.spec

Ventana de escritorio (pywebview + WebView2). No abre el navegador del usuario.
"""

import os as _os

_datas = [
    ('static', 'static'),
    ('medglobal-inicial.db', '.'),
    ('.env', '.'),
]
if _os.path.exists('licencia_publica.pem'):
    _datas.append(('licencia_publica.pem', '.'))

a = Analysis(
    ['app_desktop.py'],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=[
        # Paquetes propios (endpoints y logica de negocio).
        'routers',
        'servicios',
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'webview',
        'clr_loader',
        'pythonnet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest', 'matplotlib'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Sin consola = app de escritorio. Forzar consola de debug:
#   set MEDGLOBAL_BUILD_CONSOLA=1
_consola_debug = _os.environ.get('MEDGLOBAL_BUILD_CONSOLA', '').strip() in ('1', 'true', 'True')

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MEDGLOBAL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=_consola_debug,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
