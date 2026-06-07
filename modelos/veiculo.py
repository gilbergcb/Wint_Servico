"""Modelo de dominio: Veiculo (tabela PCM_OS_VEICULO)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Veiculo:
    cod_veiculo: int | None = None        # PCM_OS_VEICULO.CODVEICULO (PK)
    cod_cli: int | None = None            # FK logica -> PCCLIENT.CODCLI
    placa: str | None = None
    modelo: str | None = None
    marca: str | None = None
    ano: int | None = None
    combustivel: str | None = None
    motor: str | None = None
    cor: str | None = None
    chassi: str | None = None
    km_atual: int | None = None
    obs: str | None = None
    dt_cadastro: datetime | None = None
