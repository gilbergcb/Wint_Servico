# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para a rotina de Servico Winthor.

Build alvo: Windows 32-bit, single-file, sem console.
Codigo da rotina: 9520 (generico/provisorio). Para trocar, renomeie este
arquivo, ajuste APP_NAME abaixo e COD_ROTINA_PADRAO em parametros_winthor.py.

O executavel preserva os argumentos posicionais do menu WinThor:
  app.exe USUARIOWT SENHABD ALIASBD USUARIOBD CODROTINA
"""

from pathlib import Path


ROOT = Path(".").resolve()
APP_NAME = "PCWNT_9520"


def _coletar(diretorio: Path, padroes: tuple[str, ...], destino: str) -> list[tuple[str, str]]:
    arquivos: list[tuple[str, str]] = []
    if not diretorio.exists():
        return arquivos
    for item in diretorio.iterdir():
        if item.is_file() and any(item.match(padrao) for padrao in padroes):
            arquivos.append((str(item), destino))
    return arquivos


datas: list[tuple[str, str]] = []
datas += _coletar(ROOT / "assets", ("*.ico", "*.png", "*.svg"), "assets")
datas += _coletar(ROOT / "scripts", ("ddl_pcm.sql",), "scripts")  # DDL p/ tela Configuracao

hiddenimports = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtSvg",
    "PyQt6.sip",
    "oracledb",
    "sqlalchemy",
    "sqlalchemy.dialects.oracle",
    "sqlalchemy.dialects.oracle.oracledb",
    "dotenv",
    # Imports lazy usados pelo python-oracledb.
    "array",
    "asyncio",
    "base64",
    "ctypes",
    "getpass",
    "hashlib",
    "hmac",
    "secrets",
    "socket",
    "ssl",
    "uuid",
]

excludes = [
    "PyQt6.QtNetwork",
    "PyQt6.QtQml",
    "PyQt6.QtQuick",
    "PyQt6.QtSql",
    "PyQt6.QtTest",
    "PyQt6.QtMultimedia",
    "tkinter",
    "unittest",
    "pydoc_data",
]

a = Analysis(
    ["app.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=str(ROOT / "assets" / "app.ico"),
)
