"""Repositorio de veiculos da O.S. (tabela propria PCM_OS_VEICULO).

Acesso via SQLAlchemy Core (text()). PK por PCM_OS_VEICULO_SEQ.NEXTVAL antes
do INSERT (a trigger PCM_OS_VEICULO_BI so atua quando CODVEICULO vem NULL).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap
from modelos.veiculo import Veiculo

_COLS = (
    "CODVEICULO, CODCLI, PLACA, MODELO, MARCA, ANO, COMBUSTIVEL, MOTOR, "
    "COR, CHASSI, KMATUAL, OBS, DTCADASTRO"
)


def _row_para_veiculo(row: Any) -> Veiculo:
    m = colmap(row)
    return Veiculo(
        cod_veiculo=int(m["CODVEICULO"]),
        cod_cli=int(m["CODCLI"]) if m["CODCLI"] is not None else None,
        placa=m["PLACA"],
        modelo=m["MODELO"],
        marca=m["MARCA"],
        ano=int(m["ANO"]) if m["ANO"] is not None else None,
        combustivel=m["COMBUSTIVEL"],
        motor=m["MOTOR"],
        cor=m["COR"],
        chassi=m["CHASSI"],
        km_atual=int(m["KMATUAL"]) if m["KMATUAL"] is not None else None,
        obs=m["OBS"],
        dt_cadastro=m["DTCADASTRO"],
    )


class VeiculoRepo:
    # ------------------------------------------------------------------ leitura
    def listar(self, cod_cli: int | None = None) -> list[Veiculo]:
        cond = ""
        params: dict[str, Any] = {}
        if cod_cli is not None:
            cond = " WHERE CODCLI = :cli"
            params["cli"] = cod_cli
        sql = f"SELECT {_COLS} FROM PCM_OS_VEICULO{cond} ORDER BY PLACA"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql), params).fetchall()
        return [_row_para_veiculo(r) for r in rows]

    def obter(self, cod_veiculo: int) -> Veiculo | None:
        sql = f"SELECT {_COLS} FROM PCM_OS_VEICULO WHERE CODVEICULO = :cod"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"cod": cod_veiculo}).fetchone()
        return _row_para_veiculo(row) if row else None

    def buscar_por_placa(self, placa: str) -> Veiculo | None:
        sql = f"SELECT {_COLS} FROM PCM_OS_VEICULO WHERE UPPER(PLACA) = :placa"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"placa": (placa or "").strip().upper()}).fetchone()
        return _row_para_veiculo(row) if row else None

    # ------------------------------------------------------------------ escrita
    def inserir(self, veiculo: Veiculo) -> int:
        """Insere em PCM_OS_VEICULO e retorna o CODVEICULO gerado."""
        with get_engine().begin() as cx:
            cod = cx.execute(text("SELECT PCM_OS_VEICULO_SEQ.NEXTVAL FROM DUAL")).scalar_one()
            cod = int(cod)
            cx.execute(
                text(
                    "INSERT INTO PCM_OS_VEICULO ("
                    "CODVEICULO, CODCLI, PLACA, MODELO, MARCA, ANO, COMBUSTIVEL, "
                    "MOTOR, COR, CHASSI, KMATUAL, OBS, DTCADASTRO) VALUES ("
                    ":cod, :codcli, :placa, :modelo, :marca, :ano, :combustivel, "
                    ":motor, :cor, :chassi, :kmatual, :obs, SYSDATE)"
                ),
                self._params(veiculo, cod),
            )
        return cod

    def atualizar(self, veiculo: Veiculo) -> None:
        if veiculo.cod_veiculo is None:
            raise ValueError("cod_veiculo obrigatorio para atualizar.")
        with get_engine().begin() as cx:
            cx.execute(
                text(
                    "UPDATE PCM_OS_VEICULO SET "
                    "CODCLI = :codcli, PLACA = :placa, MODELO = :modelo, MARCA = :marca, "
                    "ANO = :ano, COMBUSTIVEL = :combustivel, MOTOR = :motor, COR = :cor, "
                    "CHASSI = :chassi, KMATUAL = :kmatual, OBS = :obs "
                    "WHERE CODVEICULO = :cod"
                ),
                self._params(veiculo, veiculo.cod_veiculo),
            )

    @staticmethod
    def _params(veiculo: Veiculo, cod: int) -> dict[str, Any]:
        return {
            "cod": cod,
            "codcli": veiculo.cod_cli,
            "placa": (veiculo.placa or "").strip().upper() or None,
            "modelo": veiculo.modelo,
            "marca": veiculo.marca,
            "ano": veiculo.ano,
            "combustivel": veiculo.combustivel,
            "motor": veiculo.motor,
            "cor": veiculo.cor,
            "chassi": veiculo.chassi,
            "kmatual": veiculo.km_atual,
            "obs": veiculo.obs,
        }
