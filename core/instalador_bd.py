"""Instalador de objetos do banco (tabelas PCM_*, sequences, triggers, indices).

Le o script scripts/ddl_pcm.sql (em dev pela raiz do projeto; no .exe pelo
diretorio de bundle do PyInstaller) e executa cada statement de forma
idempotente: ORA-00955 (objeto ja existe) e tratado como "ja existe".

Usado tanto pela tela de Configuracao quanto pelo script scripts/_aplicar_ddl.py.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_PLSQL_INICIO = ("CREATE OR REPLACE TRIGGER", "CREATE TRIGGER", "BEGIN", "DECLARE")


def caminho_ddl() -> Path:
    """Resolve o caminho do ddl_pcm.sql em dev e empacotado (PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / "scripts" / "ddl_pcm.sql"


def dividir_statements(texto: str) -> list[str]:
    """Divide um script SQL*Plus em statements.

    Statements normais terminam em ';'; blocos PL/SQL (CREATE ... TRIGGER /
    BEGIN / DECLARE) terminam numa linha contendo apenas '/'.
    """
    statements: list[str] = []
    buf: list[str] = []
    is_plsql = False
    for raw in texto.splitlines():
        stripped = raw.strip()
        if not buf and (not stripped or stripped.startswith("--")):
            continue  # ignora comentarios/linhas em branco entre statements
        if not buf:
            is_plsql = stripped.upper().startswith(_PLSQL_INICIO)
        if stripped == "/":
            stmt = "\n".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf, is_plsql = [], False
            continue
        buf.append(raw)
        if not is_plsql and stripped.endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            buf = []
    resto = "\n".join(buf).strip()
    if resto:
        statements.append(resto)
    return statements


@dataclass
class ResultadoInstalacao:
    criados: int = 0
    existiam: int = 0
    falhas: int = 0
    linhas: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.falhas == 0

    @property
    def resumo(self) -> str:
        return f"{self.criados} criados, {self.existiam} ja existiam, {self.falhas} falhas."


def _rotulo(stmt: str) -> str:
    return " ".join(stmt.split()[:4])


def aplicar_ddl(conn: Any) -> ResultadoInstalacao:
    """Executa o DDL na conexao oracledb informada. Idempotente."""
    statements = dividir_statements(caminho_ddl().read_text(encoding="utf-8"))
    res = ResultadoInstalacao()
    for stmt in statements:
        rotulo = _rotulo(stmt)
        try:
            with conn.cursor() as cur:
                cur.execute(stmt)
            res.criados += 1
            res.linhas.append(f"[OK]     {rotulo}")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "ORA-00955" in msg:  # name is already used by an existing object
                res.existiam += 1
                res.linhas.append(f"[EXISTE] {rotulo}")
            else:
                res.falhas += 1
                res.linhas.append(f"[FALHA]  {rotulo} -> {msg.splitlines()[0]}")
    conn.commit()
    return res
