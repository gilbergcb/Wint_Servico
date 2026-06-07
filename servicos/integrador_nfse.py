"""Subsistema de NFS-e: interface abstrata + stub.

Emissao propria com certificado A1 (.pfx). O provedor concreto (PyNFe,
ABRASF, ou gateway) sera implementado na Fase 5, apos definicao de
municipio/padrao. Persistencia em PCM_NFSE.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from decimal import Decimal
from enum import IntEnum


class SituacaoNFSe(IntEnum):
    PENDENTE = 0
    AUTORIZADA = 1
    REJEITADA = 2
    CANCELADA = 3


@dataclass
class DadosNFSe:
    """Dados de entrada para emissao da NFS-e a partir de uma O.S."""

    num_os: int
    cod_filial: str
    cod_municipio: str | None = None
    cod_cli: int | None = None
    vl_servico: Decimal = Decimal("0")
    vl_iss: Decimal = Decimal("0")
    vl_deducoes: Decimal = Decimal("0")
    discriminacao: str = ""


@dataclass
class ResultadoNFSe:
    situacao: SituacaoNFSe
    num_nfse: str | None = None
    cod_verificacao: str | None = None
    protocolo: str | None = None
    mensagem: str = ""
    xml_envio: str | None = None
    xml_retorno: str | None = None


class IntegradorNFSe(abc.ABC):
    """Interface de integracao com o emissor de NFS-e."""

    @abc.abstractmethod
    def emitir(self, dados: DadosNFSe) -> ResultadoNFSe:
        """Emite a NFS-e e retorna o resultado da prefeitura."""

    @abc.abstractmethod
    def cancelar(self, codigo: str, motivo: str) -> ResultadoNFSe:
        """Cancela uma NFS-e ja autorizada."""

    @abc.abstractmethod
    def consultar(self, protocolo: str) -> ResultadoNFSe:
        """Consulta a situacao de uma NFS-e pelo protocolo."""


class IntegradorNFSeStub(IntegradorNFSe):
    """Implementacao vazia (placeholder) ate a definicao do provedor."""

    def emitir(self, dados: DadosNFSe) -> ResultadoNFSe:
        raise NotImplementedError("Provedor de NFS-e nao configurado.")

    def cancelar(self, codigo: str, motivo: str) -> ResultadoNFSe:
        raise NotImplementedError("Provedor de NFS-e nao configurado.")

    def consultar(self, protocolo: str) -> ResultadoNFSe:
        raise NotImplementedError("Provedor de NFS-e nao configurado.")
