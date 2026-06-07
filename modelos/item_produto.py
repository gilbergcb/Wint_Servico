"""Modelo de dominio: ItemProduto (peca/produto da O.S., tabela PCM_OS_PRODUTO)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ItemProduto:
    num_os_produto: int | None = None     # PCM_OS_PRODUTO.NUMOSPRODUTO (PK)
    num_os: int | None = None             # FK -> PCM_OS.NUMOS
    cod_prod: int | None = None           # FK logica -> PCPRODUT.CODPROD
    descricao: str = ""
    qtde: Decimal = Decimal("1")
    punit: Decimal = Decimal("0")
    vl_desconto: Decimal = Decimal("0")
    preco: Decimal = Decimal("0")         # total do item (QTDE * PUNIT - desconto)
    baixa_estoque: bool = True
