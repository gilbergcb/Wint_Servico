"""Engine SQLAlchemy sobre a conexao oracledb ja configurada.

Reaproveita o ``ConexaoOracle`` (singleton) como ``creator`` do engine, de
modo que a sessao herde o modo (thin/thick), as credenciais resolvidas e o
NLS ja ajustado. Os repositorios usam SQLAlchemy Core (``text()``).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from .conexao_oracle import ConexaoOracle

log = logging.getLogger(__name__)

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Retorna (criando sob demanda) o engine SQLAlchemy do modulo.

    Usa ``creator`` apontando para a conexao singleton, evitando que o
    SQLAlchemy abra uma segunda conexao com configuracao divergente.

    ``StaticPool`` reaproveita a mesma conexao e NAO a fecha no checkin
    (ao contrario do ``NullPool``, que fecharia a conexao do ``ConexaoOracle``
    a cada ``engine.connect()``). O ciclo de vida segue com o ``ConexaoOracle``;
    a conexao so e liberada em ``dispose_engine`` / ``ConexaoOracle.fechar``.
    """
    global _engine
    if _engine is not None:
        return _engine

    conexao = ConexaoOracle.instance()

    def _creator():  # type: ignore[no-untyped-def]
        return conexao.conn

    _engine = create_engine(
        "oracle+oracledb://",
        creator=_creator,
        poolclass=StaticPool,
        future=True,
    )
    log.info("Engine SQLAlchemy inicializado (modo=%s).", conexao.modo)
    return _engine


def dispose_engine() -> None:
    """Libera o engine (sem fechar a conexao singleton subjacente)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
