"""Modelo de dominio: ItemServico (item de O.S., tabela PCM_OS_SERVICO)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class ItemServico:
    num_os_servico: int | None = None     # PCM_OS_SERVICO.NUMOSSERVICO (PK)
    num_os: int | None = None             # FK -> PCM_OS.NUMOS
    cod_servico: int | None = None        # FK -> PCM_SERVICO.CODSERVICO
    cod_prod: int | None = None           # FK logica -> PCPRODUT.CODPROD
    cod_func: int | None = None           # tecnico (PCEMPR.MATRICULA)
    descricao: str = ""
    qtde: Decimal = Decimal("1")
    punit: Decimal = Decimal("0")
    preco: Decimal = Decimal("0")         # total do item
    vl_desconto: Decimal = Decimal("0")
    perc_comissao: Decimal = Decimal("0")
    comissao: Decimal = Decimal("0")
    reter_iss: bool = False
    perc_aliq_iss_retida: Decimal = Decimal("0")
    dt_inicio: datetime | None = None
    dt_final: datetime | None = None
    titulo_levantamento: str | None = None
    detalhe_levantamento: str | None = None
