"""Modelo de dominio: Servico (catalogo, tabela PCM_SERVICO)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Servico:
    cod_servico: int | None = None        # PCM_SERVICO.CODSERVICO (PK)
    cod_prod: int | None = None           # FK logica -> PCPRODUT.CODPROD (Opcao A)
    descricao: str = ""
    cod_filial: str | None = None
    preco_padrao: Decimal = Decimal("0")
    tempo_estimado_min: int | None = None
    reter_iss: bool = False
    perc_aliq_iss: Decimal = Decimal("0")
    ativo: bool = True
    obs: str | None = None
    dt_cadastro: datetime | None = None
    dt_alteracao: datetime | None = None
    usuario_cad: str | None = None
