"""Repositorio de Ordem de Servico no backend NATIVO do modulo 35 do Winthor.

Drop-in da interface de ``core.ordem_servico_repo.OrdemServicoRepo``, porem
gravando/lendo nas tabelas nativas:
  - Cabecalho  -> PCORDEMSERVICO   (NUMOS via DFSEQ_PCORDEMSERVICO)
  - Servicos   -> PCORDEMSERVICOI  (NUMOSSERVICO via DFSEQ_PCORDEMSERVICOI)
  - Produtos   -> PCITEMSERVICO    (FILHO de PCORDEMSERVICOI; PK composta)

Decisoes/limitacoes da FASE 1 (CRUD; faturamento e fase 4):
  * Nao ha colunas de total no cabecalho nativo: os totais sao calculados a
    partir dos itens (subquery no listar; soma no obter).
  * No nativo as PECAS sao filhas de uma LINHA DE SERVICO (PCITEMSERVICO ->
    PCORDEMSERVICOI). Como nosso modelo trata produtos independentes, ao salvar
    vinculamos todas as pecas a PRIMEIRA linha de servico da O.S. Exige, por
    isso, ao menos 1 servico quando houver produtos.
  * PK composta de PCITEMSERVICO: usamos defaults CODEQUIPAMENTO=0, NUMLOTE='0',
    NUMSERIEEQUIP='0' (espelham a rotina nativa 3509; ver docs/TRACE_3509.md).
    Dois produtos com o MESMO CODPROD colidiriam na PK (limitacao conhecida;
    agregar antes).
  * TIPOOS nativo e numerico (-> PCTIPOORDEMSERVICO.CODTIPO); convertido de/para
    o nosso ``tipo_os`` (texto) quando numerico.
  * Desconto por item: o nativo TEM PERCDESC (percentual). Convertemos do nosso
    ``vl_desconto`` (valor absoluto) na gravacao e reconstruimos na leitura.
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

# Defaults para a PK composta de PCITEMSERVICO (sem controle de equip/lote/serie).
# Valores espelham a rotina nativa 3509 (NUMLOTE/NUMSERIEEQUIP='0', = default da
# coluna NUMSERIEEQUIP); ver docs/TRACE_3509.md (2o trace, O.S. nº 3).
_DEF_CODEQUIPAMENTO = 0
_DEF_NUMLOTE = "0"
_DEF_NUMSERIEEQUIP = "0"
_DEF_EQUIPAMENTO = "N"
_DEF_DEMONSTRACAO = "N"

# subqueries de total (cabecalho nativo nao tem VLTOTAL*)
_SUB_VLSERV = "(SELECT NVL(SUM(s.PRECO),0) FROM PCORDEMSERVICOI s WHERE s.NUMOS = o.NUMOS)"
_SUB_VLPROD = (
    "(SELECT NVL(SUM(p.QTDE*p.PVENDA*(1-NVL(p.PERCDESC,0)/100)),0) FROM PCITEMSERVICO p "
    "JOIN PCORDEMSERVICOI s2 ON p.NUMOSSERVICO = s2.NUMOSSERVICO WHERE s2.NUMOS = o.NUMOS)"
)

_COLS_OS = (
    "o.NUMOS, o.CODFILIAL, o.CODCLI, o.CODRCA, o.CODEMITENTE, o.CODOSVEICULO, "
    "o.TIPOOS, o.SITUACAO, o.KM, o.CODCOB, o.CODPLPAG, o.DTCADASTRO, o.DTPREVTERM, "
    "o.DTFECHA, o.DTCANCEL, o.MOTIVOCANCEL, o.NUMTRANSVENDASERV, o.NUMTRANSVENDAPROD, "
    "o.NUMPED, o.OBS, "
    f"{_SUB_VLSERV} VLSERV, {_SUB_VLPROD} VLPROD"
)


def _sn(valor: bool) -> str:
    return "S" if valor else "N"


def _to_dec(valor: Any) -> Decimal:
    return Decimal("0") if valor is None else Decimal(str(valor))


def _perc_desc(item: ItemProduto) -> Decimal:
    """Converte ``vl_desconto`` (valor absoluto) em PERCDESC (percentual nativo)."""
    bruto = _to_dec(item.qtde) * _to_dec(item.punit)
    if bruto <= 0:
        return Decimal("0")
    return (_to_dec(item.vl_desconto) / bruto) * Decimal("100")


def _situacao(valor: Any) -> SituacaoOS:
    try:
        return SituacaoOS(int(valor))
    except (ValueError, TypeError):
        return SituacaoOS.ABERTA


def _tipoos_para_nativo(tipo_os: str | None) -> int | None:
    if tipo_os is None:
        return None
    txt = str(tipo_os).strip()
    return int(txt) if txt.isdigit() else None


# --------------------------------------------------------------------- mapeadores
def _row_para_os(row: Any) -> OrdemServico:
    m = colmap(row)
    vl_serv = _to_dec(m["VLSERV"])
    vl_prod = _to_dec(m["VLPROD"])
    return OrdemServico(
        num_os=int(m["NUMOS"]),
        cod_filial=m["CODFILIAL"] or "",
        cod_cli=int(m["CODCLI"]) if m["CODCLI"] is not None else None,
        cod_rca=int(m["CODRCA"]) if m["CODRCA"] is not None else None,
        cod_func_abertura=int(m["CODEMITENTE"]) if m["CODEMITENTE"] is not None else None,
        cod_veiculo=int(m["CODOSVEICULO"]) if m["CODOSVEICULO"] is not None else None,
        tipo_os=str(int(m["TIPOOS"])) if m["TIPOOS"] is not None else None,
        situacao=_situacao(m["SITUACAO"]),
        km=int(m["KM"]) if m["KM"] is not None else None,
        cod_cob=m["CODCOB"],
        cod_plpag=int(m["CODPLPAG"]) if m["CODPLPAG"] is not None else None,
        vl_total_servico=vl_serv,
        vl_total_produto=vl_prod,
        vl_desconto=Decimal("0"),
        vl_total=vl_serv + vl_prod,
        dt_cadastro=m["DTCADASTRO"],
        dt_prev_term=m["DTPREVTERM"],
        dt_fecha=m["DTFECHA"],
        dt_cancel=m["DTCANCEL"],
        motivo_cancel=m["MOTIVOCANCEL"],
        num_trans_venda_serv=int(m["NUMTRANSVENDASERV"]) if m["NUMTRANSVENDASERV"] is not None else None,
        num_trans_venda_prod=int(m["NUMTRANSVENDAPROD"]) if m["NUMTRANSVENDAPROD"] is not None else None,
        num_ped=int(m["NUMPED"]) if m["NUMPED"] is not None else None,
        obs=m["OBS"],
    )


def _row_para_item_servico(row: Any) -> ItemServico:
    m = colmap(row)
    return ItemServico(
        num_os_servico=int(m["NUMOSSERVICO"]),
        num_os=int(m["NUMOS"]),
        cod_servico=None,  # nativo nao tem CODSERVICO proprio (servico = produto)
        cod_prod=int(m["CODPROD"]) if m["CODPROD"] is not None else None,
        cod_func=int(m["CODFUNC"]) if m["CODFUNC"] is not None else None,
        descricao=m["DESCRICAO"] or "",
        qtde=_to_dec(m["QTDE"]),
        punit=_to_dec(m["PUNIT"]),
        preco=_to_dec(m["PRECO"]),
        vl_desconto=Decimal("0"),
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
    qtde = _to_dec(m["QTDE"])
    pvenda = _to_dec(m["PVENDA"])
    bruto = qtde * pvenda
    vl_desconto = bruto * _to_dec(m.get("PERCDESC")) / Decimal("100")
    return ItemProduto(
        num_os_produto=None,  # nativo tem PK composta; sem PK simples
        num_os=int(m["NUMOS"]),
        cod_prod=int(m["CODPROD"]) if m["CODPROD"] is not None else None,
        descricao=m["DESCRICAO"] or "",
        qtde=qtde,
        punit=pvenda,
        vl_desconto=vl_desconto,
        preco=bruto - vl_desconto,
        baixa_estoque=True,
    )


class OrdemServicoRepoWinthor:
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
        cond, params = self._filtros(
            filial=filial, num_os=num_os, cod_cli=cod_cli, situacao=situacao,
            cod_func=cod_func, dt_ini=dt_ini, dt_fim=dt_fim,
        )
        where = (" WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT {_COLS_OS} FROM PCORDEMSERVICO o{where} ORDER BY o.NUMOS DESC"
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
            cond.append("o.CODFILIAL = :filial")
            params["filial"] = filial
        if num_os is not None:
            cond.append("o.NUMOS = :numos")
            params["numos"] = num_os
        if cod_cli is not None:
            cond.append("o.CODCLI = :codcli")
            params["codcli"] = cod_cli
        if situacao is not None:
            cond.append("o.SITUACAO = :situacao")
            params["situacao"] = int(situacao)
        if cod_func is not None:
            cond.append(
                "EXISTS (SELECT 1 FROM PCORDEMSERVICOI s "
                "WHERE s.NUMOS = o.NUMOS AND s.CODFUNC = :codfunc)"
            )
            params["codfunc"] = cod_func
        if dt_ini is not None:
            cond.append("o.DTCADASTRO >= :dtini")
            params["dtini"] = dt_ini
        if dt_fim is not None:
            cond.append("o.DTCADASTRO < :dtfim")
            params["dtfim"] = dt_fim
        return cond, params

    def contar_por_situacao(
        self, *, filial: str | None = None, cod_func: int | None = None,
        dt_ini: date | datetime | None = None, dt_fim: date | datetime | None = None,
    ) -> dict[int, int]:
        cond, params = self._filtros(
            filial=filial, cod_func=cod_func, dt_ini=dt_ini, dt_fim=dt_fim,
        )
        where = (" WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT o.SITUACAO, COUNT(*) QTDE FROM PCORDEMSERVICO o{where} GROUP BY o.SITUACAO"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return {int(colmap(r)["SITUACAO"]): int(colmap(r)["QTDE"]) for r in rows}

    def obter(self, num_os: int) -> OrdemServico | None:
        sql = f"SELECT {_COLS_OS} FROM PCORDEMSERVICO o WHERE o.NUMOS = :numos"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"numos": num_os}).fetchone()
        if not row:
            return None
        os_ = _row_para_os(row)
        os_.servicos = self.listar_servicos(num_os)
        os_.produtos = self.listar_produtos(num_os)
        return os_

    # ------------------------------------------------------------- escrita (cabecalho)
    def inserir(self, os_: OrdemServico) -> int:
        with get_engine().begin() as cx:
            num_os = int(cx.execute(text("SELECT DFSEQ_PCORDEMSERVICO.NEXTVAL FROM DUAL")).scalar_one())
            cx.execute(
                text(
                    "INSERT INTO PCORDEMSERVICO ("
                    "NUMOS, CODFILIAL, CODCLI, CODRCA, CODEMITENTE, CODOSVEICULO, "
                    "TIPOOS, SITUACAO, KM, CODCOB, CODPLPAG, DTCADASTRO, DTPREVTERM, "
                    "NUMPED, OBS) VALUES ("
                    ":numos, :codfilial, :codcli, :codrca, :codemit, :codveiculo, "
                    ":tipoos, :situacao, :km, :codcob, :codplpag, SYSDATE, :dtprev, "
                    ":numped, :obs)"
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
                    "UPDATE PCORDEMSERVICO SET "
                    "CODFILIAL = :codfilial, CODCLI = :codcli, CODRCA = :codrca, "
                    "CODEMITENTE = :codemit, CODOSVEICULO = :codveiculo, TIPOOS = :tipoos, "
                    "SITUACAO = :situacao, KM = :km, CODCOB = :codcob, CODPLPAG = :codplpag, "
                    "DTPREVTERM = :dtprev, NUMPED = :numped, OBS = :obs "
                    "WHERE NUMOS = :numos"
                ),
                self._params_cabecalho(os_, os_.num_os),
            )

    def alterar_situacao(self, num_os: int, situacao: int) -> None:
        with get_engine().begin() as cx:
            cx.execute(
                text("UPDATE PCORDEMSERVICO SET SITUACAO = :situacao WHERE NUMOS = :numos"),
                {"situacao": int(situacao), "numos": num_os},
            )

    def cancelar(self, num_os: int, motivo: str) -> None:
        with get_engine().begin() as cx:
            cx.execute(
                text(
                    "UPDATE PCORDEMSERVICO SET SITUACAO = 5, DTCANCEL = SYSDATE, "
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
            "codemit": os_.cod_func_abertura,
            "codveiculo": os_.cod_veiculo,
            "tipoos": _tipoos_para_nativo(os_.tipo_os),
            "situacao": int(os_.situacao),
            "km": os_.km,
            "codcob": os_.cod_cob,
            "codplpag": os_.cod_plpag,
            "dtprev": os_.dt_prev_term,
            "numped": os_.num_ped,
            "obs": os_.obs,
        }

    # --------------------------------------------- itens de servico (PCORDEMSERVICOI)
    def listar_servicos(self, num_os: int) -> list[ItemServico]:
        sql = (
            "SELECT s.NUMOSSERVICO, s.NUMOS, s.CODPROD, s.CODFUNC, s.QTDE, s.PUNIT, "
            "s.PRECO, s.RETERISS, s.PERCALIQISSRETIDA, s.COMISSAO, s.PERCCOMISSAO, "
            "s.DTINICIO, s.DTFINAL, s.TITULOLEVANTAMENTO, s.DETALHELEVANTAMENTO, "
            "p.DESCRICAO "
            "FROM PCORDEMSERVICOI s LEFT JOIN PCPRODUT p ON p.CODPROD = s.CODPROD "
            "WHERE s.NUMOS = :numos ORDER BY s.NUMOSSERVICO"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), {"numos": num_os}).fetchall()
        return [_row_para_item_servico(r) for r in rows]

    def salvar_servicos(self, num_os: int, itens: list[ItemServico]) -> None:
        """Reescreve as linhas de servico da O.S. (apaga pecas filhas antes, FK)."""
        with get_engine().begin() as cx:
            self._apagar_itens(cx, num_os)
            for item in itens:
                pk = int(cx.execute(text("SELECT DFSEQ_PCORDEMSERVICOI.NEXTVAL FROM DUAL")).scalar_one())
                cx.execute(
                    text(
                        "INSERT INTO PCORDEMSERVICOI ("
                        "NUMOSSERVICO, NUMOS, CODPROD, CODFUNC, QTDE, PUNIT, PRECO, "
                        "RETERISS, PERCALIQISSRETIDA, COMISSAO, PERCCOMISSAO, DTINICIO, "
                        "DTFINAL, TITULOLEVANTAMENTO, DETALHELEVANTAMENTO) VALUES ("
                        ":pk, :numos, :codprod, :codfunc, :qtde, :punit, :preco, "
                        ":reteriss, :perciss, :comissao, :perccom, NVL(:dtinicio, SYSDATE), "
                        ":dtfinal, :titulo, :detalhe)"
                    ),
                    {
                        "pk": pk,
                        "numos": num_os,
                        "codprod": item.cod_prod,
                        "codfunc": item.cod_func,
                        "qtde": item.qtde,
                        "punit": item.punit,
                        "preco": item.preco,
                        "reteriss": _sn(item.reter_iss),
                        "perciss": item.perc_aliq_iss_retida,
                        "comissao": item.comissao,
                        "perccom": item.perc_comissao,
                        "dtinicio": item.dt_inicio,
                        "dtfinal": item.dt_final,
                        "titulo": item.titulo_levantamento,
                        "detalhe": item.detalhe_levantamento,
                    },
                )

    # --------------------------------------------- pecas/produtos (PCITEMSERVICO)
    def listar_produtos(self, num_os: int) -> list[ItemProduto]:
        sql = (
            "SELECT s.NUMOS, i.CODPROD, i.QTDE, i.PVENDA, i.PERCDESC, p.DESCRICAO "
            "FROM PCITEMSERVICO i "
            "JOIN PCORDEMSERVICOI s ON s.NUMOSSERVICO = i.NUMOSSERVICO "
            "LEFT JOIN PCPRODUT p ON p.CODPROD = i.CODPROD "
            "WHERE s.NUMOS = :numos ORDER BY i.NUMOSSERVICO, i.CODPROD"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), {"numos": num_os}).fetchall()
        return [_row_para_item_produto(r) for r in rows]

    def salvar_produtos(self, num_os: int, itens: list[ItemProduto]) -> None:
        """Vincula as pecas a primeira linha de servico da O.S. (modelo nativo).

        Exige >= 1 servico quando houver produtos (PCITEMSERVICO e filha de
        PCORDEMSERVICOI). Apaga as pecas atuais e reinsere a lista.
        """
        with get_engine().begin() as cx:
            row = cx.execute(
                text(
                    "SELECT MIN(s.NUMOSSERVICO) AS NOS, MAX(o.CODFILIAL) AS CODFILIAL "
                    "FROM PCORDEMSERVICOI s JOIN PCORDEMSERVICO o ON o.NUMOS = s.NUMOS "
                    "WHERE s.NUMOS = :numos"
                ),
                {"numos": num_os},
            ).one_or_none()
            cab = colmap(row) if row is not None else {}
            num_os_servico = cab.get("NOS")
            cod_filial = cab.get("CODFILIAL")
            cx.execute(
                text(
                    "DELETE FROM PCITEMSERVICO WHERE NUMOSSERVICO IN "
                    "(SELECT NUMOSSERVICO FROM PCORDEMSERVICOI WHERE NUMOS = :numos)"
                ),
                {"numos": num_os},
            )
            if not itens:
                return
            if num_os_servico is None:
                raise ValueError(
                    "No modo Winthor as pecas sao vinculadas a uma linha de servico: "
                    "inclua ao menos um servico na O.S. antes de adicionar produtos."
                )
            num_os_servico = int(num_os_servico)
            for item in itens:
                # Colunas espelham a rotina nativa 3509 (ver docs/TRACE_3509.md).
                # PERCDESC e percentual; convertemos do vl_desconto (valor absoluto).
                cx.execute(
                    text(
                        "INSERT INTO PCITEMSERVICO ("
                        "NUMOSSERVICO, CODPROD, QTDE, PVENDA, PTABELA, PERCDESC, "
                        "DEMONSTRACAO, CODFILIALRETIRA, CODEQUIPAMENTO, "
                        "NUMSERIEEQUIP, NUMLOTE, EQUIPAMENTO) VALUES ("
                        ":nos, :codprod, :qtde, :pvenda, :ptabela, :percdesc, "
                        ":demo, :codfilial, :codequip, "
                        ":numserie, :numlote, :equip)"
                    ),
                    {
                        "nos": num_os_servico,
                        "codprod": item.cod_prod,
                        "qtde": item.qtde,
                        "pvenda": item.punit,
                        "ptabela": item.punit,
                        "percdesc": _perc_desc(item),
                        "demo": _DEF_DEMONSTRACAO,
                        "codfilial": cod_filial,
                        "codequip": _DEF_CODEQUIPAMENTO,
                        "numserie": _DEF_NUMSERIEEQUIP,
                        "numlote": _DEF_NUMLOTE,
                        "equip": _DEF_EQUIPAMENTO,
                    },
                )

    @staticmethod
    def _apagar_itens(cx: Any, num_os: int) -> None:
        cx.execute(
            text(
                "DELETE FROM PCITEMSERVICO WHERE NUMOSSERVICO IN "
                "(SELECT NUMOSSERVICO FROM PCORDEMSERVICOI WHERE NUMOS = :numos)"
            ),
            {"numos": num_os},
        )
        cx.execute(text("DELETE FROM PCORDEMSERVICOI WHERE NUMOS = :numos"), {"numos": num_os})
