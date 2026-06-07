"""Tela: Acompanhamento das Ordens de Servico.

Painel com filtros (periodo, situacao, tecnico), KPIs por situacao, grid das
O.S. e acoes de avanco de status (Iniciar execucao / Concluir / Reabrir /
Cancelar). Duplo-clique abre a edicao da O.S.
"""
from __future__ import annotations

from datetime import datetime, time

from PyQt6 import QtCore, QtWidgets

import parametros_winthor
from core.conexao_oracle import ConexaoOracle
from core.ordem_servico_repo import OrdemServicoRepo
from core.tecnico_repo import TecnicoRepo
from modelos.ordem_servico import OrdemServico, SituacaoOS
from servicos.faturador_os import FaturadorOS, FaturamentoError
from ui_widgets.tela_os_edicao import TelaOSEdicao
from ui_widgets.theme import marcar_botao

_ROTULO_SITUACAO = {
    SituacaoOS.ABERTA: "Aberta",
    SituacaoOS.EM_EXECUCAO: "Em execucao",
    SituacaoOS.CONCLUIDA: "Concluida",
    SituacaoOS.FATURADA: "Faturada",
    SituacaoOS.CANCELADA: "Cancelada",
}

_SITUACOES_FILTRO = [(None, "Todas")] + [(s, _ROTULO_SITUACAO[s]) for s in SituacaoOS]

# KPIs exibidos (situacao, rotulo curto)
_KPIS = [
    (SituacaoOS.ABERTA, "Abertas"),
    (SituacaoOS.EM_EXECUCAO, "Em execucao"),
    (SituacaoOS.CONCLUIDA, "Concluidas"),
    (SituacaoOS.FATURADA, "Faturadas"),
    (SituacaoOS.CANCELADA, "Canceladas"),
]


