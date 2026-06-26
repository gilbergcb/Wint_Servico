"""Repositorio de servicos.

No modo PCM usa a tabela propria ``PCM_SERVICO``. No modo 100% Winthor usa os
produtos-servico nativos de ``PCPRODUT`` com ``TIPOMERC = 'SS'``.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.parametro_repo import MODO_WINTHOR, ParametroRepo
from core.sqlutil import colmap
from modelos.servico import Servico

_COLS_PCM = (
    "CODSERVICO, CODPROD, DESCRICAO, CODFILIAL, PRECOPADRAO, TEMPOESTIMADOMIN, "
    "RETERISS, PERCALIQISS, ATIVO, OBS, DTCADASTRO, DTALTERACAO, USUARIOCAD"
)

_COLS_PROD_LISTA = (
    "CODPROD, DESCRICAO, EMBALAGEM, CODEPTO, CODSEC, CODFORNEC, TIPOMERC, "
    "CUSTOREP, NATUREZAPRODUTO"
)

_COLS_PROD_DETALHE = (
    "CODPROD, DESCRICAO, EMBALAGEM, CODEPTO, CODSEC, CODFORNEC, TIPOMERC, "
    "CUSTOREP, NATUREZAPRODUTO, OSCOMODATO, OBRIGAPREENCCONTRATO, "
    "GERAOSAUTOMATIC, NUMSERVICO, PERPIS_SERVICO, PERCOFINS_SERVICO, "
    "SITTRIBUT_SERVICO, COMISSAOSERVICOPRESTADO, PERCENTUALCPRB, CODIGOCNAE, "
    "TEMPOSERVICO, PERCENTUALINCIDENCIA, TIPOSERVICOVINCULADORECEITA, "
    "INCIDENCIACPRB, NBM, PERCCSLL, PERCENTUALISS"
)


def _sn(valor: bool) -> str:
    return "S" if valor else "N"


def _to_dec(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")
    return Decimal(str(valor))


def _row_para_servico_pcm(row: Any) -> Servico:
    m = colmap(row)
    return Servico(
        cod_servico=int(m["CODSERVICO"]),
        cod_prod=int(m["CODPROD"]) if m["CODPROD"] is not None else None,
        descricao=m["DESCRICAO"] or "",
        cod_filial=m["CODFILIAL"],
        preco_padrao=_to_dec(m["PRECOPADRAO"]),
        tempo_estimado_min=int(m["TEMPOESTIMADOMIN"]) if m["TEMPOESTIMADOMIN"] is not None else None,
        reter_iss=(m["RETERISS"] or "N") == "S",
        perc_aliq_iss=_to_dec(m["PERCALIQISS"]),
        ativo=(m["ATIVO"] or "S") == "S",
        obs=m["OBS"],
        dt_cadastro=m["DTCADASTRO"],
        dt_alteracao=m["DTALTERACAO"],
        usuario_cad=m["USUARIOCAD"],
    )


def _row_para_servico_winthor(row: Any) -> Servico:
    m = colmap(row)
    return Servico(
        cod_servico=int(m["CODPROD"]),
        cod_prod=int(m["CODPROD"]) if m["CODPROD"] is not None else None,
        descricao=m["DESCRICAO"] or "",
        preco_padrao=_to_dec(m["CUSTOREP"]),
        tempo_estimado_min=int(m["TEMPOSERVICO"]) if m.get("TEMPOSERVICO") is not None else None,
        perc_aliq_iss=_to_dec(m.get("PERCENTUALISS")),
        ativo=(m["TIPOMERC"] or "") == "SS",
    )


class ServicoRepo:
    def _modo_winthor(self) -> bool:
        return ParametroRepo().modo_operacao() == MODO_WINTHOR

    # ------------------------------------------------------------------ leitura
    def listar(self, termo: str = "", ativo: bool | None = None) -> list[Servico]:
        if self._modo_winthor():
            return self._listar_winthor(termo, ativo)
        return self._listar_pcm(termo, ativo)

    def _listar_pcm(self, termo: str = "", ativo: bool | None = None) -> list[Servico]:
        cond = []
        params: dict[str, Any] = {}
        termo = (termo or "").strip()
        if termo:
            if termo.isdigit():
                cond.append("CODSERVICO = :cod")
                params["cod"] = int(termo)
            else:
                cond.append("UPPER(DESCRICAO) LIKE :desc")
                params["desc"] = f"%{termo.upper()}%"
        if ativo is not None:
            cond.append("ATIVO = :ativo")
            params["ativo"] = _sn(ativo)
        where = (" WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT {_COLS_PCM} FROM PCM_SERVICO{where} ORDER BY DESCRICAO"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_servico_pcm(r) for r in rows]

    def _listar_winthor(self, termo: str = "", ativo: bool | None = None) -> list[Servico]:
        cond = ["TIPOMERC = 'SS'"]
        params: dict[str, Any] = {}
        termo = (termo or "").strip()
        if termo:
            if termo.isdigit():
                cond.append("CODPROD = :cod")
                params["cod"] = int(termo)
            else:
                cond.append("UPPER(DESCRICAO) LIKE :desc")
                params["desc"] = f"%{termo.upper()}%"
        if ativo is False:
            return []
        where = " WHERE " + " AND ".join(cond)
        sql = f"SELECT {_COLS_PROD_DETALHE} FROM PCPRODUT{where} ORDER BY DESCRICAO"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_servico_winthor(r) for r in rows]

    def obter(self, cod_servico: int) -> Servico | None:
        if self._modo_winthor():
            sql = f"SELECT {_COLS_PROD_DETALHE} FROM PCPRODUT WHERE CODPROD = :cod"
            mapper = _row_para_servico_winthor
        else:
            sql = f"SELECT {_COLS_PCM} FROM PCM_SERVICO WHERE CODSERVICO = :cod"
            mapper = _row_para_servico_pcm
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"cod": cod_servico}).fetchone()
        return mapper(row) if row else None

    # ------------------------------------------------------------------ escrita
    def inserir(self, servico: Servico) -> int:
        if self._modo_winthor():
            return self._inserir_winthor(servico)
        return self._inserir_pcm(servico)

    def _inserir_pcm(self, servico: Servico) -> int:
        with get_engine().begin() as cx:
            cod = int(cx.execute(text("SELECT PCM_SERVICO_SEQ.NEXTVAL FROM DUAL")).scalar_one())
            cx.execute(
                text(
                    "INSERT INTO PCM_SERVICO ("
                    "CODSERVICO, CODPROD, DESCRICAO, CODFILIAL, PRECOPADRAO, "
                    "TEMPOESTIMADOMIN, RETERISS, PERCALIQISS, ATIVO, OBS, "
                    "DTCADASTRO, USUARIOCAD) VALUES ("
                    ":cod, :codprod, :descricao, :codfilial, :preco, "
                    ":tempo, :reteriss, :perciss, :ativo, :obs, "
                    "SYSDATE, :usuario)"
                ),
                self._params_pcm(servico, cod),
            )
        return cod

    def _inserir_winthor(self, servico: Servico) -> int:
        cod = servico.cod_prod or servico.cod_servico
        if cod is None:
            raise ValueError("Selecione um produto vinculado para gravar o servico.")
        servico.cod_prod = int(cod)
        servico.cod_servico = int(cod)
        self._atualizar_winthor(servico)
        return int(cod)

    def atualizar(self, servico: Servico) -> None:
        if self._modo_winthor():
            self._atualizar_winthor(servico)
        else:
            self._atualizar_pcm(servico)

    def _atualizar_pcm(self, servico: Servico) -> None:
        if servico.cod_servico is None:
            raise ValueError("cod_servico obrigatorio para atualizar.")
        with get_engine().begin() as cx:
            cx.execute(
                text(
                    "UPDATE PCM_SERVICO SET "
                    "CODPROD = :codprod, DESCRICAO = :descricao, CODFILIAL = :codfilial, "
                    "PRECOPADRAO = :preco, TEMPOESTIMADOMIN = :tempo, RETERISS = :reteriss, "
                    "PERCALIQISS = :perciss, ATIVO = :ativo, OBS = :obs, "
                    "DTALTERACAO = SYSDATE, USUARIOCAD = :usuario "
                    "WHERE CODSERVICO = :cod"
                ),
                self._params_pcm(servico, servico.cod_servico),
            )

    def _atualizar_winthor(self, servico: Servico) -> None:
        cod = servico.cod_prod or servico.cod_servico
        if cod is None:
            raise ValueError("cod_prod obrigatorio para atualizar PCPRODUT.")
        with get_engine().begin() as cx:
            cx.execute(
                text(
                    "UPDATE PCPRODUT SET "
                    "DESCRICAO = :descricao, "
                    "TIPOMERC = 'SS', "
                    "CUSTOREP = :preco, "
                    "TEMPOSERVICO = :tempo, "
                    "PERCENTUALISS = :perciss "
                    "WHERE CODPROD = :cod"
                ),
                {
                    "cod": cod,
                    "descricao": servico.descricao,
                    "preco": servico.preco_padrao,
                    "tempo": servico.tempo_estimado_min,
                    "perciss": servico.perc_aliq_iss,
                },
            )
            if cx.execute(text("SELECT COUNT(*) FROM PCPRODUT WHERE CODPROD = :cod"), {"cod": cod}).scalar_one() == 0:
                raise ValueError(f"Produto {cod} nao encontrado em PCPRODUT.")

    @staticmethod
    def _params_pcm(servico: Servico, cod: int) -> dict[str, Any]:
        return {
            "cod": cod,
            "codprod": servico.cod_prod,
            "descricao": servico.descricao,
            "codfilial": servico.cod_filial,
            "preco": servico.preco_padrao,
            "tempo": servico.tempo_estimado_min,
            "reteriss": _sn(servico.reter_iss),
            "perciss": servico.perc_aliq_iss,
            "ativo": _sn(servico.ativo),
            "obs": servico.obs,
            "usuario": servico.usuario_cad,
        }

    def inativar(self, cod_servico: int) -> None:
        if self._modo_winthor():
            sql = "UPDATE PCPRODUT SET TIPOMERC = NULL WHERE CODPROD = :cod AND TIPOMERC = 'SS'"
        else:
            sql = "UPDATE PCM_SERVICO SET ATIVO = 'N', DTALTERACAO = SYSDATE WHERE CODSERVICO = :cod"
        with get_engine().begin() as cx:
            cx.execute(text(sql), {"cod": cod_servico})

    # -------------------------------------------------------- lookup PCPRODUT
    def buscar_produto_servico(self, termo: str, limite: int = 50) -> list[dict]:
        termo = (termo or "").strip()
        params: dict[str, Any] = {"lim": limite}
        if termo.isdigit():
            cond = "CODPROD = :cod"
            params["cod"] = int(termo)
        else:
            cond = "UPPER(DESCRICAO) LIKE :desc"
            params["desc"] = f"%{termo.upper()}%"

        if self._modo_winthor():
            where = f"TIPOMERC = 'SS' AND {cond}"
        else:
            where = f"{cond} AND NVL(DTEXCLUSAO, SYSDATE) >= SYSDATE"
        sql = (
            f"SELECT * FROM (SELECT {_COLS_PROD_LISTA} FROM PCPRODUT "
            f"WHERE {where} ORDER BY DESCRICAO) WHERE ROWNUM <= :lim"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        itens = [colmap(r) for r in rows]
        return [{"cod_prod": int(c["CODPROD"]), "descricao": c["DESCRICAO"]} for c in itens]
