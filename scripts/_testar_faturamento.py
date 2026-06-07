"""Teste e2e do faturamento proprio (Fase 4). Cria dados, fatura, valida e limpa."""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import parametros_winthor  # noqa: E402
from core.conexao_oracle import ConexaoOracle  # noqa: E402
from core.fatura_repo import FaturaRepo  # noqa: E402
from core.ordem_servico_repo import OrdemServicoRepo  # noqa: E402
from core.servico_repo import ServicoRepo  # noqa: E402
from modelos.item_servico import ItemServico  # noqa: E402
from modelos.ordem_servico import OrdemServico, SituacaoOS  # noqa: E402
from modelos.servico import Servico  # noqa: E402
from servicos.faturador_os import FaturadorOS, FaturamentoError  # noqa: E402

falhas: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("[OK]   " if cond else "[FALHA]") + " " + msg)
    if not cond:
        falhas.append(msg)


def main() -> int:
    parametros_winthor.carregar_parametros()
    conn = ConexaoOracle.instance().conectar()
    srv, osr = ServicoRepo(), OrdemServicoRepo()
    cod_servico = num_os = num_os_vazia = None
    try:
        cod_servico = srv.inserir(Servico(descricao="ZZ_FAT_SERV", preco_padrao=Decimal("50"), usuario_cad="TESTE"))
        num_os = osr.inserir(OrdemServico(cod_filial="1", situacao=SituacaoOS.CONCLUIDA, usuario_cad="TESTE"))
        osr.salvar_servicos(num_os, [ItemServico(
            cod_servico=cod_servico, descricao="ZZ_FAT_ITEM", qtde=Decimal("1"),
            punit=Decimal("50"), preco=Decimal("50"),
        )])

        res = FaturadorOS().faturar(num_os, usuario="TESTE")
        check(res.cod_fatura > 0 and res.vl_total == Decimal("50"), f"faturar -> fatura {res.cod_fatura}, total {res.vl_total}")
        check(osr.obter(num_os).situacao == SituacaoOS.FATURADA, "O.S. ficou FATURADA")
        check(FaturaRepo().obter_por_os(num_os) is not None, "PCM_OS_FATURA gravada")

        # nao deixa faturar de novo
        try:
            FaturadorOS().faturar(num_os)
            check(False, "double-faturar deveria falhar")
        except FaturamentoError:
            check(True, "double-faturar bloqueado (FaturamentoError)")

        # O.S. sem itens nao fatura
        num_os_vazia = osr.inserir(OrdemServico(cod_filial="1", situacao=SituacaoOS.ABERTA, usuario_cad="TESTE"))
        try:
            FaturadorOS().faturar(num_os_vazia)
            check(False, "O.S. sem itens deveria falhar")
        except FaturamentoError:
            check(True, "O.S. sem itens bloqueada (FaturamentoError)")
    finally:
        with conn.cursor() as cur:
            for n in (num_os, num_os_vazia):
                if n is not None:
                    cur.execute("DELETE FROM PCM_OS_FATURA WHERE NUMOS = :n", {"n": n})
                    cur.execute("DELETE FROM PCM_OS_SERVICO WHERE NUMOS = :n", {"n": n})
                    cur.execute("DELETE FROM PCM_OS WHERE NUMOS = :n", {"n": n})
            if cod_servico is not None:
                cur.execute("DELETE FROM PCM_SERVICO WHERE CODSERVICO = :c", {"c": cod_servico})
        conn.commit()
        print("       (registros de teste removidos)")

    print(f"\n{'=== FATURAMENTO OK ===' if not falhas else '=== FALHAS: ' + str(len(falhas)) + ' ==='}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
