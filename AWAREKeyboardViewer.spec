# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for AWARE Keyboard Viewer.

Build with:
    pyinstaller AWAREKeyboardViewer.spec

The resulting binary will be in dist/AWAREKeyboardViewer.
Data directories (data/uploads, data/filtered, etc.) are created
at runtime next to the executable.
"""

import os

block_cipher = None

# Project root (where this .spec file lives)
ROOT = os.path.abspath('.')

a = Analysis(
    ['launcher.py'],
    pathex=[
        os.path.join(ROOT, 'src'),
    ],
    binaries=[],
    datas=[
        # Templates
        ('templates', 'templates'),
        # Static assets (CSS, JS, vendor libs)
        ('static', 'static'),
        # Source modules (app.py imports these at runtime)
        ('src', 'src'),
        # Typing performance analyzer subproject
        ('typing-performance-analyzer/performance_analyzer', 'typing-performance-analyzer/performance_analyzer'),
    ],
    hiddenimports=[
        'flask',
        'jinja2',
        'werkzeug',
        'pandas',
        'numpy',
        'sqlite3',
        'zoneinfo',
        'json',
        'hashlib',
        # src modules (imported dynamically via sys.path)
        'database',
        'segmentation',
        'utils',
        'analyzer',
        # typing-performance-analyzer modules
        'performance_analyzer',
        'performance_analyzer.typing_speed',
        'performance_analyzer.typing_speed._core',
        'performance_analyzer.error_rate',
        'performance_analyzer.error_rate._core',
        'performance_analyzer.typing_path',
        'performance_analyzer.typing_path._core',
        'performance_analyzer.typing_path._typingactivity',
        'performance_analyzer.typing_path.enum',
        'performance_analyzer.typing_path.util',
        'performance_analyzer.spellcheck',
        'performance_analyzer.utils',
        'performance_analyzer.utils.json',
        'performance_analyzer.utils.string',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
        'pytest',
    ],
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
    name='AWAREKeyboardViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # Show console for server log output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
