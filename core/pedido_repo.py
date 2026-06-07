"""Repositorio de pedidos de venda (consulta a PCPEDC, tabela nativa - leitura).

Usado para vincular uma Ordem de Servico a um pedido de venda valido do Winthor
(MVP: associacao obrigatoria). Pedido valido = existe, NAO cancelado
(DTCANCEL IS NULL) e do mesmo cliente da O.S.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap


def _row_para_dict(row: Any) -> dict:
    m = colmap(row)
    return {
        "num_ped": int(m["NUMPED"]),
        "data": m["DATA"],
        "vl_total": m["VLTOTAL"],
    }


class PedidoRepo:
    def buscar(
        self,
        cod_cli: int,
        *,
        dt_ini: date | datetime | None = None,
        dt_fim: date | datetime | None = None,
        limite: int = 200,
    ) -> list[dict]:
        """Lista pedidos nao cancelados do cliente no periodo (DATA between).

        Espelha a regra: ``SELECT NUMPED FROM PCPEDC WHERE DTCANCEL IS NULL
        AND CODCLI = :codcli AND DATA BETWEEN :dtini AND :dtfim``.
        """
        cond = ["DTCANCEL IS NULL", "CODCLI = :codcli"]
        params: dict[str, Any] = {"codcli": int(cod_cli), "lim": limite}
        if dt_ini is not None:
            cond.append("DATA >= :dtini")
            params["dtini"] = dt_ini
        if dt_fim is not None:
            cond.append("DATA < :dtfim")
            params["dtfim"] = dt_fim
        where = " AND ".join(cond)
        sql = (
            "SELECT * FROM (SELECT NUMPED, DATA, VLTOTAL FROM PCPEDC "
            f"WHERE {where} ORDER BY NUMPED DESC) WHERE ROWNUM <= :lim"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_dict(r) for r in rows]

    def validar(self, num_ped: int, cod_cli: int) -> dict | None:
        """Devolve o pedido se for valido (existe, do cliente, nao cancelado)."""
        sql = (
            "SELECT NUMPED, DATA, VLTOTAL FROM PCPEDC "
            "WHERE NUMPED = :n AND CODCLI = :c AND DTCANCEL IS NULL"
        )
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"n": int(num_ped), "c": int(cod_cli)}).fetchone()
        return _row_para_dict(row) if row else None
