"""Repositorio de setores (consulta a PCSETOR; usado para filtrar PCEMPR.CODSETOR)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap


def _row_para_dict(row: Any) -> dict:
    m = colmap(row)
    return {
        "cod_setor": int(m["CODSETOR"]),
        "nome": m["NOME"] or "",
    }


class SetorRepo:
    def buscar(self, termo: str = "", limite: int = 80) -> list[dict]:
        termo = (termo or "").strip()
        params: dict[str, Any] = {"limite": limite}
        filtros = ""
        if termo:
            if termo.isdigit():
                filtros = "WHERE CODSETOR = :cod_setor"
                params["cod_setor"] = int(termo)
            else:
                filtros = "WHERE UPPER(DESCRICAO) LIKE :termo"
                params["termo"] = f"%{termo.upper()}%"
        base = f"SELECT CODSETOR, DESCRICAO AS NOME FROM PCSETOR {filtros} ORDER BY DESCRICAO"
        sql = f"SELECT * FROM ({base}) WHERE ROWNUM <= :limite"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_dict(r) for r in rows]

    def obter(self, cod_setor: int) -> dict | None:
        sql = "SELECT CODSETOR, DESCRICAO AS NOME FROM PCSETOR WHERE CODSETOR = :cod_setor"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"cod_setor": cod_setor}).fetchone()
        return _row_para_dict(row) if row else None
