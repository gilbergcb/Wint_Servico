"""Repositorio de parametros da rotina (tabela PCM_PARAM, chave/valor).

Parametro principal (MVP): TIPO_FATURAMENTO, que decide se o faturamento da
O.S. gera registro proprio (PCM_OS_FATURA) ou conta a receber nas tabelas
nativas do Winthor (PCPREST).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap

# chaves conhecidas
CHAVE_TIPO_FATURAMENTO = "TIPO_FATURAMENTO"
CHAVE_PEDIDO_OBRIGATORIO = "PEDIDO_OBRIGATORIO"
CHAVE_MODO_OPERACAO = "MODO_OPERACAO"
CHAVE_SETOR_TECNICOS = "SETOR_TECNICOS"

# valores de TIPO_FATURAMENTO
FATURAMENTO_INTERNO = "INTERNO"   # grava em PCM_OS_FATURA (tabela propria)
FATURAMENTO_WINTHOR = "WINTHOR"   # gera conta a receber em PCPREST (nativa)

FATURAMENTO_PADRAO = FATURAMENTO_INTERNO

# valores de MODO_OPERACAO (perfil do cliente)
MODO_PCM = "PCM"          # persiste nas tabelas proprias PCM_* (default)
MODO_WINTHOR = "WINTHOR"  # persiste 100% nas tabelas nativas do modulo 35

MODO_OPERACAO_PADRAO = MODO_PCM

# valores S/N
SIM = "S"
NAO = "N"
PEDIDO_OBRIGATORIO_PADRAO = SIM  # por padrao, exige pedido de venda na O.S.

_DESCRICOES = {
    CHAVE_TIPO_FATURAMENTO: "Tipo de faturamento da O.S. (INTERNO|WINTHOR)",
    CHAVE_PEDIDO_OBRIGATORIO: "Exige pedido de venda do Winthor na O.S. (S|N)",
    CHAVE_MODO_OPERACAO: "Perfil de persistencia: PCM (tabelas proprias) ou WINTHOR (modulo 35)",
    CHAVE_SETOR_TECNICOS: "Codigo do setor de tecnicos em PCEMPR.CODSETOR",
}


class ParametroRepo:
    def obter(self, chave: str, default: str | None = None) -> str | None:
        sql = "SELECT VALOR FROM PCM_PARAM WHERE CHAVE = :c"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"c": chave}).fetchone()
        if not row:
            return default
        valor = colmap(row)["VALOR"]
        return valor if valor is not None else default

    def salvar(self, chave: str, valor: str, usuario: str | None = None) -> None:
        """Insere ou atualiza o parametro (UPSERT via MERGE; compativel 10g)."""
        params: dict[str, Any] = {
            "c": chave,
            "v": valor,
            "d": _DESCRICOES.get(chave),
            "u": usuario,
        }
        sql = (
            "MERGE INTO PCM_PARAM p USING (SELECT :c AS CHAVE FROM DUAL) s "
            "ON (p.CHAVE = s.CHAVE) "
            "WHEN MATCHED THEN UPDATE SET p.VALOR = :v, p.DTALTERACAO = SYSDATE, "
            "p.USUARIO = :u "
            "WHEN NOT MATCHED THEN INSERT (CHAVE, VALOR, DESCRICAO, DTALTERACAO, USUARIO) "
            "VALUES (:c, :v, :d, SYSDATE, :u)"
        )
        with get_engine().begin() as cx:
            cx.execute(text(sql), params)

    # --------------------------------------------------------- atalhos de dominio
    def tipo_faturamento(self) -> str:
        """Devolve INTERNO|WINTHOR (default INTERNO se nao configurado)."""
        valor = self.obter(CHAVE_TIPO_FATURAMENTO, FATURAMENTO_PADRAO)
        return valor if valor in (FATURAMENTO_INTERNO, FATURAMENTO_WINTHOR) else FATURAMENTO_PADRAO

    def pedido_obrigatorio(self) -> bool:
        """Indica se a O.S. exige pedido de venda do Winthor (default: sim).

        Regra global (todos os usuarios). Excecoes por usuario sao tratadas via
        permissao do Winthor (PCCONTROI) em ``core.permissao_repo``.
        """
        valor = self.obter(CHAVE_PEDIDO_OBRIGATORIO, PEDIDO_OBRIGATORIO_PADRAO)
        return (valor or PEDIDO_OBRIGATORIO_PADRAO).upper() != NAO

    def modo_operacao(self) -> str:
        """Perfil de persistencia: PCM (tabelas proprias) | WINTHOR (modulo 35).

        Default PCM se nao configurado.
        """
        valor = self.obter(CHAVE_MODO_OPERACAO, MODO_OPERACAO_PADRAO)
        return valor if valor in (MODO_PCM, MODO_WINTHOR) else MODO_OPERACAO_PADRAO

    def setor_tecnicos(self) -> int | None:
        """Codigo de PCEMPR.CODSETOR usado para filtrar tecnicos."""
        valor = (self.obter(CHAVE_SETOR_TECNICOS, "") or "").strip()
        if not valor:
            return None
        try:
            codigo = int(valor)
        except ValueError:
            return None
        return codigo if codigo > 0 else None
