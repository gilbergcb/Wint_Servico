"""Aplica scripts/ddl_pcm.sql no banco configurado (.env), via stack real.

Wrapper de linha de comando sobre core.instalador_bd.aplicar_ddl (mesma logica
usada pela tela de Configuracao). Idempotente.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import parametros_winthor  # noqa: E402
from core.conexao_oracle import ConexaoOracle  # noqa: E402
from core.instalador_bd import aplicar_ddl  # noqa: E402


def main() -> int:
    parametros_winthor.carregar_parametros()
    conn = ConexaoOracle.instance().conectar()
    res = aplicar_ddl(conn)
    print("\n".join(res.linhas))
    print(f"\nResumo: {res.resumo}")
    return 1 if not res.ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
