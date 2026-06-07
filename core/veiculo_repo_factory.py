"""Selecao do backend de veiculos conforme o perfil do cliente (MODO_OPERACAO).

Espelha core/os_repo_factory.py para o cadastro de veiculo:
  - PCM     -> VeiculoRepo        (tabela propria PCM_OS_VEICULO).
  - WINTHOR -> VeiculoRepoWinthor (cascata nativa PCOSVEICULO* do modulo 35).

Ambos expoem a mesma interface (listar/obter/buscar_por_placa/inserir/atualizar),
entao a UI obtem o repositorio por aqui e troca de backend de forma transparente.
"""
from __future__ import annotations

from core.parametro_repo import MODO_WINTHOR, ParametroRepo
from core.veiculo_repo import VeiculoRepo
from core.veiculo_repo_winthor import VeiculoRepoWinthor


def obter_veiculo_repo(modo: str | None = None) -> VeiculoRepo | VeiculoRepoWinthor:
    """Devolve o repositorio de veiculo do perfil ativo."""
    if modo is None:
        modo = ParametroRepo().modo_operacao()
    if modo == MODO_WINTHOR:
        return VeiculoRepoWinthor()
    return VeiculoRepo()
