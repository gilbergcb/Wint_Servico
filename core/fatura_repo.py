"""Repositorio de faturamento proprio da O.S. (tabela PCM_OS_FATURA).

A gravacao da fatura e a mudanca de situacao da O.S. para Faturada (4) ocorrem
na MESMA transacao (atomico). Nao toca tabelas nativas (PCMOV/PCPREST).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap
from modelos.ordem_servico import SituacaoOS


class FaturaRepo:
    def obter_por_os(self, num_os: int) -> dict | None:
        sql = (
            "SELECT CODFATURA, NUMOS, DTFATURA, VLSERVICO, VLPRODUTO, "
            "VLDESCONTO, VLTOTAL, USUARIO FROM PCM_OS_FATURA WHERE NUMOS = :n"
        )
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"n": num_os}).fetchone()
        if not row:
            return None
        m = colmap(row)
        return {
            "cod_fatura": int(m["CODFATURA"]),
            "num_os": int(m["NUMOS"]),
            "dt_fatura": m["DTFATURA"],
            "vl_servico": m["VLSERVICO"],
            "vl_produto": m["VLPRODUTO"],
            "vl_desconto": m["VLDESCONTO"],
            "vl_total": m["VLTOTAL"],
            "usuario": m["USUARIO"],
        }

    def faturar(
        self,
        num_os: int,
        *,
        vl_servico: Decimal,
        vl_produto: Decimal,
        vl_desconto: Decimal,
        vl_total: Decimal,
        usuario: str | None,
    ) -> int:
        """Grava a fatura e marca a O.S. como Faturada na mesma transacao."""
        params: dict[str, Any] = {
            "numos": num_os,
            "vlserv": vl_servico,
            "vlprod": vl_produto,
            "vldesc": vl_desconto,
            "vltotal": vl_total,
            "usuario": usuario,
        }
        with get_engine().begin() as cx:
            cod = int(cx.execute(text("SELECT PCM_OS_FATURA_SEQ.NEXTVAL FROM DUAL")).scalar_one())
            params["cod"] = cod
            cx.execute(
                text(
                    "INSERT INTO PCM_OS_FATURA ("
                    "CODFATURA, NUMOS, DTFATURA, VLSERVICO, VLPRODUTO, VLDESCONTO, "
                    "VLTOTAL, USUARIO) VALUES ("
                    ":cod, :numos, SYSDATE, :vlserv, :vlprod, :vldesc, :vltotal, :usuario)"
                ),
                params,
            )
            cx.execute(
                text("UPDATE PCM_OS SET SITUACAO = :sit, DTFECHA = SYSDATE WHERE NUMOS = :numos"),
                {"sit": int(SituacaoOS.FATURADA), "numos": num_os},
            )
        return cod
