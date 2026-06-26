"""Modelo de dominio: OrdemServico (cabecalho, tabela PCM_OS)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import IntEnum

from .item_produto import ItemProduto
from .item_servico import ItemServico


class SituacaoOS(IntEnum):
    """Situacoes da Ordem de Servico (PCORDEMSERVICO.SITUACAO)."""

    ABERTA = 1
    EM_EXECUCAO = 2
    CANCELADA = 3
    CONCLUIDA = 4
    FATURADA = 5


@dataclass
class OrdemServico:
    num_os: int | None = None             # PCM_OS.NUMOS (PK)
    cod_filial: str = ""
    cod_cli: int | None = None            # FK logica -> PCCLIENT.CODCLI
    cliente_nome: str | None = None
    cod_rca: int | None = None
    cod_func_abertura: int | None = None  # FK logica -> PCEMPR.MATRICULA
    cod_veiculo: int | None = None        # FK -> PCM_OS_VEICULO.CODVEICULO
    placa_veiculo: str | None = None
    descricao_veiculo: str | None = None
    tipo_os: str | None = None
    situacao: SituacaoOS = SituacaoOS.ABERTA
    km: int | None = None
    cod_cob: str | None = None
    cod_plpag: int | None = None
    vl_total_servico: Decimal = Decimal("0")
    vl_total_produto: Decimal = Decimal("0")
    vl_desconto: Decimal = Decimal("0")
    vl_total: Decimal = Decimal("0")
    dt_cadastro: datetime | None = None
    dt_prev_term: datetime | None = None
    dt_fecha: datetime | None = None
    dt_cancel: datetime | None = None
    motivo_cancel: str | None = None
    num_trans_venda_serv: int | None = None
    num_trans_venda_prod: int | None = None
    num_ped: int | None = None
    obs: str | None = None
    usuario_cad: str | None = None
    # itens (carregados sob demanda pelo repositorio)
    servicos: list[ItemServico] = field(default_factory=list)
    produtos: list[ItemProduto] = field(default_factory=list)
