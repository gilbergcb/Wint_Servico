"""Parametros recebidos quando o executavel e chamado pelo menu do Winthor."""
from __future__ import annotations

import os
import sys

USUARIOWT: str = ""
SENHABD: str = ""
ALIASBD: str = ""
USUARIOBD: str = ""
CODROTINA: str = ""
CHAMADO_PELO_MENU: bool = False

# Código genérico da rotina no menu Winthor (provisório; trocar se/quando
# for atribuído um código oficial). Em runtime o CODROTINA vindo do menu
# (argv[5]) prevalece sobre este padrão.
COD_ROTINA_PADRAO = 9520
NOME_ROTINA = "Serviço / Oficina"
TITULO_ROTINA = "Ordem de Serviço - Oficina / Borracharia"


def carregar_parametros() -> None:
    """Carrega parametros posicionais do menu Winthor.

    Convencao esperada:
      app.exe USUARIOWT SENHABD ALIASBD USUARIOBD CODROTINA
    """
    global USUARIOWT, SENHABD, ALIASBD, USUARIOBD, CODROTINA, CHAMADO_PELO_MENU
    USUARIOWT = SENHABD = ALIASBD = USUARIOBD = CODROTINA = ""
    CHAMADO_PELO_MENU = False

    if len(sys.argv) >= 6:
        USUARIOWT = (sys.argv[1] or "").strip()
        SENHABD = (sys.argv[2] or "").strip()
        ALIASBD = (sys.argv[3] or "").strip()
        USUARIOBD = (sys.argv[4] or "").strip()
        CODROTINA = (sys.argv[5] or "").strip()

    USUARIOWT = USUARIOWT or (os.environ.get("USUARIOWT") or "").strip()
    SENHABD = SENHABD or (os.environ.get("SENHABD") or "").strip()
    ALIASBD = ALIASBD or (os.environ.get("ALIASBD") or "").strip()
    USUARIOBD = USUARIOBD or (os.environ.get("USUARIOBD") or "").strip()
    CODROTINA = CODROTINA or (os.environ.get("CODROTINA") or "").strip()
    CHAMADO_PELO_MENU = bool(ALIASBD and USUARIOBD)


def cod_rotina_atual() -> int:
    valor = (CODROTINA or "").strip()
    return int(valor) if valor.isdigit() else COD_ROTINA_PADRAO


def descricao_rotina() -> str:
    return f"{cod_rotina_atual()} {NOME_ROTINA}"

