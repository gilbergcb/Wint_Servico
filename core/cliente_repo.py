"""Repositorio de clientes (consulta a PCCLIENT, tabela nativa - somente leitura).

LGPD: ao expor dados pessoais, prever log em PCLOGDADOSPESSOAS (rotina 3509).
Colunas nativas assumidas (TODO confirmar no banco quando voltar):
  CODCLI, CLIENTE (nome), FANTASIA, CGCENT (CNPJ/CPF).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap


def _row_para_dict(row: Any) -> dict:
    m = colmap(row)
    return {
        "cod_cli": int(m["CODCLI"]),
        "nome": m["CLIENTE"] or "",
        "cgc": m["CGCENT"],
    }


class ClienteRepo:
    def buscar(self, termo: str, limite: int = 50) -> list[dict]:
        """Busca clientes em PCCLIENT por CODCLI (se digito) ou nome (LIKE)."""
        termo = (termo or "").strip()
        params: dict[str, Any] = {"lim": limite}
        if termo.isdigit():
            cond = "CODCLI = :cod"
            params["cod"] = int(termo)
        else:
            cond = "UPPER(CLIENTE) LIKE :nome"
            params["nome"] = f"%{termo.upper()}%"
        sql = (
            "SELECT * FROM (SELECT CODCLI, CLIENTE, CGCENT FROM PCCLIENT "
            f"WHERE {cond} ORDER BY CLIENTE) WHERE ROWNUM <= :lim"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_dict(r) for r in rows]

    def obter(self, cod_cli: int) -> dict | None:
        sql = "SELECT CODCLI, CLIENTE, CGCENT FROM PCCLIENT WHERE CODCLI = :cod"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"cod": cod_cli}).fetchone()
        return _row_para_dict(row) if row else None
