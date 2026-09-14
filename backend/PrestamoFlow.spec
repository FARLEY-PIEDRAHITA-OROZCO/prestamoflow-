# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para PrestamoFlow.
# Incluye el frontend compilado (frontend/dist) y empaqueta la app FastAPI+SQLite
# como un ejecutable de Windows sin consola (los datos van junto al exe).

from pathlib import Path

ROOT = Path(SPECPATH).resolve()
FRONTEND_DIST = ROOT.parent / "frontend" / "dist"
assert (FRONTEND_DIST / "index.html").exists(), (
    "frontend/dist no existe. Compila el frontend con 'npm run build' antes de empaquetar."
)

datas=[(str(FRONTEND_DIST), "frontend_dist")]
VERSION_FILE = ROOT / "version.txt"
if VERSION_FILE.exists():
    datas.append((str(VERSION_FILE), "."))

a = Analysis(
    ["serve.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "pytest", "unittest", "tkinter", "setuptools"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PrestamoFlow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PrestamoFlow",
)