import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPEC).resolve().parents[1]
BROWSER_BUNDLE = Path(os.environ["RESUME_WORKSHOP_BROWSER_BUNDLE"]).resolve()

datas = [
    (str(ROOT / "web"), "web"),
    (str(BROWSER_BUNDLE), "playwright-browsers"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "LICENSE.en.md"), "."),
    (str(ROOT / "PRIVACY.md"), "."),
    (str(ROOT / "README.md"), "."),
]
binaries = []
hiddenimports = []

for package in ("playwright", "rapidocr"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

analysis = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "coremltools",
        "easyocr",
        "llvmlite",
        "matplotlib",
        "numba",
        "openvino",
        "paddle",
        "paddleocr",
        "pandas",
        "patchright",
        "psycopg2",
        "PyQt5",
        "scipy",
        "tensorflow",
        "tensorrt",
        "torch",
        "torchvision",
    ],
    noarchive=False,
    optimize=0,
)
analysis.datas = [item for item in analysis.datas if not item[0].startswith("patchright")]
analysis.binaries = [item for item in analysis.binaries if not item[0].startswith("patchright")]
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ResumeWorkshop",
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
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ResumeWorkshop",
)

if sys.platform == "darwin":
    app = BUNDLE(
        bundle,
        name="Resume Workshop.app",
        icon=None,
        bundle_identifier="com.resumeworkshop.desktop",
        info_plist={
            "CFBundleDisplayName": "简历工坊",
            "CFBundleName": "Resume Workshop",
            "NSHighResolutionCapable": True,
        },
    )
