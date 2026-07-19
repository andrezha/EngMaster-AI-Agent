# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('resources', 'resources'), ('data', 'data'), ('assets', 'assets'), ('prompts.json', '.')],
    hiddenimports=[
        'vocab_module',
        'word_list_view',
        'exam_module',
        'utils',
        'watermark_modes',
        'pdf_document_generator',
        'self_register_vocab_module',
        'phrase_irregular_module',
        'challenge_rounds',
        'challenge_history_dialog',
        'run_flull_exam',
        'parsers.full_exam_specific_parsers',
        'core.ai_logic',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tools', 'license_generator'],
    noarchive=False,
    optimize=0,
)

# QtGui collects the touch-oriented Qt Virtual Keyboard plugin on Windows.
# This desktop application uses normal keyboard input and has no QML/Qt Quick
# UI, so keeping that plugin forces roughly 13 MB of unused runtime libraries
# to be unpacked and scanned on every one-file launch.
_unused_qt_virtual_keyboard_files = {
    'pyside6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll',
    'pyside6/qt6virtualkeyboard.dll',
    'pyside6/qt6quick.dll',
    'pyside6/qt6qml.dll',
    'pyside6/qt6qmlmeta.dll',
    'pyside6/qt6qmlmodels.dll',
    'pyside6/qt6qmlworkerscript.dll',
}


def _without_unused_qt_virtual_keyboard(entries):
    return [
        entry for entry in entries
        if entry[0].replace('\\', '/').lower() not in _unused_qt_virtual_keyboard_files
    ]


a.binaries = _without_unused_qt_virtual_keyboard(a.binaries)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='高中-高考英语单词助手_v1.0',
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
