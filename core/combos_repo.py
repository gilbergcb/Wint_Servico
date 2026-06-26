"""Listas para combos baseadas nas tabelas Winthor."""
from __future__ import annotations

from sqlalchemy import text

from core.db_engine import get_engine


class CombosRepo:
    """Acesso a listas curtas usadas em combos da UI."""

    def filiais(self) -> list[tuple[str, str]]:
        sql = """
            select codigo, codigo || ' - ' || nvl(fantasia, razaosocial) rotulo
              from pcfilial
             order by codigo
        """
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql)).fetchall()
        return [(str(cod), str(rotulo)) for cod, rotulo in rows]

    def cobrancas(self) -> list[tuple[str, str]]:
        sql = """
            select codcob, codcob || ' - ' || cobranca rotulo
              from pccob
             order by codcob
        """
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql)).fetchall()
        return [(str(cod), str(rotulo)) for cod, rotulo in rows]

    def planos_pagto(self) -> list[tuple[int, str]]:
        sql = """
            select codplpag, codplpag || ' - ' || descricao rotulo
              from pcplpag
             order by codplpag
        """
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql)).fetchall()
        return [(int(cod), str(rotulo)) for cod, rotulo in rows]
