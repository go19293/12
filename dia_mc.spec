# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 스펙 (Windows, onedir).
#   빌드:  pyinstaller dia_mc.spec
# 결과물:  dist/DIA_MC/dia_mc.exe  (+ _internal 폴더)
# 빌드 후 dia_logo.ico / dia_logo.png 를 dia_mc.exe 와 같은 폴더(dist/DIA_MC)에
# 복사해야 한다. (앱이 실행파일 위치에서 로고/설정 파일을 찾음)

block_cipher = None

a = Analysis(
    ['dia_mc.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'pygame',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='dia_mc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='dia_logo.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DIA_MC',
)
