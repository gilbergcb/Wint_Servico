"""Controle simples de licenca por codigo da empresa WinThor (CODCLIPC)."""
from __future__ import annotations

from .conexao_oracle import ConexaoOracle
from .licenca_config import CODCLIPC_LIBERADOS


class LicencaRepo:
    def codclipc_atual(self) -> int | None:
        with ConexaoOracle.instance().conn.cursor() as cur:
            cur.execute("select codclipc from pcconsum")
            row = cur.fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def validar_empresa_liberada(self) -> int:
        codclipc = self.codclipc_atual()
        if codclipc not in CODCLIPC_LIBERADOS:
            raise RuntimeError(
                "Licenca nao liberada para esta empresa. "
                "Entre em contato para liberacao.\n\n"
                "WhatsApp: 99 991083193\n"
                "Instagram: gilbergcb"
            )
        return codclipc
