# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for RainTranslater (slim)"""

LLAMA_KEEP = [
    'llama-server.exe', 'llama-server-impl.dll',
    'llama.dll', 'llama-common.dll',
    'ggml.dll', 'ggml-base.dll',
    'ggml-cpu-*.dll',
]

a = Analysis(
    ['main.py'],
    pathex=['D:/VibeCodingProject/RainTranslater'],
    binaries=[],
    datas=[
        ('ui/*', 'ui'),
        # Only include needed llama.cpp files
        ('bin/llama-server.exe', 'bin'),
        ('bin/llama-server-impl.dll', 'bin'),
        ('bin/llama.dll', 'bin'),
        ('bin/llama-common.dll', 'bin'),
        ('bin/ggml.dll', 'bin'),
        ('bin/ggml-base.dll', 'bin'),
        ('bin/ggml-cpu-*.dll', 'bin'),
    ],
    hiddenimports=[
        'flask', 'flask_cors', 'webview', 'requests',
        'huggingface_hub', 'backend',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2',
        'torch', 'tensorflow', 'jax', 'sympy', 'sqlalchemy',
        'IPython', 'jupyter', 'notebook', 'ipykernel',
        'pytest', 'sphinx', 'docutils',
        'transformers', 'tokenizers', 'safetensors',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RainTranslater',
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
    icon='app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RainTranslater',
)
