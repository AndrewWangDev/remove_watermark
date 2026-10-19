# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files

entry_script = os.path.join('src', 'main.py')

datas = [('logo.png', '.'), ('logo.ico', '.')]
try:
    datas += collect_data_files('customtkinter')
except Exception:
    pass

# Helper dummy paths for Python 3.14 Tcl9 ZipFS compatibility if present
for helper in ['_tcl_data', '_tk_data', 'tcl', 'tk']:
    helper_path = os.path.join('build_helpers', helper)
    if os.path.exists(helper_path):
        datas.append((helper_path, helper))

a = Analysis(
    [entry_script],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'pandas', 'matplotlib', 'IPython'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

icon_choice = ['logo.ico'] if sys.platform == 'win32' and os.path.exists('logo.ico') else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_choice,
)
