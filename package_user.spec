# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources/main_window.ui', 'resources'),
        ('resources/style.qss', 'resources'),
        ('assets/branding/yingsicheng_app_icon.png', 'assets/branding'),
        ('packaging/public_assets/editions/zhongkao/vocabulary.json', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/zhongkao/trial_vocabulary.json', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/zhongkao/phrases.json', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/zhongkao/irregular_verbs.json', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/zhongkao/scientific_memory_data.json', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/zhongkao/OPEN_ENGLISH_WORDNET_LICENSE.md', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/zhongkao/PRINCETON_WORDNET_LICENSE.txt', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/zhongkao/IPA_DICT_LICENSE.txt', 'assets/editions/zhongkao'),
        ('packaging/public_assets/editions/gaokao/vocabulary.json', 'assets/editions/gaokao'),
        ('packaging/public_assets/editions/gaokao/trial_vocabulary.json', 'assets/editions/gaokao'),
        ('packaging/public_assets/editions/gaokao/phrases.json', 'assets/editions/gaokao'),
        ('packaging/public_assets/editions/gaokao/irregular_verbs.json', 'assets/editions/gaokao'),
        ('packaging/public_assets/editions/gaokao/scientific_memory_data.json', 'assets/editions/gaokao'),
        ('packaging/public_assets/editions/gaokao/OPEN_ENGLISH_WORDNET_LICENSE.md', 'assets/editions/gaokao'),
        ('packaging/public_assets/editions/gaokao/PRINCETON_WORDNET_LICENSE.txt', 'assets/editions/gaokao'),
        ('packaging/public_assets/editions/gaokao/IPA_DICT_LICENSE.txt', 'assets/editions/gaokao'),
    ],
    hiddenimports=[
        'vocab_module',
        'word_list_view',
        'scientific_memory_view',
        'utils',
        'watermark_modes',
        'pdf_document_generator',
        'self_register_vocab_module',
        'phrase_irregular_module',
        'challenge_rounds',
        'challenge_history_dialog',
        'experience_guide',
        'guide_pages',
        'trial_center',
        'version_management',
        'purchase_config',
        'purchase_activation_panel',
        'ui_styles',
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
    name='英思成英语词汇复习软件 V1.0',
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
    icon='assets/branding/yingsicheng_icon.ico',
    version='assets/branding/yingsicheng_version_info.txt',
)
