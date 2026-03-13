# -*- mode: python ; coding: utf-8 -*-
#
# BulkPDFGenerator_mac.spec  —  PyInstaller build config for Bulk PDF Generator (macOS)
#
# Build with:
#   pyinstaller BulkPDFGenerator_mac.spec --clean
#
# Output:  dist/Bulk PDF Generator.app

from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── PyMuPDF (fitz) ──────────────────────────────────────────────────────────
pymupdf_datas, pymupdf_binaries, pymupdf_hidden = collect_all('PyMuPDF')

try:
    fitz_datas, fitz_binaries, fitz_hidden = collect_all('fitz')
except Exception:
    fitz_datas, fitz_binaries, fitz_hidden = [], [], []

# ── ttkbootstrap ────────────────────────────────────────────────────────────
ttkbs_datas, ttkbs_binaries, ttkbs_hidden = collect_all('ttkbootstrap')

# ── openpyxl ────────────────────────────────────────────────────────────────
openpyxl_datas = collect_data_files('openpyxl')

# ── pandas ───────────────────────────────────────────────────────────────────
pandas_datas = collect_data_files('pandas')

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    ['pdf_generator.py'],
    pathex=[],
    binaries=pymupdf_binaries + fitz_binaries + ttkbs_binaries,
    datas=[
        ('getting_started.md', '.'),
        ('icon.png',           '.'),
        ('icon.ico',           '.'),
    ] + pymupdf_datas + fitz_datas + openpyxl_datas + pandas_datas + ttkbs_datas,
    hiddenimports=(
        pymupdf_hidden
        + fitz_hidden
        + ttkbs_hidden
        + [
            'openpyxl.cell._writer',
            'openpyxl.styles.stylesheet',
            'pandas._libs.tslibs.np_datetime',
            'pandas._libs.tslibs.nattype',
            'pandas._libs.tslibs.offsets',
            'pandas._libs.tslibs.timestamps',
            'tkinter',
            'tkinter.filedialog',
            'tkinter.messagebox',
            'tkinter.simpledialog',
            'tkinter.ttk',
            '_version',
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'IPython', 'jupyter', 'notebook',
        'pytest', 'setuptools', 'pip',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ── Executable (inside the .app bundle) ─────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Bulk PDF Generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.png',
)

# ── Collect into .app bundle ─────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Bulk PDF Generator',
)

# ── macOS .app bundle ────────────────────────────────────────────────────────
app = BUNDLE(
    coll,
    name='Bulk PDF Generator.app',
    icon='icon.png',
    bundle_identifier='com.antigravity.bulkpdfgenerator',
    info_plist={
        'CFBundleName': 'Bulk PDF Generator',
        'CFBundleDisplayName': 'Bulk PDF Generator',
        'CFBundleVersion': '2.5.0',
        'CFBundleShortVersionString': '2.5',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    },
)