class TelaAcompanhamento(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = OrdemServicoRepo()
        self._ordens: list[OrdemServico] = []
        self._kpi_labels: dict[SituacaoOS, QtWidgets.QLabel] = {}
        self._montar_ui()
        self._carregar_tecnicos()
        QtCore.QTimer.singleShot(0, self._pesquisar)

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Acompanhamento de O.S.")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        # --- filtros ---
        filtros = QtWidgets.QHBoxLayout()
        self.chk_periodo = QtWidgets.QCheckBox("Periodo")
        self.chk_periodo.setChecked(True)
        self.dt_ini = QtWidgets.QDateEdit(calendarPopup=True)
        self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_ini.setDate(QtCore.QDate.currentDate().addMonths(-1))
        self.dt_fim = QtWidgets.QDateEdit(calendarPopup=True)
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim.setDate(QtCore.QDate.currentDate())
        self.cmb_situacao = QtWidgets.QComboBox()
        for sit, rotulo in _SITUACOES_FILTRO:
            self.cmb_situacao.addItem(rotulo, sit)
        self.cmb_tecnico = QtWidgets.QComboBox()
        self.cmb_tecnico.addItem("Todos os tecnicos", None)
        btn_pesquisar = QtWidgets.QPushButton("Pesquisar")
        btn_pesquisar.clicked.connect(self._pesquisar)

        filtros.addWidget(self.chk_periodo)
        filtros.addWidget(self.dt_ini)
        filtros.addWidget(QtWidgets.QLabel("a"))
        filtros.addWidget(self.dt_fim)
        filtros.addWidget(QtWidgets.QLabel("Situacao:"))
        filtros.addWidget(self.cmb_situacao)
        filtros.addWidget(QtWidgets.QLabel("Tecnico:"))
        filtros.addWidget(self.cmb_tecnico, 1)
        filtros.addWidget(btn_pesquisar)
        layout.addLayout(filtros)

        # --- KPIs ---
        kpis = QtWidgets.QHBoxLayout()
        for sit, rotulo in _KPIS:
            card = QtWidgets.QFrame()
            card.setObjectName("kpiCard")
            cl = QtWidgets.QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            lbl_n = QtWidgets.QLabel("0")
            lbl_n.setObjectName("telaTitulo")
            lbl_n.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lbl_t = QtWidgets.QLabel(rotulo)
            lbl_t.setObjectName("telaSubtitulo")
            lbl_t.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(lbl_n)
            cl.addWidget(lbl_t)
            kpis.addWidget(card, 1)
            self._kpi_labels[sit] = lbl_n
        layout.addLayout(kpis)

        # --- grid ---
        self.tabela = QtWidgets.QTableWidget(0, 6)
        self.tabela.setHorizontalHeaderLabels(
            ["Nº O.S.", "Cliente", "Situacao", "Dt Cadastro", "Dt Prev. Term.", "Vl Total"]
        )
        self.tabela.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.doubleClicked.connect(lambda *_: self._abrir())
        layout.addWidget(self.tabela, 1)

        # --- acoes ---
        acoes = QtWidgets.QHBoxLayout()
        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setObjectName("telaSubtitulo")
        btn_iniciar = QtWidgets.QPushButton("Iniciar execucao")
        btn_iniciar.clicked.connect(lambda: self._mudar_situacao(SituacaoOS.EM_EXECUCAO))
        btn_concluir = QtWidgets.QPushButton("Concluir")
        marcar_botao(btn_concluir, "primary")
        btn_concluir.clicked.connect(lambda: self._mudar_situacao(SituacaoOS.CONCLUIDA))
        btn_reabrir = QtWidgets.QPushButton("Reabrir")
        btn_reabrir.clicked.connect(lambda: self._mudar_situacao(SituacaoOS.ABERTA))
        btn_faturar = QtWidgets.QPushButton("Faturar O.S.")
        btn_faturar.clicked.connect(self._faturar)
        btn_cancelar = QtWidgets.QPushButton("Cancelar O.S.")
        btn_cancelar.clicked.connect(self._cancelar)
        btn_abrir = QtWidgets.QPushButton("Abrir")
        btn_abrir.clicked.connect(self._abrir)
        acoes.addWidget(self.lbl_status, 1)
        for b in (btn_iniciar, btn_concluir, btn_reabrir, btn_faturar, btn_cancelar, btn_abrir):
            acoes.addWidget(b)
        layout.addLayout(acoes)

    # ----------------------------------------------------------------- helpers
    def _offline(self) -> bool:
        if ConexaoOracle.instance().offline:
            self.lbl_status.setText("Sem conexao com o banco (modo dev). Operacoes indisponiveis.")
            return True
        return False

    def _carregar_tecnicos(self) -> None:
        if ConexaoOracle.instance().offline:
            return
        try:
            for tec in TecnicoRepo().listar_ativos():
                self.cmb_tecnico.addItem(f"{tec['matricula']} - {tec['nome']}", tec["matricula"])
        except Exception:  # noqa: BLE001
            pass  # combo fica so com "Todos"; nao quebra a tela

    def _periodo(self):
        if not self.chk_periodo.isChecked():
            return None, None
        dt_ini = datetime.combine(self.dt_ini.date().toPyDate(), time.min)
        dt_fim = datetime.combine(self.dt_fim.date().toPyDate(), time.max)
        return dt_ini, dt_fim

    def _os_selecionada(self) -> OrdemServico | None:
        linha = self.tabela.currentRow()
        if linha < 0 or linha >= len(self._ordens):
            return None
        return self._ordens[linha]

    # ------------------------------------------------------------------ acoes
    def _pesquisar(self) -> None:
        if self._offline():
            self.tabela.setRowCount(0)
            for lbl in self._kpi_labels.values():
                lbl.setText("0")
            return
        dt_ini, dt_fim = self._periodo()
        cod_func = self.cmb_tecnico.currentData()
        try:
            self._ordens = self._repo.listar(
                situacao=int(self.cmb_situacao.currentData()) if self.cmb_situacao.currentData() else None,
                cod_func=cod_func,
                dt_ini=dt_ini,
                dt_fim=dt_fim,
            )
            contagem = self._repo.contar_por_situacao(cod_func=cod_func, dt_ini=dt_ini, dt_fim=dt_fim)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Acompanhamento", f"Falha ao pesquisar:\n{exc}")
            return
        self._preencher_tabela()
        for sit, lbl in self._kpi_labels.items():
            lbl.setText(str(contagem.get(int(sit), 0)))
        self.lbl_status.setText(f"{len(self._ordens)} O.S.")

    def _preencher_tabela(self) -> None:
        self.tabela.setRowCount(0)
        for os_ in self._ordens:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            self.tabela.setItem(linha, 0, QtWidgets.QTableWidgetItem(str(os_.num_os or "")))
            self.tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(str(os_.cod_cli or "")))
            self.tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(_ROTULO_SITUACAO.get(os_.situacao, "")))
            dt_cad = os_.dt_cadastro.strftime("%d/%m/%Y") if os_.dt_cadastro else ""
            self.tabela.setItem(linha, 3, QtWidgets.QTableWidgetItem(dt_cad))
            dt_prev = os_.dt_prev_term.strftime("%d/%m/%Y") if os_.dt_prev_term else ""
            self.tabela.setItem(linha, 4, QtWidgets.QTableWidgetItem(dt_prev))
            it_total = QtWidgets.QTableWidgetItem(f"{os_.vl_total:,.2f}")
            it_total.setTextAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            self.tabela.setItem(linha, 5, it_total)

    def _mudar_situacao(self, nova: SituacaoOS) -> None:
        if self._offline():
            return
        os_ = self._os_selecionada()
        if os_ is None or os_.num_os is None:
            QtWidgets.QMessageBox.information(self, "Acompanhamento", "Selecione uma O.S. na lista.")
            return
        if os_.situacao == SituacaoOS.CANCELADA:
            QtWidgets.QMessageBox.information(
                self, "Acompanhamento", "O.S. cancelada nao pode mudar de situacao."
            )
            return
        try:
            self._repo.alterar_situacao(os_.num_os, int(nova))
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Acompanhamento", f"Falha ao alterar situacao:\n{exc}")
            return
        self._pesquisar()

    def _cancelar(self) -> None:
        if self._offline():
            return
        os_ = self._os_selecionada()
        if os_ is None or os_.num_os is None:
            QtWidgets.QMessageBox.information(self, "Acompanhamento", "Selecione uma O.S. na lista.")
            return
        motivo, ok = QtWidgets.QInputDialog.getText(self, "Cancelar O.S.", "Motivo do cancelamento:")
        if not ok or not motivo.strip():
            return
        try:
            self._repo.cancelar(os_.num_os, motivo.strip())
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Acompanhamento", f"Falha ao cancelar:\n{exc}")
            return
        self._pesquisar()

    def _faturar(self) -> None:
        if self._offline():
            return
        os_ = self._os_selecionada()
        if os_ is None or os_.num_os is None:
            QtWidgets.QMessageBox.information(self, "Acompanhamento", "Selecione uma O.S. na lista.")
            return
        resp = QtWidgets.QMessageBox.question(
            self, "Faturar O.S.", f"Faturar a O.S. {os_.num_os}?"
        )
        if resp != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        usuario = (parametros_winthor.USUARIOWT or "").strip() or None
        try:
            res = FaturadorOS().faturar(os_.num_os, usuario=usuario)
        except FaturamentoError as exc:
            QtWidgets.QMessageBox.warning(self, "Faturar O.S.", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Faturar O.S.", f"Falha ao faturar:\n{exc}")
            return
        QtWidgets.QMessageBox.information(self, "Faturar O.S.", res.mensagem)
        self._pesquisar()

    def _abrir(self) -> None:
        if self._offline():
            return
        os_ = self._os_selecionada()
        if os_ is None or os_.num_os is None:
            QtWidgets.QMessageBox.information(self, "Acompanhamento", "Selecione uma O.S. na lista.")
            return
        dlg = TelaOSEdicao(os_.num_os, self)
        if dlg.exec():
            self._pesquisar()
