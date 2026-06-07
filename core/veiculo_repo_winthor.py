"""Repositorio de veiculos no backend NATIVO do modulo 35 (cascata normalizada).

Drop-in da interface de ``core.veiculo_repo.VeiculoRepo``, porem gravando/lendo
nas tabelas nativas, na mesma cascata que a rotina 3509 (ver docs/TRACE_3509.md):

  - Marca       -> PCOSVEICULOMARCA       (CODOSMARCA   via SEQ_PCOSVEICULOMARCA)
  - Modelo      -> PCOSVEICULOMODELO      (CODOSMODELO  via SEQ_PCOSVEICULOMODELO; FK CODOSMARCA)
  - Combustivel -> PCOSVEICULOCOMBUSTIVEL (lookup; sem sequence -> NVL(MAX,0)+1)
  - Veiculo     -> PCOSVEICULO            (CODOSVEICULO via SEQ_PCOSVEICULO)

Diferencas do PCM (PCM_OS_VEICULO, denormalizado):
  * O nativo NAO tem CODCLI/COR/CHASSI/KMATUAL no veiculo -> esses campos ficam
    None na leitura e sao ignorados na escrita.
  * marca/modelo/combustivel sao normalizados: resolvidos (get-or-create) por nome.
  * ANO, PLACA, CODOSMODELO e CODOSCOMBUSTIVEL sao NOT NULL no nativo -> placa,
    marca, modelo e combustivel passam a ser obrigatorios no modo Winthor; ANO
    vazio grava 0.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db_engine import get_engine
from core.sqlutil import colmap
from modelos.veiculo import Veiculo

_SELECT = (
    "SELECT v.CODOSVEICULO, v.PLACA, v.ANO, v.MOTOR, v.OBS, v.DTCADASTRO, "
    "mo.MODELO, ma.MARCA, co.COMBUSTIVEL "
    "FROM PCOSVEICULO v "
    "JOIN PCOSVEICULOMODELO mo ON mo.CODOSMODELO = v.CODOSMODELO "
    "JOIN PCOSVEICULOMARCA ma ON ma.CODOSMARCA = mo.CODOSMARCA "
    "LEFT JOIN PCOSVEICULOCOMBUSTIVEL co ON co.CODOSCOMBUSTIVEL = v.CODOSCOMBUSTIVEL"
)


def _row_para_veiculo(row: Any) -> Veiculo:
    m = colmap(row)
    return Veiculo(
        cod_veiculo=int(m["CODOSVEICULO"]),
        cod_cli=None,  # nativo nao guarda CODCLI no veiculo
        placa=m["PLACA"],
        modelo=m["MODELO"],
        marca=m["MARCA"],
        ano=int(m["ANO"]) if m["ANO"] is not None else None,
        combustivel=m["COMBUSTIVEL"],
        motor=m["MOTOR"],
        cor=None,
        chassi=None,
        km_atual=None,
        obs=m["OBS"],
        dt_cadastro=m["DTCADASTRO"],
    )


def _obrig(valor: str | None, rotulo: str) -> str:
    texto = (valor or "").strip()
    if not texto:
        raise ValueError(f"No modo Winthor o campo '{rotulo}' do veiculo e obrigatorio.")
    return texto


class VeiculoRepoWinthor:
    # ------------------------------------------------------------------ leitura
    def listar(self, cod_cli: int | None = None) -> list[Veiculo]:
        # cod_cli e ignorado: o veiculo nativo nao tem vinculo com cliente.
        sql = f"{_SELECT} ORDER BY v.PLACA"
        with get_engine().connect() as cx:
            rows = cx.execute(text(sql)).fetchall()
        return [_row_para_veiculo(r) for r in rows]

    def obter(self, cod_veiculo: int) -> Veiculo | None:
        sql = f"{_SELECT} WHERE v.CODOSVEICULO = :cod"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"cod": cod_veiculo}).fetchone()
        return _row_para_veiculo(row) if row else None

    def buscar_por_placa(self, placa: str) -> Veiculo | None:
        sql = f"{_SELECT} WHERE UPPER(v.PLACA) = :placa"
        with get_engine().connect() as cx:
            row = cx.execute(text(sql), {"placa": (placa or "").strip().upper()}).fetchone()
        return _row_para_veiculo(row) if row else None

    # ------------------------------------------------------------------ escrita
    def inserir(self, veiculo: Veiculo) -> int:
        """Resolve a cascata marca/modelo/combustivel e insere em PCOSVEICULO."""
        with get_engine().begin() as cx:
            cod_modelo, cod_comb = self._resolver_cascata(cx, veiculo)
            cod = int(cx.execute(text("SELECT SEQ_PCOSVEICULO.NEXTVAL FROM DUAL")).scalar_one())
            cx.execute(
                text(
                    "INSERT INTO PCOSVEICULO ("
                    "CODOSVEICULO, PLACA, CODOSMODELO, ANO, CODOSCOMBUSTIVEL, "
                    "MOTOR, OBS, DTCADASTRO) VALUES ("
                    ":cod, :placa, :codmodelo, :ano, :codcomb, :motor, :obs, SYSDATE)"
                ),
                self._params_veiculo(veiculo, cod, cod_modelo, cod_comb),
            )
        return cod

    def atualizar(self, veiculo: Veiculo) -> None:
        if veiculo.cod_veiculo is None:
            raise ValueError("cod_veiculo obrigatorio para atualizar.")
        with get_engine().begin() as cx:
            cod_modelo, cod_comb = self._resolver_cascata(cx, veiculo)
            cx.execute(
                text(
                    "UPDATE PCOSVEICULO SET PLACA = :placa, CODOSMODELO = :codmodelo, "
                    "ANO = :ano, CODOSCOMBUSTIVEL = :codcomb, MOTOR = :motor, OBS = :obs "
                    "WHERE CODOSVEICULO = :cod"
                ),
                self._params_veiculo(veiculo, veiculo.cod_veiculo, cod_modelo, cod_comb),
            )

    # ------------------------------------------------------------------ cascata
    def _resolver_cascata(self, cx: Any, veiculo: Veiculo) -> tuple[int, int]:
        marca = _obrig(veiculo.marca, "Marca")
        modelo = _obrig(veiculo.modelo, "Modelo")
        combustivel = _obrig(veiculo.combustivel, "Combustivel")
        cod_marca = self._marca_id(cx, marca)
        cod_modelo = self._modelo_id(cx, cod_marca, modelo)
        cod_comb = self._combustivel_id(cx, combustivel)
        return cod_modelo, cod_comb

    @staticmethod
    def _params_veiculo(veiculo: Veiculo, cod: int, cod_modelo: int, cod_comb: int) -> dict[str, Any]:
        return {
            "cod": cod,
            "placa": (veiculo.placa or "").strip().upper() or None,
            "codmodelo": cod_modelo,
            "ano": veiculo.ano if veiculo.ano is not None else 0,  # ANO e NOT NULL
            "codcomb": cod_comb,
            "motor": veiculo.motor,
            "obs": veiculo.obs,
        }

    @staticmethod
    def _marca_id(cx: Any, marca: str) -> int:
        cod = cx.execute(
            text("SELECT CODOSMARCA FROM PCOSVEICULOMARCA WHERE UPPER(MARCA) = :m"),
            {"m": marca.upper()},
        ).scalar()
        if cod is not None:
            return int(cod)
        cod = int(cx.execute(text("SELECT SEQ_PCOSVEICULOMARCA.NEXTVAL FROM DUAL")).scalar_one())
        cx.execute(
            text("INSERT INTO PCOSVEICULOMARCA (CODOSMARCA, MARCA) VALUES (:c, :m)"),
            {"c": cod, "m": marca},
        )
        return cod

    @staticmethod
    def _modelo_id(cx: Any, cod_marca: int, modelo: str) -> int:
        cod = cx.execute(
            text(
                "SELECT CODOSMODELO FROM PCOSVEICULOMODELO "
                "WHERE CODOSMARCA = :ma AND UPPER(MODELO) = :mo"
            ),
            {"ma": cod_marca, "mo": modelo.upper()},
        ).scalar()
        if cod is not None:
            return int(cod)
        cod = int(cx.execute(text("SELECT SEQ_PCOSVEICULOMODELO.NEXTVAL FROM DUAL")).scalar_one())
        cx.execute(
            text(
                "INSERT INTO PCOSVEICULOMODELO (CODOSMARCA, CODOSMODELO, MODELO) "
                "VALUES (:ma, :c, :mo)"
            ),
            {"ma": cod_marca, "c": cod, "mo": modelo},
        )
        return cod

    @staticmethod
    def _combustivel_id(cx: Any, combustivel: str) -> int:
        cod = cx.execute(
            text("SELECT CODOSCOMBUSTIVEL FROM PCOSVEICULOCOMBUSTIVEL WHERE UPPER(COMBUSTIVEL) = :c"),
            {"c": combustivel.upper()},
        ).scalar()
        if cod is not None:
            return int(cod)
        # Tabela de lookup sem sequence -> proximo codigo via MAX+1.
        cod = int(
            cx.execute(
                text("SELECT NVL(MAX(CODOSCOMBUSTIVEL), 0) + 1 FROM PCOSVEICULOCOMBUSTIVEL")
            ).scalar_one()
        )
        cx.execute(
            text(
                "INSERT INTO PCOSVEICULOCOMBUSTIVEL (CODOSCOMBUSTIVEL, COMBUSTIVEL) "
                "VALUES (:c, :nome)"
            ),
            {"c": cod, "nome": combustivel},
        )
        return cod
