# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH)  # backend/
PROJECT_ROOT = ROOT.parent

a = Analysis(
    ["run.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "frontend"), "frontend"),
        (str(PROJECT_ROOT / "assets"), "assets"),
    ],
    hiddenimports=[
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "win32com.client",
        "win32timezone",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DiskInfo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(PROJECT_ROOT / "assets" / "icon.ico"),
    # Embeds a requireAdministrator manifest -- Windows UAC-prompts on every
    # launch regardless of how it's started. Deliberate: several features
    # (writing the benchmark temp file to a protected drive root, later
    # TRIM/power-mode actions) need admin, and the decision is to elevate
    # once and predictably rather than per-feature. See
    # DiskInfo-project-plan.md's "Why DiskInfo runs elevated".
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DiskInfo",
)
