"""Calculo de totais da O.S. (sem dependencia de PyQt).

Soma o total dos itens de servico e de produto (campo ``preco`` ja liquido por
item) e aplica o desconto do cabecalho ao total geral. Tudo em ``Decimal``.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from modelos.item_produto import ItemProduto
from modelos.item_servico import ItemServico


def _to_dec(valor: object) -> Decimal:
    if valor is None:
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def somar_servicos(itens: Iterable[ItemServico]) -> Decimal:
    """Soma o ``preco`` (total liquido) de cada item de servico."""
    total = Decimal("0")
    for item in itens:
        total += _to_dec(item.preco)
    return total


def somar_produtos(itens: Iterable[ItemProduto]) -> Decimal:
    """Soma o ``preco`` (total liquido) de cada item de produto."""
    total = Decimal("0")
    for item in itens:
        total += _to_dec(item.preco)
    return total


def calcular_totais(
    servicos: Iterable[ItemServico],
    produtos: Iterable[ItemProduto],
    vl_desconto: object = Decimal("0"),
) -> tuple[Decimal, Decimal, Decimal]:
    """Devolve (vl_total_servico, vl_total_produto, vl_total).

    ``vl_total`` = total de servicos + total de produtos - desconto do cabecalho
    (nunca abaixo de zero).
    """
    total_servico = somar_servicos(servicos)
    total_produto = somar_produtos(produtos)
    desconto = _to_dec(vl_desconto)
    vl_total = total_servico + total_produto - desconto
    if vl_total < 0:
        vl_total = Decimal("0")
    return total_servico, total_produto, vl_total


def calcular_preco_item(qtde: object, punit: object, vl_desconto: object = Decimal("0")) -> Decimal:
    """Calcula o total liquido de um item: qtde * punit - desconto (>= 0)."""
    preco = _to_dec(qtde) * _to_dec(punit) - _to_dec(vl_desconto)
    return preco if preco > 0 else Decimal("0")
