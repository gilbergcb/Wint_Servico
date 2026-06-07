"""Selecao do backend de persistencia da O.S. conforme o perfil do cliente.

MODO_OPERACAO (PCM_PARAM) decide onde a rotina grava:
  - PCM     -> tabelas proprias PCM_* (OrdemServicoRepo atual).
  - WINTHOR -> 100% nas tabelas nativas do modulo 35 (PCORDEMSERVICO/...).

Esta fabrica e o unico ponto que a UI/servicos devem usar para obter o
repositorio de O.S., de modo que a troca de perfil seja transparente. O backend
nativo (modulo 35) ainda esta em implementacao; ver docs/MAPEAMENTO_MODULO35.md.
"""
from __future__ import annotations

from core.ordem_servico_repo import OrdemServicoRepo
from core.ordem_servico_repo_winthor import OrdemServicoRepoWinthor
from core.parametro_repo import MODO_WINTHOR, ParametroRepo


class ModoNaoImplementadoError(Exception):
    """Perfil de operacao selecionado ainda nao tem backend implementado."""


def obter_os_repo(modo: str | None = None) -> OrdemServicoRepo | OrdemServicoRepoWinthor:
    """Devolve o repositorio de O.S. do perfil ativo.

    - PCM     -> OrdemServicoRepo (tabelas proprias PCM_*).
    - WINTHOR -> OrdemServicoRepoWinthor (tabelas nativas do modulo 35).

    Ambos expoem a mesma interface, entao a UI/servicos trocam de backend de
    forma transparente. O faturamento nativo (modulo 35) ainda e fase 4.
    """
    if modo is None:
        modo = ParametroRepo().modo_operacao()
    if modo == MODO_WINTHOR:
        return OrdemServicoRepoWinthor()
    return OrdemServicoRepo()
