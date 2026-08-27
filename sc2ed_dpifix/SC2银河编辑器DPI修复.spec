# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['sc2ed_dpifix_qml.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.ico', '.'),
        ('VERSION', '.'),
        ('CREDITS.md', '.'),
        ('CHANGELOG.md', '.'),
        ('l10n/SC2EditorDependencyL10n.dll', 'l10n'),
        ('l10n/OfficialDependencyNames.tsv', 'l10n'),
        ('l10n/Editor', 'l10n/Editor'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel', 'PySide6.Qt3DCore', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PySide6.QtSql', 'PySide6.QtTest', 'tkinter', 'numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SC2银河编辑器DPI修复',
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
)
