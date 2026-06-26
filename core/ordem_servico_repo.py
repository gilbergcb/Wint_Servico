"""Repositorio de Ordem de Servico (PCM_OS / PCM_OS_SERVICO / PCM_OS_PRODUTO).

Acesso via SQLAlchemy Core (text()). PK por SEQ.NEXTVAL antes do INSERT
(deterministico; as triggers *_BI so atuam quando a PK vem NULL).

Estrategia dos itens (servicos/produtos): salvar_* faz DELETE de todos os
itens do NUMOS e reinsere a lista atual (padrao simples). Os itens NAO sao
gravados em ``inserir``/``atualizar`` (que cuidam so do cabecalho).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap
from modelos.item_produto import ItemProduto
from modelos.item_servico import ItemServico
from modelos.ordem_servico import OrdemServico, SituacaoOS

_COLS_OS = (
    "NUMOS, CODFILIAL, CODCLI, CODRCA, CODFUNCABERTURA, CODVEICULO, TIPOOS, "
    "SITUACAO, KM, CODCOB, CODPLPAG, VLTOTALSERVICO, VLTOTALPRODUTO, "
    "VLDESCONTO, VLTOTAL, DTCADASTRO, DTPREVTERM, DTFECHA, DTCANCEL, "
    "MOTIVOCANCEL, NUMTRANSVENDASERV, NUMTRANSVENDAPROD, NUMPED, OBS, USUARIOCAD, "
    "(SELECT c.CLIENTE FROM PCCLIENT c WHERE c.CODCLI = PCM_OS.CODCLI) CLIENTE_NOME, "
    "(SELECT v.PLACA FROM PCM_OS_VEICULO v WHERE v.CODVEICULO = PCM_OS.CODVEICULO) PLACA_VEICULO, "
    "(SELECT v.MARCA || '/' || v.MODELO || '/' || v.ANO "
    "FROM PCM_OS_VEICULO v WHERE v.CODVEICULO = PCM_OS.CODVEICULO) DESCRICAO_VEICULO"
)

_COLS_OS_SERVICO = (
    "NUMOSSERVICO, NUMOS, CODSERVICO, CODPROD, CODFUNC, DESCRICAO, QTDE, PUNIT, "
    "PRECO, VLDESCONTO, PERCCOMISSAO, COMISSAO, RETERISS, PERCALIQISSRETIDA, "
    "DTINICIO, DTFINAL, TITULOLEVANTAMENTO, DETALHELEVANTAMENTO"
)

_COLS_OS_PRODUTO = (
    "NUMOSPRODUTO, NUMOS, CODPROD, DESCRICAO, QTDE, PUNIT, VLDESCONTO, PRECO, "
    "BAIXAESTOQUE"
)


def _sn(valor: bool) -> str:
    return "S" if valor else "N"


def _to_dec(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")
    return Decimal(str(valor))


# --------------------------------------------------------------------- mapeadores
def _row_para_os(row: Any) -> OrdemServico:
    m = colmap(row)
    return OrdemServico(
        num_os=int(m["NUMOS"]),
        cod_filial=m["CODFILIAL"] or "",
        cod_cli=int(m["CODCLI"]) if m["CODCLI"] is not None else None,
        cliente_nome=m["CLIENTE_NOME"],
        cod_rca=int(m["CODRCA"]) if m["CODRCA"] is not None else None,
        cod_func_abertura=int(m["CODFUNCABERTURA"]) if m["CODFUNCABERTURA"] is not None else None,
        cod_veiculo=int(m["CODVEICULO"]) if m["CODVEICULO"] is not None else None,
        placa_veiculo=m["PLACA_VEICULO"],
        descricao_veiculo=m["DESCRICAO_VEICULO"],
        tipo_os=m["TIPOOS"],
        situacao=SituacaoOS(int(m["SITUACAO"])),
        km=int(m["KM"]) if m["KM"] is not None else None,
        cod_cob=m["CODCOB"],
        cod_plpag=int(m["CODPLPAG"]) if m["CODPLPAG"] is not None else None,
        vl_total_servico=_to_dec(m["VLTOTALSERVICO"]),
        vl_total_produto=_to_dec(m["VLTOTALPRODUTO"]),
        vl_desconto=_to_dec(m["VLDESCONTO"]),
        vl_total=_to_dec(m["VLTOTAL"]),
        dt_cadastro=m["DTCADASTRO"],
        dt_prev_term=m["DTPREVTERM"],
        dt_fecha=m["DTFECHA"],
        dt_cancel=m["DTCANCEL"],
        motivo_cancel=m["MOTIVOCANCEL"],
        num_trans_venda_serv=int(m["NUMTRANSVENDASERV"]) if m["NUMTRANSVENDASERV"] is not None else None,
        num_trans_venda_prod=int(m["NUMTRANSVENDAPROD"]) if m["NUMTRANSVENDAPROD"] is not None else None,
        num_ped=int(m["NUMPED"]) if m["NUMPED"] is not None else None,
        obs=m["OBS"],
        usuario_cad=m["USUARIOCAD"],
    )


def _row_para_item_servico(row: Any) -> ItemServico:
    m = colmap(row)
    return ItemServico(
        num_os_servico=int(m["NUMOSSERVICO"]),
        num_os=int(m["NUMOS"]),
        cod_servico=int(m["CODSERVICO"]) if m["CODSERVICO"] is not None else None,
        cod_prod=int(m["CODPROD"]) if m["CODPROD"] is not None else None,
        cod_func=int(m["CODFUNC"]) if m["CODFUNC"] is not None else None,
        descricao=m["DESCRICAO"] or "",
        qtde=_to_dec(m["QTDE"]),
        punit=_to_dec(m["PUNIT"]),
        preco=_to_dec(m["PRECO"]),
        vl_desconto=_to_dec(m["VLDESCONTO"]),
        perc_comissao=_to_dec(m["PERCCOMISSAO"]),
        comissao=_to_dec(m["COMISSAO"]),
        reter_iss=(m["RETERISS"] or "N") == "S",
        perc_aliq_iss_retida=_to_dec(m["PERCALIQISSRETIDA"]),
        dt_inicio=m["DTINICIO"],
        dt_final=m["DTFINAL"],
        titulo_levantamento=m["TITULOLEVANTAMENTO"],
        detalhe_levantamento=m["DETALHELEVANTAMENTO"],
    )


def _row_para_item_produto(row: Any) -> ItemProduto:
    m = colmap(row)
    return ItemProduto(
        num_os_produto=int(m["NUMOSPRODUTO"]),
        num_os=int(m["NUMOS"]),
        cod_prod=int(m["CODPROD"]) if m["CODPROD"] is not None else None,
        descricao=m["DESCRICAO"] or "",
        qtde=_to_dec(m["QTDE"]),
        punit=_to_dec(m["PUNIT"]),
        vl_desconto=_to_dec(m["VLDESCONTO"]),
        preco=_to_dec(m["PRECO"]),
        baixa_estoque=(m["BAIXAESTOQUE"] or "S") == "S",
    )


class OrdemServicoRepo:
    # ------------------------------------------------------------------ leitura
    def listar(
        self,
        *,
        filial: str | None = None,
        num_os: int | None = None,
        cod_cli: int | None = None,
        situacao: int | None = None,
        cod_func: int | None = None,
        dt_ini: date | datetime | None = None,
        dt_fim: date | datetime | None = None,
    ) -> list[OrdemServico]:
        """Lista cabecalhos de O.S. com WHERE dinamico.

        ``cod_func`` filtra O.S. que tenham algum item de servico do tecnico.
        """
        cond, params = self._filtros(
            filial=filial, num_os=num_os, cod_cli=cod_cli, situacao=situacao,
            cod_func=cod_func, dt_ini=dt_ini, dt_fim=dt_fim,
        )
        where = (" WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT {_COLS_OS} FROM PCM_OS{where} ORDER BY NUMOS DESC"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_os(r) for r in rows]

    @staticmethod
    def _filtros(
        *, filial=None, num_os=None, cod_cli=None, situacao=None,
        cod_func=None, dt_ini=None, dt_fim=None,
    ) -> tuple[list[str], dict[str, Any]]:
        cond: list[str] = []
        params: dict[str, Any] = {}
        if filial:
            cond.append("CODFILIAL = :filial")
            params["filial"] = filial
        if num_os is not None:
            cond.append("NUMOS = :numos")
            params["numos"] = num_os
        if cod_cli is not None:
            cond.append("CODCLI = :codcli")
            params["codcli"] = cod_cli
        if situacao is not None:
            cond.append("SITUACAO = :situacao")
            params["situacao"] = int(situacao)
        if cod_func is not None:
            cond.append(
                "EXISTS (SELECT 1 FROM PCM_OS_SERVICO s "
                "WHERE s.NUMOS = PCM_OS.NUMOS AND s.CODFUNC = :codfunc)"
            )
            params["codfunc"] = cod_func
        if dt_ini is not None:
            cond.append("DTCADASTRO >= :dtini")
            params["dtini"] = dt_ini
        if dt_fim is not None:
            cond.append("DTCADASTRO < :dtfim")
            params["dtfim"] = dt_fim
        return cond, params

    def contar_por_situacao(
        self, *, filial: str | None = None, cod_func: int | None = None,
        dt_ini: date | datetime | None = None, dt_fim: date | datetime | None = None,
    ) -> dict[int, int]:
        """Conta O.S. agrupadas por SITUACAO (para os KPIs do acompanhamento)."""
        cond, params = self._filtros(
            filial=filial, cod_func=cod_func, dt_ini=dt_ini, dt_fim=dt_fim,
        )
        where = (" WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT SITUACAO, COUNT(*) QTDE FROM PCM_OS{where} GROUP BY SITUACAO"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return {int(colmap(r)["SITUACAO"]): int(colmap(r)["QTDE"]) for r in rows}

    def obter(self, num_os: int) -> OrdemServico | None:
        """Carrega o cabecalho + itens de servico + itens de produto."""
        sql = f"SELECT {_COLS_OS} FROM PCM_OS WHERE NUMOS = :numos"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"numos": num_os}).fetchone()
        if not row:
            return None
        os_ = _row_para_os(row)
        os_.servicos = self.listar_servicos(num_os)
        os_.produtos = self.listar_produtos(num_os)
        return os_

    # ------------------------------------------------------------------ escrita (cabecalho)
    def proximo_num_os(self) -> int:
        with get_engine().connect() as cx:
            return int(cx.execute(text("SELECT PCM_OS_SEQ.NEXTVAL FROM DUAL")).scalar_one())

    def inserir(self, os_: OrdemServico) -> int:
        """Insere em PCM_OS (somente cabecalho) e retorna o NUMOS gerado."""
        with get_engine().begin() as cx:
            num_os = int(os_.num_os or cx.execute(text("SELECT PCM_OS_SEQ.NEXTVAL FROM DUAL")).scalar_one())
            cx.execute(
                text(
                    "INSERT INTO PCM_OS ("
                    "NUMOS, CODFILIAL, CODCLI, CODRCA, CODFUNCABERTURA, CODVEICULO, "
                    "TIPOOS, SITUACAO, KM, CODCOB, CODPLPAG, VLTOTALSERVICO, "
                    "VLTOTALPRODUTO, VLDESCONTO, VLTOTAL, DTCADASTRO, DTPREVTERM, "
                    "NUMPED, OBS, USUARIOCAD) VALUES ("
                    ":numos, :codfilial, :codcli, :codrca, :codfunc, :codveiculo, "
                    ":tipoos, :situacao, :km, :codcob, :codplpag, :vlserv, "
                    ":vlprod, :vldesc, :vltotal, SYSDATE, :dtprev, "
                    ":numped, :obs, :usuario)"
                ),
                self._params_cabecalho(os_, num_os),
            )
        return num_os

    def atualizar(self, os_: OrdemServico) -> None:
        if os_.num_os is None:
            raise ValueError("num_os obrigatorio para atualizar.")
        with get_engine().begin() as cx:
            cx.execute(
                text(
                    "UPDATE PCM_OS SET "
                    "CODFILIAL = :codfilial, CODCLI = :codcli, CODRCA = :codrca, "
                    "CODFUNCABERTURA = :codfunc, CODVEICULO = :codveiculo, TIPOOS = :tipoos, "
                    "SITUACAO = :situacao, KM = :km, CODCOB = :codcob, CODPLPAG = :codplpag, "
                    "VLTOTALSERVICO = :vlserv, VLTOTALPRODUTO = :vlprod, VLDESCONTO = :vldesc, "
                    "VLTOTAL = :vltotal, DTPREVTERM = :dtprev, NUMPED = :numped, "
                    "OBS = :obs, USUARIOCAD = :usuario "
                    "WHERE NUMOS = :numos"
                ),
                self._params_cabecalho(os_, os_.num_os),
            )

    def alterar_situacao(self, num_os: int, situacao: int) -> None:
        with get_engine().begin() as cx:
            cx.execute(
                text("UPDATE PCM_OS SET SITUACAO = :situacao WHERE NUMOS = :numos"),
                {"situacao": int(situacao), "numos": num_os},
            )

    def cancelar(self, num_os: int, motivo: str) -> None:
        with get_engine().begin() as cx:
            cx.execute(
                text(
                    "UPDATE PCM_OS SET SITUACAO = 3, DTCANCEL = SYSDATE, "
                    "MOTIVOCANCEL = :motivo WHERE NUMOS = :numos"
                ),
                {"motivo": motivo, "numos": num_os},
            )

    @staticmethod
    def _params_cabecalho(os_: OrdemServico, num_os: int) -> dict[str, Any]:
        return {
            "numos": num_os,
            "codfilial": os_.cod_filial,
            "codcli": os_.cod_cli,
            "codrca": os_.cod_rca,
            "codfunc": os_.cod_func_abertura,
            "codveiculo": os_.cod_veiculo,
            "tipoos": os_.tipo_os,
            "situacao": int(os_.situacao),
            "km": os_.km,
            "codcob": os_.cod_cob,
            "codplpag": os_.cod_plpag,
            "vlserv": os_.vl_total_servico,
            "vlprod": os_.vl_total_produto,
            "vldesc": os_.vl_desconto,
            "vltotal": os_.vl_total,
            "dtprev": os_.dt_prev_term,
            "numped": os_.num_ped,
            "obs": os_.obs,
            "usuario": os_.usuario_cad,
        }

    # --------------------------------------------- itens de servico (PCM_OS_SERVICO)
    def listar_servicos(self, num_os: int) -> list[ItemServico]:
        sql = (
            f"SELECT {_COLS_OS_SERVICO} FROM PCM_OS_SERVICO "
            "WHERE NUMOS = :numos ORDER BY NUMOSSERVICO"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), {"numos": num_os}).fetchall()
        return [_row_para_item_servico(r) for r in rows]

    def salvar_servicos(self, num_os: int, itens: list[ItemServico]) -> None:
        """DELETE dos itens do NUMOS + reinsere a lista atual (padrao simples)."""
        with get_engine().begin() as cx:
            cx.execute(text("DELETE FROM PCM_OS_SERVICO WHERE NUMOS = :numos"), {"numos": num_os})
            for item in itens:
                pk = int(cx.execute(text("SELECT PCM_OS_SERVICO_SEQ.NEXTVAL FROM DUAL")).scalar_one())
                cx.execute(
                    text(
                        "INSERT INTO PCM_OS_SERVICO ("
                        "NUMOSSERVICO, NUMOS, CODSERVICO, CODPROD, CODFUNC, DESCRICAO, QTDE, "
                        "PUNIT, PRECO, VLDESCONTO, PERCCOMISSAO, COMISSAO, RETERISS, "
                        "PERCALIQISSRETIDA, DTINICIO, DTFINAL, TITULOLEVANTAMENTO, "
                        "DETALHELEVANTAMENTO) VALUES ("
                        ":pk, :numos, :codservico, :codprod, :codfunc, :descricao, :qtde, "
                        ":punit, :preco, :vldesc, :perccom, :comissao, :reteriss, "
                        ":perciss, :dtinicio, :dtfinal, :titulo, :detalhe)"
                    ),
                    {
                        "pk": pk,
                        "numos": num_os,
                        "codservico": item.cod_servico,
                        "codprod": item.cod_prod,
                        "codfunc": item.cod_func,
                        "descricao": item.descricao,
                        "qtde": item.qtde,
                        "punit": item.punit,
                        "preco": item.preco,
                        "vldesc": item.vl_desconto,
                        "perccom": item.perc_comissao,
                        "comissao": item.comissao,
                        "reteriss": _sn(item.reter_iss),
                        "perciss": item.perc_aliq_iss_retida,
                        "dtinicio": item.dt_inicio,
                        "dtfinal": item.dt_final,
                        "titulo": item.titulo_levantamento,
                        "detalhe": item.detalhe_levantamento,
                    },
                )

    # --------------------------------------------- pecas/produtos (PCM_OS_PRODUTO)
    def listar_produtos(self, num_os: int) -> list[ItemProduto]:
        sql = (
            f"SELECT {_COLS_OS_PRODUTO} FROM PCM_OS_PRODUTO "
            "WHERE NUMOS = :numos ORDER BY NUMOSPRODUTO"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), {"numos": num_os}).fetchall()
        return [_row_para_item_produto(r) for r in rows]

    def salvar_produtos(self, num_os: int, itens: list[ItemProduto]) -> None:
        """DELETE dos itens do NUMOS + reinsere a lista atual (padrao simples)."""
        with get_engine().begin() as cx:
            cx.execute(text("DELETE FROM PCM_OS_PRODUTO WHERE NUMOS = :numos"), {"numos": num_os})
            for item in itens:
                pk = int(cx.execute(text("SELECT PCM_OS_PRODUTO_SEQ.NEXTVAL FROM DUAL")).scalar_one())
                cx.execute(
                    text(
                        "INSERT INTO PCM_OS_PRODUTO ("
                        "NUMOSPRODUTO, NUMOS, CODPROD, DESCRICAO, QTDE, PUNIT, "
                        "VLDESCONTO, PRECO, BAIXAESTOQUE) VALUES ("
                        ":pk, :numos, :codprod, :descricao, :qtde, :punit, "
                        ":vldesc, :preco, :baixa)"
                    ),
                    {
                        "pk": pk,
                        "numos": num_os,
                        "codprod": item.cod_prod,
                        "descricao": item.descricao,
                        "qtde": item.qtde,
                        "punit": item.punit,
                        "vldesc": item.vl_desconto,
                        "preco": item.preco,
                        "baixa": _sn(item.baixa_estoque),
                    },
                )
