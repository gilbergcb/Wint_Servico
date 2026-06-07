"""Utilitarios para resultados SQLAlchemy Core.

O dialeto Oracle do SQLAlchemy normaliza identificadores nao-citados para
minusculas nas chaves de ``row._mapping`` (ex.: CODSERVICO -> 'codservico').
``colmap`` devolve um dict com as chaves em MAIUSCULAS para que os mappers
acessem pelos nomes de coluna como escritos no SELECT.
"""
from __future__ import annotations

from typing import Any


def colmap(row: Any) -> dict[str, Any]:
    return {str(chave).upper(): valor for chave, valor in row._mapping.items()}
