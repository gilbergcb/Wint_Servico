"""Faturamento proprio da O.S. (Fase 4).

Regras de negocio + orquestracao: valida a O.S., calcula os totais e delega a
gravacao atomica (fatura + situacao Faturada) ao FaturaRepo. NAO gera movimento
de estoque/financeiro nativo (decisao: faturamento proprio).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.fatura_repo import FaturaRepo
from core.ordem_servico_repo import OrdemServicoRepo
from modelos.ordem_servico import SituacaoOS
from servicos.calculadora_os import calcular_totais


class FaturamentoError(Exception):
    """Erro de regra de negocio ao faturar uma O.S."""


@dataclass
class ResultadoFaturamento:
    cod_fatura: int
    num_os: int
    vl_total: Decimal
    mensagem: str = ""


class FaturadorOS:
    def __init__(self) -> None:
        self._os_repo = OrdemServicoRepo()
        self._fatura_repo = FaturaRepo()

    def faturar(self, num_os: int, usuario: str | None = None) -> ResultadoFaturamento:
        os_ = self._os_repo.obter(num_os)
        if os_ is None:
            raise FaturamentoError("O.S. nao encontrada.")
        if os_.situacao == SituacaoOS.CANCELADA:
            raise FaturamentoError("O.S. cancelada nao pode ser faturada.")
        if os_.situacao == SituacaoOS.FATURADA or self._fatura_repo.obter_por_os(num_os) is not None:
            raise FaturamentoError("O.S. ja faturada.")
        if not os_.servicos and not os_.produtos:
            raise FaturamentoError("O.S. sem itens para faturar.")

        vl_serv, vl_prod, vl_total = calcular_totais(os_.servicos, os_.produtos, os_.vl_desconto)
        if vl_total <= 0:
            raise FaturamentoError("Valor total da O.S. e zero; nada a faturar.")

        cod = self._fatura_repo.faturar(
            num_os,
            vl_servico=vl_serv,
            vl_produto=vl_prod,
            vl_desconto=os_.vl_desconto,
            vl_total=vl_total,
            usuario=usuario,
        )
        return ResultadoFaturamento(
            cod_fatura=cod, num_os=num_os, vl_total=vl_total,
            mensagem=f"O.S. {num_os} faturada (fatura {cod}). Total R$ {vl_total:,.2f}.",
        )
