"""Tela: Lista de Ordens de Servico (espelha a 3509 inicial).

Filtros (Nº O.S., Cliente, periodo, Situacao) + grid + acoes "Nova O.S." /
"Alterar O.S.". A edicao abre o TelaOSEdicao como QDialog.
"""
from __future__ import annotations

from datetime import datetime, time

from PyQt6 import QtCore, QtWidgets

from core.conexao_oracle import ConexaoOracle
from core.ordem_servico_repo import OrdemServicoRepo
from modelos.ordem_servico import OrdemServico, SituacaoOS
from ui_widgets.tela_os_edicao import TelaOSEdicao
from ui_widgets.theme import marcar_botao

_SITUACOES_FILTRO = [
    (None, "Todas"),
    (SituacaoOS.ABERTA, "Aberta"),
    (SituacaoOS.EM_EXECUCAO, "Em execucao"),
    (SituacaoOS.CONCLUIDA, "Concluida"),
    (SituacaoOS.FATURADA, "Faturada"),
    (SituacaoOS.CANCELADA, "Cancelada"),
]

_ROTULO_SITUACAO = {
    SituacaoOS.ABERTA: "Aberta",
    SituacaoOS.EM_EXECUCAO: "Em execucao",
    SituacaoOS.CONCLUIDA: "Concluida",
    SituacaoOS.FATURADA: "Faturada",
    SituacaoOS.CANCELADA: "Cancelada",
}


class TelaOSLista(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = OrdemServicoRepo()
        self._ordens: list[OrdemServico] = []
        self._montar_ui()

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Ordens de Servico")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        # --- filtros ---
        filtros = QtWidgets.QHBoxLayout()
        self.spin_numos = QtWidgets.QSpinBox()
        self.spin_numos.setRange(0, 2147483647)  # limite do QSpinBox (int 32-bit)
        self.spin_numos.setSpecialValueText("Nº O.S.")
        self.spin_cliente = QtWidgets.QSpinBox()
        self.spin_cliente.setRange(0, 99999999)
        self.spin_cliente.setSpecialValueText("Cliente")
        self.dt_ini = QtWidgets.QDateEdit()
        self.dt_ini.setCalendarPopup(True)
        self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_ini.setDate(QtCore.QDate.currentDate().addMonths(-1))
        self.dt_fim = QtWidgets.QDateEdit()
        self.dt_fim.setCalendarPopup(True)
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setDate(QtCore.QDate.currentDate())
        self.chk_periodo = QtWidgets.QCheckBox("Periodo")
        self.cmb_situacao = QtWidgets.QComboBox()
        for sit, rotulo in _SITUACOES_FILTRO:
            self.cmb_situacao.addItem(rotulo, sit)
        btn_pesquisar = QtWidgets.QPushButton("Pesquisar")
        btn_pesquisar.clicked.connect(self._pesquisar)

        filtros.addWidget(QtWidgets.QLabel("Nº:"))
        filtros.addWidget(self.spin_numos)
        filtros.addWidget(QtWidgets.QLabel("Cliente:"))
        filtros.addWidget(self.spin_cliente)
        filtros.addWidget(self.chk_periodo)
        filtros.addWidget(self.dt_ini)
        filtros.addWidget(QtWidgets.QLabel("a"))
        filtros.addWidget(self.dt_fim)
        filtros.addWidget(QtWidgets.QLabel("Situacao:"))
        filtros.addWidget(self.cmb_situacao)
        filtros.addStretch(1)
        filtros.addWidget(btn_pesquisar)
        layout.addLayout(filtros)

        # --- tabela ---
        self.tabela = QtWidgets.QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(["Nº O.S.", "Cliente", "Situacao", "Dt Cadastro", "Vl Total"])
        self.tabela.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.doubleClicked.connect(lambda *_: self._alterar())
        layout.addWidget(self.tabela, 1)

        # --- acoes ---
        acoes = QtWidgets.QHBoxLayout()
        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setObjectName("telaSubtitulo")
        btn_nova = QtWidgets.QPushButton("Nova O.S.")
        marcar_botao(btn_nova, "primary")
        btn_nova.clicked.connect(self._nova)
        btn_alterar = QtWidgets.QPushButton("Alterar O.S.")
        btn_alterar.clicked.connect(self._alterar)
        acoes.addWidget(self.lbl_status, 1)
        acoes.addWidget(btn_nova)
        acoes.addWidget(btn_alterar)
        layout.addLayout(acoes)

        QtCore.QTimer.singleShot(0, self._pesquisar)

    # ----------------------------------------------------------------- helpers
    def _offline(self) -> bool:
        if ConexaoOracle.instance().offline:
            self.lbl_status.setText("Sem conexao com o banco (modo dev). Operacoes indisponiveis.")
            return True
        return False

    def _os_selecionada(self) -> OrdemServico | None:
        linha = self.tabela.currentRow()
        if linha < 0 or linha >= len(self._ordens):
            return None
        return self._ordens[linha]

    # ------------------------------------------------------------------ acoes
    def _pesquisar(self) -> None:
        if self._offline():
            self.tabela.setRowCount(0)
            return
        dt_ini = dt_fim = None
        if self.chk_periodo.isChecked():
            dt_ini = datetime.combine(self.dt_ini.date().toPyDate(), time.min)
            dt_fim = datetime.combine(self.dt_fim.date().toPyDate(), time.max)
        try:
            self._ordens = self._repo.listar(
                num_os=self.spin_numos.value() or None,
                cod_cli=self.spin_cliente.value() or None,
                situacao=int(self.cmb_situacao.currentData()) if self.cmb_situacao.currentData() else None,
                dt_ini=dt_ini,
                dt_fim=dt_fim,
            )
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Pesquisar O.S.", f"Falha ao pesquisar:\n{exc}")
            return
        self._preencher_tabela()
        self.lbl_status.setText(f"{len(self._ordens)} O.S.")

    def _preencher_tabela(self) -> None:
        self.tabela.setRowCount(0)
        for os_ in self._ordens:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            self.tabela.setItem(linha, 0, QtWidgets.QTableWidgetItem(str(os_.num_os or "")))
            self.tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(str(os_.cod_cli or "")))
            self.tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(_ROTULO_SITUACAO.get(os_.situacao, "")))
            dt = os_.dt_cadastro.strftime("%d/%m/%Y") if os_.dt_cadastro else ""
            self.tabela.setItem(linha, 3, QtWidgets.QTableWidgetItem(dt))
            it_total = QtWidgets.QTableWidgetItem(f"{os_.vl_total:,.2f}")
            it_total.setTextAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            self.tabela.setItem(linha, 4, it_total)

    def _nova(self) -> None:
        if self._offline():
            return
        dlg = TelaOSEdicao(None, self)
        if dlg.exec():
            self._pesquisar()

    def _alterar(self) -> None:
        if self._offline():
            return
        os_ = self._os_selecionada()
        if os_ is None or os_.num_os is None:
            QtWidgets.QMessageBox.information(self, "Alterar", "Selecione uma O.S. na lista.")
            return
        dlg = TelaOSEdicao(os_.num_os, self)
        if dlg.exec():
            self._pesquisar()
