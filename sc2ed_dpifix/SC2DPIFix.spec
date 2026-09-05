# -*- mode: python ; coding: utf-8 -*-
# SC2 银河编辑器 DPI 修复 —— 瘦身打包 spec
# 收集后过滤: 剔除 WebEngine(单个 195MB!)及一批用不到的 Qt 模块/qml 目录。
block_cipher = None

a = Analysis(
    ['sc2ed_dpifix_qml.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app.ico', '.'),
        ('VERSION', '.'),
        ('CREDITS.md', '.'),
        ('CHANGELOG.md', '.'),
        ('packages/hook', 'packages/hook'),
        ('packages/editor', 'packages/editor'),
    ],
    hiddenimports=[],
    excludes=[
        'tkinter', 'numpy', 'unittest', 'pydoc', 'doctest',
        'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineQuick', 'PySide6.QtWebChannel',
        'PySide6.QtMultimedia', 'PySide6.QtCharts', 'PySide6.QtSql',
        'PySide6.QtTest', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.Qt3DCore', 'PySide6.QtDataVisualization',
        'PySide6.QtBluetooth', 'PySide6.QtPositioning', 'PySide6.QtLocation',
    ],
    cipher=block_cipher, noarchive=False,
)

# 目标路径(小写、正斜杠)包含任一 token 即剔除
DROP = [
    'webengine', 'quick3d', 'qt63d', 'qt3d',
    'charts', 'datavisualization', 'multimedia', 'spatialaudio',
    'sqldrivers', 'qt6sql', 'qttest', 'qt6test',
    'location', 'positioning', 'websockets', 'webchannel',
    'bluetooth', 'nfc', 'sensors', 'serialport', 'serialbus',
    'remoteobjects', 'scxml', 'statemachine', 'texttospeech',
    'virtualkeyboard', 'designer', 'pdf', 'qmltooling',
    'opengl32sw', 'assetimporters', 'sceneparsers', 'geometryloaders',
    'quick/controls', 'quick/templates', 'quick/layouts', 'quick/dialogs',
    'quick/localstorage', 'quick/studio', 'quick/timeline', 'quick/scene',
    'labs/platform', 'labs/animation', 'labs/folderlistmodel',
    'labs/qmlmodels', 'labs/settings', 'labs/sharedimage', 'labs/wavefrontmesh',
    'translations',
]


def _drop(toc):
    out = []
    for entry in toc:
        name = entry[0]
        low = name.replace('\\', '/').lower()
        if any(t in low for t in DROP):
            continue
        out.append(entry)
    return TOC(out)


a.binaries = _drop(a.binaries)
a.datas = _drop(a.datas)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='SC2银河编辑器DPI修复',
    debug=False, bootloader_ignore_signals=False, strip=False,
    upx=False, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False,
    argv_emulation=False, target_arch=None, codesign_identity=None,
    entitlements_file=None, icon='app.ico',
)
