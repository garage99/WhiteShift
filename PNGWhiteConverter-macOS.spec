# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["png_black_converter/app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name="WhiteShift",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="assets/app-icon.icns",
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="WhiteShift",
)
app = BUNDLE(
    collection,
    name="WhiteShift.app",
    icon="assets/app-icon.icns",
    bundle_identifier="jp.pngtools.white-to-near-white",
    info_plist={
        "CFBundleDisplayName": "WhiteShift",
        "CFBundleName": "WhiteShift",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
)
