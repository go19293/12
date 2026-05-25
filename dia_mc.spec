# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 스펙 (Windows, onedir = 폴더 방식).
#   빌드:  pyinstaller dia_mc.spec
# 결과물:  dist/DIA_MC/dia_mc.exe  (+ _internal 폴더)
#   -> DIA_MC 폴더 전체를 옮겨서 안에 있는 dia_mc.exe 를 실행하면 된다.
# 로고(dia_logo.png/ico)는 _internal 안에 포함된다. 설정(last_settings.json)은
# dia_mc.exe 가 있는 폴더에 자동 저장된다.

block_cipher = None

a = Analysis(
    ['dia_mc.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dia_logo.png', '.'),
        ('dia_logo.ico', '.'),
    ],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon='dia_logo.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DIA_MC',
)
