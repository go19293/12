# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 스펙 (Windows, onefile = 단일 실행파일).
#   빌드:  pyinstaller dia_mc.spec
# 결과물:  dist/dia_mc.exe  (이 파일 하나만 있으면 실행됨)
# 로고(dia_logo.png/ico)는 exe 안에 포함된다. 설정(last_settings.json)은
# exe 가 있는 폴더에 자동 저장된다.

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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='dia_mc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='dia_logo.ico',
)
