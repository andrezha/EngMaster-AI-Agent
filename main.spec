# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('resources', 'resources'), ('data', 'data'), ('assets', 'assets'), ('prompts.json', '.')],
    hiddenimports=['vocab_module', 'word_list_view', 'exam_module', 'utils', 'self_register_vocab_module', 'phrase_irregular_module', 'run_flull_exam', 'parsers.full_exam_specific_parsers', 'core.ai_logic'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
app = BUNDLE(
    exe,
    name='main.app',
    icon=None,
    bundle_identifier=None,
)
