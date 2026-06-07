"""Teste CRUD ponta a ponta das Fases 1 e 2 contra o banco real.

Cria registros de teste em PCM_SERVICO / PCM_OS / itens, valida as operacoes
dos repositorios e REMOVE tudo ao final (test data nao fica no banco).
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import parametros_winthor  # noqa: E402
from core.conexao_oracle import ConexaoOracle  # noqa: E402
from core.ordem_servico_repo import OrdemServicoRepo  # noqa: E402
from core.servico_repo import ServicoRepo  # noqa: E402
from modelos.item_produto import ItemProduto  # noqa: E402
from modelos.item_servico import ItemServico  # noqa: E402
from modelos.ordem_servico import OrdemServico, SituacaoOS  # noqa: E402
from modelos.servico import Servico  # noqa: E402

falhas: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("[OK]   " if cond else "[FALHA]") + " " + msg)
    if not cond:
        falhas.append(msg)


def main() -> int:
    parametros_winthor.carregar_parametros()
    conn = ConexaoOracle.instance().conectar()
    srv = ServicoRepo()
    osr = OrdemServicoRepo()

    cod_servico = num_os = None
    try:
        # --------------------------------------------------- Fase 1: ServicoRepo
        cod_servico = srv.inserir(Servico(
            descricao="ZZ_TESTE_AUTOMATIZADO", preco_padrao=Decimal("10.50"),
            reter_iss=True, perc_aliq_iss=Decimal("5"), ativo=True, usuario_cad="TESTE",
        ))
        check(isinstance(cod_servico, int) and cod_servico > 0, f"ServicoRepo.inserir -> {cod_servico}")

        s = srv.obter(cod_servico)
        check(s is not None and s.descricao == "ZZ_TESTE_AUTOMATIZADO", "ServicoRepo.obter retorna o gravado")
        check(s.preco_padrao == Decimal("10.50") and s.reter_iss is True, "Servico: preco/reter_iss persistidos")

        achados = srv.listar(termo="ZZ_TESTE", ativo=True)
        check(any(x.cod_servico == cod_servico for x in achados), "ServicoRepo.listar encontra por descricao")

        s.preco_padrao = Decimal("12.00")
        srv.atualizar(s)
        check(srv.obter(cod_servico).preco_padrao == Decimal("12.00"), "ServicoRepo.atualizar altera preco")

        srv.inativar(cod_servico)
        check(srv.obter(cod_servico).ativo is False, "ServicoRepo.inativar marca ativo=N")

        # --------------------------------------- pega um CODPROD valido p/ produto
        with conn.cursor() as cur:
            cur.execute("SELECT CODPROD FROM PCPRODUT WHERE DTEXCLUSAO IS NULL AND ROWNUM = 1")
            row = cur.fetchone()
        cod_prod = int(row[0]) if row else None
        print(f"       (CODPROD de teste: {cod_prod})")

        # --------------------------------------------------- Fase 2: OrdemServico
        num_os = osr.inserir(OrdemServico(
            cod_filial="1", situacao=SituacaoOS.ABERTA, usuario_cad="TESTE",
            vl_total_servico=Decimal("21.00"), vl_total=Decimal("21.00"),
        ))
        check(isinstance(num_os, int) and num_os > 0, f"OrdemServicoRepo.inserir -> {num_os}")

        osr.salvar_servicos(num_os, [ItemServico(
            cod_servico=cod_servico, descricao="ZZ_ITEM_SERV", qtde=Decimal("2"),
            punit=Decimal("10.50"), preco=Decimal("21.00"), reter_iss=True,
        )])
        produtos = []
        if cod_prod is not None:
            produtos = [ItemProduto(cod_prod=cod_prod, descricao="ZZ_ITEM_PROD",
                                    qtde=Decimal("1"), punit=Decimal("5"), preco=Decimal("5"))]
            osr.salvar_produtos(num_os, produtos)

        carregado = osr.obter(num_os)
        check(carregado is not None, "OrdemServicoRepo.obter retorna a O.S.")
        check(len(carregado.servicos) == 1, f"O.S. carrega 1 item de servico (got {len(carregado.servicos)})")
        check(len(carregado.produtos) == len(produtos), f"O.S. carrega {len(produtos)} produto(s)")

        achadas = osr.listar(num_os=num_os)
        check(len(achadas) == 1 and achadas[0].num_os == num_os, "OrdemServicoRepo.listar por num_os")

        osr.alterar_situacao(num_os, int(SituacaoOS.EM_EXECUCAO))
        check(osr.obter(num_os).situacao == SituacaoOS.EM_EXECUCAO, "alterar_situacao -> EM_EXECUCAO")

        osr.cancelar(num_os, "teste automatizado")
        rec = osr.obter(num_os)
        check(rec.situacao == SituacaoOS.CANCELADA and rec.motivo_cancel == "teste automatizado",
              "cancelar -> CANCELADA + motivo")

    finally:
        # ------------------------------------------------------------- limpeza
        with conn.cursor() as cur:
            if num_os is not None:
                cur.execute("DELETE FROM PCM_OS_SERVICO WHERE NUMOS = :n", {"n": num_os})
                cur.execute("DELETE FROM PCM_OS_PRODUTO WHERE NUMOS = :n", {"n": num_os})
                cur.execute("DELETE FROM PCM_OS WHERE NUMOS = :n", {"n": num_os})
            if cod_servico is not None:
                cur.execute("DELETE FROM PCM_SERVICO WHERE CODSERVICO = :c", {"c": cod_servico})
        conn.commit()
        print("       (registros de teste removidos)")

    print(f"\n{'=== CRUD OK ===' if not falhas else '=== FALHAS: ' + str(len(falhas)) + ' ==='}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
