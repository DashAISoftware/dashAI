import os
import platform
import site

SITEPKG = str(site.getsitepackages()[-1])

# Check for llama_cpp/lib presence to determine if we can include the binaries
llama_lib = os.path.exists(os.path.join(SITEPKG, "llama_cpp/lib"))

# Ensure the temp_checkpoints directory exists before building
if not os.path.exists(os.path.join("DashAI/back/user_models/temp_checkpoints")):
    os.makedirs("DashAI/back/user_models/temp_checkpoints")

a = Analysis(
    platform.system() == "Windows" and ["DashAI/__main__.py"] or ["DashAI/webview.py"],
    pathex=["."],
    binaries=llama_lib and [(f"{SITEPKG}/llama_cpp/lib/*", "llama_cpp/lib")] or [],
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
        (f"{SITEPKG}/transformers", "transformers"),
    ],
    hiddenimports=[],
    hookspath=["hooks"],
    runtime_hooks=None,
    excludes=None,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="DashAI-launcher-cpu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    argv_emulation=True,
)

if platform.system() == "Darwin":
    app = BUNDLE(
        coll,
        name='DashAI.app',
        icon=None, 
        bundle_identifier='com.dashai.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
        },
    )
else:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="DashAI-launcher-cpu",
    )
