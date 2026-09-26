# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

photoshop_datas, photoshop_binaries, photoshop_hidden = collect_all("photoshopapi")
# PhotoshopAPI (pybind11) imports numpy.core.multiarray from C code, which
# PyInstaller cannot see. Without these the frozen app fails when saving PSD.
NUMPY_HIDDEN = ["numpy.core", "numpy.core.multiarray", "numpy.core._multiarray_umath"]

a = Analysis(
    ["png_black_converter/app.py"],
    pathex=[],
    binaries=photoshop_binaries,
    datas=photoshop_datas,
    hiddenimports=photoshop_hidden + NUMPY_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WhiteShift",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/app-icon.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
