"""Repositorio de servicos (tabela propria PCM_SERVICO).

Opcao A: PCM_SERVICO referencia PCPRODUT.CODPROD (servico flagueado na 3501).
Acesso via SQLAlchemy Core (text()) sobre o engine do modulo.

Numeracao da PK: usamos PCM_SERVICO_SEQ.NEXTVAL explicitamente antes do INSERT
(deterministico e dispensa RETURNING INTO). A trigger PCM_SERVICO_BI so atua
quando CODSERVICO vem NULL, entao passar o valor explicito e consistente.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap
from modelos.servico import Servico

# Colunas de PCM_SERVICO mapeadas para o modelo (ordem usada nos SELECTs).
_COLS = (
    "CODSERVICO, CODPROD, DESCRICAO, CODFILIAL, PRECOPADRAO, TEMPOESTIMADOMIN, "
    "RETERISS, PERCALIQISS, ATIVO, OBS, DTCADASTRO, DTALTERACAO, USUARIOCAD"
)


def _sn(valor: bool) -> str:
    return "S" if valor else "N"


def _to_dec(valor: Any) -> Decimal:
    if valor is None:
        return Decimal("0")
    return Decimal(str(valor))


def _row_para_servico(row: Any) -> Servico:
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


class ServicoRepo:
    # ------------------------------------------------------------------ leitura
    def listar(self, termo: str = "", ativo: bool | None = None) -> list[Servico]:
        """Lista servicos filtrando por descricao/codigo (termo) e situacao."""
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
        sql = f"SELECT {_COLS} FROM PCM_SERVICO{where} ORDER BY DESCRICAO"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_servico(r) for r in rows]

    def obter(self, cod_servico: int) -> Servico | None:
        sql = f"SELECT {_COLS} FROM PCM_SERVICO WHERE CODSERVICO = :cod"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"cod": cod_servico}).fetchone()
        return _row_para_servico(row) if row else None

    # ------------------------------------------------------------------ escrita
    def inserir(self, servico: Servico) -> int:
        """Insere em PCM_SERVICO e retorna o CODSERVICO gerado."""
        with get_engine().begin() as cx:
            cod = cx.execute(text("SELECT PCM_SERVICO_SEQ.NEXTVAL FROM DUAL")).scalar_one()
            cod = int(cod)
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
                {
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
                },
            )
        return cod

    def atualizar(self, servico: Servico) -> None:
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
                {
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
                    "cod": servico.cod_servico,
                },
            )

    def inativar(self, cod_servico: int) -> None:
        with get_engine().begin() as cx:
            cx.execute(
                text("UPDATE PCM_SERVICO SET ATIVO = 'N', DTALTERACAO = SYSDATE WHERE CODSERVICO = :cod"),
                {"cod": cod_servico},
            )

    # -------------------------------------------------------- lookup PCPRODUT
    def buscar_produto_servico(self, termo: str, limite: int = 50) -> list[dict]:
        """Lookup de produto em PCPRODUT (nativa, somente leitura).

        Usa apenas CODPROD/DESCRICAO (colunas garantidas).
        TODO: quando o banco estabilizar, confirmar o flag de servico em
        PCPRODUT (ex.: SERVICO='S') e filtrar so produtos-servico.
        """
        termo = (termo or "").strip()
        params: dict[str, Any] = {"lim": limite}
        if termo.isdigit():
            cond = "CODPROD = :cod"
            params["cod"] = int(termo)
        else:
            cond = "UPPER(DESCRICAO) LIKE :desc"
            params["desc"] = f"%{termo.upper()}%"
        sql = (
            "SELECT * FROM (SELECT CODPROD, DESCRICAO FROM PCPRODUT "
            f"WHERE {cond} AND NVL(DTEXCLUSAO, SYSDATE) >= SYSDATE "
            "ORDER BY DESCRICAO) WHERE ROWNUM <= :lim"
        )
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        itens = [colmap(r) for r in rows]
        return [{"cod_prod": int(c["CODPROD"]), "descricao": c["DESCRICAO"]} for c in itens]
