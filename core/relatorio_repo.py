"""Repositorio de relatorios (consultas agregadas, somente leitura).

Cada metodo devolve (cabecalho, linhas): uma lista de titulos de coluna e uma
lista de linhas (cada linha = lista de valores ja formatados para exibicao).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap
from modelos.ordem_servico import SituacaoOS

_ROTULO_SITUACAO = {
    int(SituacaoOS.ABERTA): "Aberta",
    int(SituacaoOS.EM_EXECUCAO): "Em execucao",
    int(SituacaoOS.CONCLUIDA): "Concluida",
    int(SituacaoOS.FATURADA): "Faturada",
    int(SituacaoOS.CANCELADA): "Cancelada",
}

Periodo = tuple[date | datetime | None, date | datetime | None]


def _dec(v: Any) -> Decimal:
    return Decimal("0") if v is None else Decimal(str(v))


def _periodo_cond(dt_ini, dt_fim, coluna: str = "DTCADASTRO") -> tuple[str, dict]:
    cond, params = [], {}
    if dt_ini is not None:
        cond.append(f"{coluna} >= :dtini")
        params["dtini"] = dt_ini
    if dt_fim is not None:
        cond.append(f"{coluna} < :dtfim")
        params["dtfim"] = dt_fim
    where = (" WHERE " + " AND ".join(cond)) if cond else ""
    return where, params


class RelatorioRepo:
    def os_por_situacao(self, dt_ini=None, dt_fim=None) -> tuple[list[str], list[list]]:
        where, params = _periodo_cond(dt_ini, dt_fim)
        sql = (
            "SELECT SITUACAO, COUNT(*) QTDE, NVL(SUM(VLTOTAL),0) TOTAL "
            f"FROM PCM_OS{where} GROUP BY SITUACAO ORDER BY SITUACAO"
        )
        with get_engine().connect() as cx:
            rows = [colmap(r) for r in cx.execute(text(sql), params).fetchall()]
        linhas = [
            [_ROTULO_SITUACAO.get(int(m["SITUACAO"]), str(m["SITUACAO"])),
             int(m["QTDE"]), f"{_dec(m['TOTAL']):,.2f}"]
            for m in rows
        ]
        return ["Situacao", "Qtde O.S.", "Vl Total"], linhas

    def comissoes_por_tecnico(self, dt_ini=None, dt_fim=None) -> tuple[list[str], list[list]]:
        where, params = _periodo_cond(dt_ini, dt_fim, "o.DTCADASTRO")
        sql = (
            "SELECT s.CODFUNC, e.NOME, COUNT(*) ITENS, NVL(SUM(s.COMISSAO),0) COMISSAO "
            "FROM PCM_OS_SERVICO s JOIN PCM_OS o ON o.NUMOS = s.NUMOS "
            "LEFT JOIN PCEMPR e ON e.MATRICULA = s.CODFUNC"
            f"{where} GROUP BY s.CODFUNC, e.NOME ORDER BY COMISSAO DESC"
        )
        with get_engine().connect() as cx:
            rows = [colmap(r) for r in cx.execute(text(sql), params).fetchall()]
        linhas = [
            [m["CODFUNC"] if m["CODFUNC"] is not None else "-",
             m["NOME"] or "(sem tecnico)", int(m["ITENS"]), f"{_dec(m['COMISSAO']):,.2f}"]
            for m in rows
        ]
        return ["Matricula", "Tecnico", "Itens", "Comissao"], linhas

    def servicos_mais_executados(self, dt_ini=None, dt_fim=None, limite: int = 20) -> tuple[list[str], list[list]]:
        where, params = _periodo_cond(dt_ini, dt_fim, "o.DTCADASTRO")
        params["lim"] = limite
        sql = (
            "SELECT * FROM (SELECT s.CODSERVICO, MAX(srv.DESCRICAO) DESCRICAO, "
            "COUNT(*) QTDE, NVL(SUM(s.PRECO),0) TOTAL "
            "FROM PCM_OS_SERVICO s JOIN PCM_OS o ON o.NUMOS = s.NUMOS "
            "LEFT JOIN PCM_SERVICO srv ON srv.CODSERVICO = s.CODSERVICO"
            f"{where} GROUP BY s.CODSERVICO ORDER BY QTDE DESC) WHERE ROWNUM <= :lim"
        )
        with get_engine().connect() as cx:
            rows = [colmap(r) for r in cx.execute(text(sql), params).fetchall()]
        linhas = [
            [m["CODSERVICO"] if m["CODSERVICO"] is not None else "-",
             m["DESCRICAO"] or "(sem descricao)", int(m["QTDE"]), f"{_dec(m['TOTAL']):,.2f}"]
            for m in rows
        ]
        return ["Cod.Servico", "Descricao", "Qtde", "Vl Total"], linhas
