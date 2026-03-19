# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = [('C:\\Users\\Admin\\Downloads\\projects\\python\\PythonExcelPostgres_v3\\PythonExcelPostgres\\app.py', '.'), ('services', 'services')]
binaries = []
hiddenimports = ['datetime.date', 'datetime.datetime', 'datetime.timedelta', 'dotenv.dotenv_values', 'glob', 'io.BytesIO', 'json', 'os', 'pandas', 'psycopg2.extras.RealDictCursor', 'requests', 'services.db.get_db_connection', 'services.execute_custom_query', 'services.execute_custom_query_with_uuids', 'services.execute_dml_with_uuids', 'services.execute_eac_fix', 'services.execute_hide_hts_entries', 'services.execute_hiv_enrollment_update', 'services.execute_lab_sync', 'services.execute_recall_sample', 'services.execute_tb_completion_update', 'services.execute_testing_setting_update', 'services.execute_update_test_result', 'services.execute_verification_query', 'services.insert_pmtct_batch', 'services.insert_pmtct_record', 'services.lab_results.execute_lab_sync_filtered', 'services.read_excel_file', 'services.read_uuids_from_excel', 'services.validate_db_credentials', 'streamlit', 'tempfile', 'zipfile', 'services', 'services.db', 'services.excel', 'services.verification', 'services.lab_results', 'services.pmtct', 'services.eac', 'services.pmtct_update', 'services.hts', 'services.lims', 'services.custom_query']
datas += copy_metadata('streamlit')
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\Admin\\AppData\\Local\\Temp\\tmpcl7gtvwh.py'],
    pathex=['.'],
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
    name='LAMISPLUS Gap Resolution Tools',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\Admin\\Downloads\\projects\\python\\PythonExcelPostgres_v3\\PythonExcelPostgres\\attached_assets\\logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LAMISPLUS Gap Resolution Tools',
)
