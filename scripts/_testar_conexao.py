"""Teste de conexao thick contra o banco de teste, exercitando a stack real.

Valida: init do Instant Client (modo do .env) -> ConexaoOracle.conectar()
-> consulta de versao -> engine SQLAlchemy. Imprime diagnostico objetivo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

import parametros_winthor  # noqa: E402
from core.conexao_oracle import ConexaoOracle  # noqa: E402
from core.db_engine import get_engine  # noqa: E402


def main() -> int:
    parametros_winthor.carregar_parametros()
    conexao = ConexaoOracle.instance()
    print(f"Modo configurado : {conexao.modo}")
    print(f"Instant Client   : {os.environ.get('SVC_ORACLE_CLIENT_LIB_DIR') or '(PATH/registro)'}")
    print(f"DSN              : {os.environ.get('SVC_DB_DSN')}")

    try:
        conn = conexao.conectar()
    except Exception as exc:  # noqa: BLE001
        print(f"\n[FALHA] Conexao recusada:\n  {type(exc).__name__}: {exc}")
        return 1

    print(f"\n[OK] Conectado como {conexao.usuario} (origem: {conexao.origem})")

    with conn.cursor() as cur:
        cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
        print("Servidor         :", cur.fetchone()[0])
        cur.execute("SELECT USER FROM DUAL")
        print("Schema           :", cur.fetchone()[0])

    # valida o engine SQLAlchemy sobre a mesma conexao
    try:
        with get_engine().connect() as cx:
            val = cx.execute(text("SELECT 1 FROM DUAL")).scalar_one()
        print(f"[OK] Engine SQLAlchemy respondeu: SELECT 1 -> {val}")
    except Exception as exc:  # noqa: BLE001
        print(f"[FALHA] Engine SQLAlchemy:\n  {type(exc).__name__}: {exc}")
        return 1

    # verifica se a PCM_SERVICO ja existe (DDL aplicado?)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM all_tables WHERE table_name = 'PCM_SERVICO'")
        existe = cur.fetchone()[0] > 0
    print(f"Tabela PCM_SERVICO: {'JA EXISTE' if existe else 'AINDA NAO criada (rodar ddl_pcm.sql)'}")

    print("\n=== TESTE DE CONEXAO OK ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
