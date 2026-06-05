import os
import platform
import site
from PyInstaller.utils.hooks import collect_all

SITEPKG = str(site.getsitepackages()[-1])

# Check for llama_cpp/lib presence to determine if we can include the binaries
llama_lib = os.path.exists(os.path.join(SITEPKG, "llama_cpp/lib"))

if platform.system() == "Darwin":
    webview_datas, webview_binaries, webview_hiddenimports = collect_all('webview')
else:
    webview_datas, webview_binaries, webview_hiddenimports = [], [], []

# Ensure the temp_checkpoints directory exists before building
if not os.path.exists(os.path.join("DashAI/back/user_models/temp_checkpoints")):
    os.makedirs("DashAI/back/user_models/temp_checkpoints")

a = Analysis(
    platform.system() == "Windows" and ["DashAI/__main__.py"] or ["DashAI/webview.py"],
    pathex=["."],
    binaries=(llama_lib and [(f"{SITEPKG}/llama_cpp/lib/*", "llama_cpp/lib")] or []) + webview_binaries,
    datas=[
        ("DashAI/__main__.py", "DashAI/__main__.py"),
        ("DashAI/alembic", "DashAI/alembic"),
        ("DashAI/front/build", "DashAI/front/build"),
        ("DashAI/back/static/images", "DashAI/back/static/images"),
        ("DashAI/back/types/inf/ptype/LR.sav", "DashAI/back/types/inf/ptype"),
        ("DashAI/back/types/inf/ptype/scaler.pkl", "DashAI/back/types/inf/ptype"),
        (
            "DashAI/back/user_models/temp_checkpoints",
            "DashAI/back/user_models/temp_checkpoints",
        ),
        ("DashAI/back/seeds", "DashAI/back/seeds"),
        (f"{SITEPKG}/transformers", "transformers"),
    ] + webview_datas,
    hiddenimports=webview_hiddenimports,
    hookspath=["hooks"],
    runtime_hooks=None,
    excludes=None,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="dashAI-launcher-cpu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    argv_emulation=True,
    icon="installer/dashAI.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="dashAI-launcher-cpu",
)

if platform.system() == "Darwin":
    app = BUNDLE(
        coll,
        name='dashAI.app',
        icon='installer/dashAI.icns',
        bundle_identifier='com.dashai.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
        },
    )
