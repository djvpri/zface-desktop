# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = []
datas += collect_data_files('insightface')
datas += collect_data_files('onnxruntime', include_py_files=True)

hidden_imports = [
    # Keyring Windows backend
    'keyring.backends',
    'keyring.backends.Windows',
    'keyring.core',
    # InsightFace
    'insightface',
    'insightface.model_zoo',
    'insightface.model_zoo.model_zoo',
    'insightface.utils',
    'insightface.utils.face_align',
    'insightface.data',
    # OnnxRuntime
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi._pybind_state',
    # PyQt6
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    # Misc
    'cv2',
    'numpy',
    'requests',
    'urllib3',
    'charset_normalizer',
    'certifi',
    'PIL',
    'PIL.Image',
]

excludes = [
    # Tidak dipakai di desktop app (CLIP hanya di server)
    'torch', 'torchvision', 'clip',
    # Tidak perlu
    'matplotlib', 'pandas', 'IPython',
    'tkinter', 'wx',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='ZFace',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll'],
    name='ZFace-Desktop',
)
