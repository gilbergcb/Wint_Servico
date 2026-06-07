"""Leitura de permissoes de acesso do Winthor (tabela nativa PCCONTROI).

PCCONTROI mapeia (CODROTINA, CODCONTROLE, CODUSUARIO) -> ACESSO ('S'/'N'):
para cada "controle" numerado de uma rotina, define se o usuario tem acesso.

O CODUSUARIO e a MATRICULA do funcionario (PCEMPR.MATRICULA). O login recebido
do menu (parametros_winthor.USUARIOWT) e resolvido para a matricula via
``PCEMPR.USUARIOBD = :login``.

Uso atual: controle ``CONTROLE_DISPENSA_PEDIDO`` -> usuario com ACESSO='S' pode
gravar a O.S. sem informar o pedido de venda, mesmo com a regra global ligada.
"""
from __future__ import annotations

from sqlalchemy import text

import parametros_winthor
from core.db_engine import get_engine
from core.sqlutil import colmap

# Controles (CODCONTROLE) definidos para a rotina de Servico/Oficina.
# Devem ser cadastrados/liberados no Winthor (PCCONTROI) para os usuarios.
CONTROLE_DISPENSA_PEDIDO = 1  # dispensa o pedido de venda obrigatorio na O.S.


class PermissaoRepo:
    def cod_usuario(self, login: str | None = None) -> int | None:
        """Resolve a MATRICULA do usuario a partir do login (USUARIOWT)."""
        login = (login if login is not None else parametros_winthor.USUARIOWT or "").strip()
        if not login:
            return None
        sql = "SELECT MATRICULA FROM PCEMPR WHERE USUARIOBD = :login"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"login": login}).fetchone()
        if not row:
            return None
        valor = colmap(row)["MATRICULA"]
        return int(valor) if valor is not None else None

    def tem_acesso(
        self,
        cod_controle: int,
        *,
        cod_rotina: int | None = None,
        cod_usuario: int | None = None,
    ) -> bool:
        """Devolve True se o usuario tem ACESSO='S' ao controle da rotina.

        Sem registro em PCCONTROI -> sem acesso (False).
        """
        if cod_usuario is None:
            cod_usuario = self.cod_usuario()
        if cod_usuario is None:
            return False
        if cod_rotina is None:
            cod_rotina = parametros_winthor.cod_rotina_atual()
        sql = (
            "SELECT ACESSO FROM PCCONTROI "
            "WHERE CODROTINA = :rot AND CODCONTROLE = :ctrl AND CODUSUARIO = :usu"
        )
        with get_engine().connect() as cx:
            row = cx.execute(
                text(sql),
                {"rot": int(cod_rotina), "ctrl": int(cod_controle), "usu": int(cod_usuario)},
            ).fetchone()
        if not row:
            return False
        return (colmap(row)["ACESSO"] or "N").upper() == "S"
