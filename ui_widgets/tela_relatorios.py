"""Tela: Relatorios.

Selecao de relatorio + periodo, grid de resultados e exportacao CSV.
Relatorios disponiveis: O.S. por situacao, Comissoes por tecnico e Servicos
mais executados (core.relatorio_repo).
"""
from __future__ import annotations

import csv
from datetime import datetime, time
from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from core.conexao_oracle import ConexaoOracle
from core.relatorio_repo import RelatorioRepo
from ui_widgets.theme import configurar_combo, configurar_grid
from ui_widgets.theme import marcar_botao

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

# (rotulo, nome do metodo em RelatorioRepo)
_RELATORIOS = [
    ("O.S. por situação", "os_por_situacao"),
    ("Comissões por técnico", "comissoes_por_tecnico"),
    ("Serviços mais executados", "servicos_mais_executados"),
]


class TelaRelatorios(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = RelatorioRepo()
        self._cabecalho: list[str] = []
        self._linhas: list[list] = []
        self._montar_ui()

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Relatórios")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        filtros = QtWidgets.QHBoxLayout()
        self.cmb_relatorio = QtWidgets.QComboBox()
        configurar_combo(self.cmb_relatorio)
        for rotulo, metodo in _RELATORIOS:
            self.cmb_relatorio.addItem(rotulo, metodo)
        self.chk_periodo = QtWidgets.QCheckBox("Período")
        self.chk_periodo.setChecked(True)
        self.dt_ini = QtWidgets.QDateEdit(calendarPopup=True)
        self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_ini.setDate(QtCore.QDate.currentDate().addMonths(-1))
        self.dt_fim = QtWidgets.QDateEdit(calendarPopup=True)
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setDate(QtCore.QDate.currentDate())
        btn_gerar = QtWidgets.QPushButton("Gerar")
        marcar_botao(btn_gerar, "primary")
        btn_gerar.clicked.connect(self._gerar)

        filtros.addWidget(QtWidgets.QLabel("Relatório:"))
        filtros.addWidget(self.cmb_relatorio, 1)
        filtros.addWidget(self.chk_periodo)
        filtros.addWidget(self.dt_ini)
        filtros.addWidget(QtWidgets.QLabel("a"))
        filtros.addWidget(self.dt_fim)
        filtros.addWidget(btn_gerar)
        layout.addLayout(filtros)

        self.tabela = QtWidgets.QTableWidget(0, 0)
        configurar_grid(self.tabela)
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.tabela, 1)

        rodape = QtWidgets.QHBoxLayout()
        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setObjectName("telaSubtitulo")
        self.btn_export = QtWidgets.QPushButton("Exportar CSV")
        self.btn_export.clicked.connect(self._exportar)
        self.btn_export.setEnabled(False)
        rodape.addWidget(self.lbl_status, 1)
        rodape.addWidget(self.btn_export)
        layout.addLayout(rodape)

    # ----------------------------------------------------------------- helpers
    def _offline(self) -> bool:
        if ConexaoOracle.instance().offline:
            self.lbl_status.setText("Sem conexão com o banco (modo dev). Operações indisponíveis.")
            return True
        return False

    def _periodo(self):
        if not self.chk_periodo.isChecked():
            return None, None
        return (
            datetime.combine(self.dt_ini.date().toPyDate(), time.min),
            datetime.combine(self.dt_fim.date().toPyDate(), time.max),
        )

    # ------------------------------------------------------------------ acoes
    def _gerar(self) -> None:
        if self._offline():
            return
        metodo = getattr(self._repo, self.cmb_relatorio.currentData())
        dt_ini, dt_fim = self._periodo()
        try:
            self._cabecalho, self._linhas = metodo(dt_ini, dt_fim)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Relatórios", f"Falha ao gerar:\n{exc}")
            return
        self._preencher()
        self.btn_export.setEnabled(bool(self._linhas))
        self.lbl_status.setText(f"{len(self._linhas)} linha(s)")

    def _preencher(self) -> None:
        self.tabela.clear()
        self.tabela.setColumnCount(len(self._cabecalho))
        self.tabela.setHorizontalHeaderLabels(self._cabecalho)
        self.tabela.setRowCount(0)
        for valores in self._linhas:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            for col, valor in enumerate(valores):
                item = QtWidgets.QTableWidgetItem(str(valor))
                if isinstance(valor, (int,)) or (isinstance(valor, str) and self._cabecalho[col] in ("Vl Total", "Comissão")):
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                self.tabela.setItem(linha, col, item)
        if self._cabecalho:
            self.tabela.horizontalHeader().setSectionResizeMode(
                1, QtWidgets.QHeaderView.ResizeMode.Stretch
            )

    def _exportar(self) -> None:
        if not self._linhas:
            return
        OUTPUTS.mkdir(exist_ok=True)
        nome = self.cmb_relatorio.currentData()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho = OUTPUTS / f"{nome}_{stamp}.csv"
        try:
            with caminho.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(self._cabecalho)
                w.writerows(self._linhas)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Exportar", f"Falha ao exportar:\n{exc}")
            return
        QtWidgets.QMessageBox.information(self, "Exportar", f"Exportado para:\n{caminho}")

