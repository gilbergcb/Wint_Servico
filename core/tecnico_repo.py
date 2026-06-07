"""Repositorio de tecnicos (consulta a PCEMPR; MATRICULA = CODFUNC).

Tabela nativa - somente leitura. Ativo = DTDEMISSAO IS NULL.
Colunas nativas assumidas (TODO confirmar no banco quando voltar):
  MATRICULA, NOME, DTDEMISSAO.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap


def _row_para_dict(row: Any) -> dict:
    m = colmap(row)
    return {
        "matricula": int(m["MATRICULA"]),
        "nome": m["NOME"] or "",
    }


class TecnicoRepo:
    def listar_ativos(self) -> list[dict]:
        """Retorna tecnicos ativos de PCEMPR (matricula, nome)."""
        sql = (
            "SELECT MATRICULA, NOME FROM PCEMPR "
            "WHERE DTDEMISSAO IS NULL ORDER BY NOME"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql)).fetchall()
        return [_row_para_dict(r) for r in rows]

    def obter(self, matricula: int) -> dict | None:
        sql = "SELECT MATRICULA, NOME FROM PCEMPR WHERE MATRICULA = :mat"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"mat": matricula}).fetchone()
        return _row_para_dict(row) if row else None
