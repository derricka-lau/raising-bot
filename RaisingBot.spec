# -*- mode: python ; coding: utf-8 -*-
import sys


a = Analysis(
    ['api.py'],
    pathex=[],
    binaries=[],
    datas=[
        # This section is crucial. It copies all necessary files into your app.
        ('raising-bot-web/dist', 'raising-bot-web/dist'), # Your React frontend
        ('main.py', '.'),                                 # The bot script
        ('config.py', '.'),                               # Your config logic
        ('signal_utils.py', '.'),                         # Your signal logic
    ],
    hiddenimports=[
        # --- LIBRARIES FROM requirements.txt ---
        'flask',
        'telethon',
        'ibapi',
        'pyaes',
        'rsa',
        'pyasn1',
        # --- END LIBRARIES ---
        'engineio.async_drivers.threading',
        'binascii',
        'socket',
        'asyncio',
        'queue',
        'threading',
        'json',
        'logging',
        'multiprocessing',
        'selectors',
        'ssl',
        'urllib',
        'encodings',
        'ctypes',
        'platform',
        'os',
        'sys',
        'time',
        'datetime',
        'traceback',
        'subprocess',
        'email',
        'collections',
        'math',
        'decimal',
        'zlib',
        'hashlib',
        # Add any other modules you use or see missing in error logs
    ],
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
    name='RaisingBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Show terminal for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RaisingBot',
)
# This part is for macOS only to create a clean .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='RaisingBot.app',
        icon=None, # You can add an .icns file here
        bundle_identifier='com.yourname.raisingbot', # Recommended to change this
    )
