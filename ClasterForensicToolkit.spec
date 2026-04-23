# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('claster', 'claster'), ('models', 'models'), ('data', 'data'), ('config.yaml', '.')]
binaries = []
hiddenimports = ['tensorflow', 'tensorflow.keras', 'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'sklearn', 'sklearn.preprocessing', 'matplotlib', 'matplotlib.backends.backend_qt5agg', 'PIL', 'PIL.ExifTags', 'scapy', 'scapy.all', 'psutil', 'yaml', 'jinja2', 'reportlab', 'docx', 'cryptography', 'mutagen', 'pandas', 'numpy', 'h5py', 'claster', 'claster.core', 'claster.core.config', 'claster.core.database', 'claster.core.events', 'claster.core.exceptions', 'claster.core.fs_ops', 'claster.core.hashing', 'claster.core.logger', 'claster.core.plugins', 'claster.core.system', 'claster.core.utils', 'claster.core.evtx_parser', 'claster.disk', 'claster.disk.mft', 'claster.disk.usn', 'claster.disk.ads', 'claster.disk.anomalies', 'claster.disk.carving', 'claster.disk.slack', 'claster.disk.fat_exfat', 'claster.disk.ext4', 'claster.disk.imaging', 'claster.registry', 'claster.memory', 'claster.network', 'claster.stego', 'claster.crypto', 'claster.metadata', 'claster.browser', 'claster.pfi', 'claster.pfi.model', 'claster.pfi.dataset', 'claster.pfi.train', 'claster.pfi.inference', 'claster.pfi.monitor', 'claster.pfi.synthetic', 'claster.report', 'claster.gui', 'claster.gui.main_window', 'claster.gui.i18n', 'claster.gui.translations', 'claster.gui.widgets', 'claster.gui.widgets.dashboard', 'claster.gui.widgets.evidence_tree', 'claster.gui.widgets.task_runner', 'claster.gui.widgets.pfi_trainer', 'claster.gui.widgets.file_browser', 'claster.gui.widgets.hex_viewer', 'claster.gui.widgets.terminal', 'claster.gui.widgets.case_manager', 'claster.gui.widgets.evidence_viewer', 'claster.gui.widgets.help_browser', 'claster.gui.dialogs', 'claster.gui.dialogs.settings', 'claster.gui.dialogs.about', 'claster.gui.dialogs.plugin_manager', 'claster.gui.dialogs.report_dialog', 'claster.gui.dialogs.new_case', 'claster.gui.dialogs.function_args_dialog', 'claster.gui.workers', 'claster.gui.workers.analysis_worker', 'claster.cli']
tmp_ret = collect_all('tensorflow')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('matplotlib')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='ClasterForensicToolkit',
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
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ClasterForensicToolkit',
)
