"""Tela: Acompanhamento das Ordens de Servico.

Painel com filtros (periodo, situacao, tecnico), KPIs por situacao, grid das
O.S. e acoes de avanco de status (Iniciar execucao / Concluir / Reabrir /
Cancelar). Duplo-clique abre a edicao da O.S.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from PyQt6 import QtCore, QtGui, QtWidgets

import parametros_winthor
from core.conexao_oracle import ConexaoOracle
from core.os_repo_factory import obter_os_repo
from core.tecnico_repo import TecnicoRepo
from modelos.ordem_servico import OrdemServico, SituacaoOS
from servicos.faturador_os import FaturadorOS, FaturamentoError
from ui_widgets.tela_os_edicao import TelaOSEdicao
from ui_widgets.theme import StatusBadgeDelegate, configurar_combo, configurar_grid, marcar_botao

_ROTULO_SITUACAO = {
    SituacaoOS.ABERTA: "Aberta",
    SituacaoOS.EM_EXECUCAO: "Em execução",
    SituacaoOS.CANCELADA: "Cancelada",
    SituacaoOS.CONCLUIDA: "Concluída",
    SituacaoOS.FATURADA: "Faturada",
}

_SITUACOES_FILTRO = [(None, "Todas")] + [(s, _ROTULO_SITUACAO[s]) for s in SituacaoOS]

_PERIODOS = [
    ("hoje", "Hoje"),
    ("semana", "Semana Atual"),
    ("mes", "Mês Atual"),
    ("trimestre", "Trimestre Atual"),
    ("ano", "Ano Atual"),
]

# KPIs exibidos (situacao, rotulo curto)
_KPIS = [
    (SituacaoOS.ABERTA, "Abertas"),
    (SituacaoOS.EM_EXECUCAO, "Em execução"),
    (SituacaoOS.CANCELADA, "Canceladas"),
    (SituacaoOS.CONCLUIDA, "Concluídas"),
    (SituacaoOS.FATURADA, "Faturadas"),
    (None, "Todos"),
]

_COR_STATUS = {
    None: "blue",
    SituacaoOS.ABERTA: "orange",
    SituacaoOS.EM_EXECUCAO: "yellow",
    SituacaoOS.CANCELADA: "red",
    SituacaoOS.CONCLUIDA: "light_green",
    SituacaoOS.FATURADA: "dark_green",
}

_COR_BADGE = {
    None: ("#dbeafe", "#1d4ed8"),
    SituacaoOS.ABERTA: ("#ffedd5", "#9a3412"),
    SituacaoOS.EM_EXECUCAO: ("#fef9c3", "#854d0e"),
    SituacaoOS.CANCELADA: ("#fee2e2", "#991b1b"),
    SituacaoOS.CONCLUIDA: ("#dcfce7", "#166534"),
    SituacaoOS.FATURADA: ("#dcfce7", "#14532d"),
}


def _intervalo(chave: str) -> tuple[datetime, datetime]:
    hoje = date.today()
    if chave == "hoje":
        ini, fim = hoje, hoje + timedelta(days=1)
    elif chave == "semana":
        ini = hoje - timedelta(days=hoje.weekday())
        fim = ini + timedelta(days=7)
    elif chave == "mes":
        ini = hoje.replace(day=1)
        fim = date(ini.year + 1, 1, 1) if ini.month == 12 else date(ini.year, ini.month + 1, 1)
    elif chave == "trimestre":
        mes_ini = ((hoje.month - 1) // 3) * 3 + 1
        ini = date(hoje.year, mes_ini, 1)
        prox = mes_ini + 3
        fim = date(hoje.year + 1, 1, 1) if prox > 12 else date(hoje.year, prox, 1)
    else:
        ini = date(hoje.year, 1, 1)
        fim = date(hoje.year + 1, 1, 1)
    return datetime.combine(ini, time.min), datetime.combine(fim, time.min)


class TelaAcompanhamento(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._ordens: list[OrdemServico] = []
        self._kpi_labels: dict[SituacaoOS | None, QtWidgets.QLabel] = {}
        self._kpi_cards: dict[SituacaoOS | None, QtWidgets.QFrame] = {}
        self._periodo_chave = "mes"
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
        self.cmb_periodo = QtWidgets.QComboBox()
        configurar_combo(self.cmb_periodo, destaque=True)
        for chave, rotulo in _PERIODOS:
            self.cmb_periodo.addItem(rotulo, chave)
        self.cmb_periodo.setCurrentIndex(self.cmb_periodo.findData(self._periodo_chave))
        self.cmb_periodo.setFixedWidth(176)
        self.cmb_periodo.currentIndexChanged.connect(self._alterar_periodo)
        self.cmb_situacao = QtWidgets.QComboBox()
        configurar_combo(self.cmb_situacao)
        for sit, rotulo in _SITUACOES_FILTRO:
            self.cmb_situacao.addItem(rotulo, sit)
        self.cmb_tecnico = QtWidgets.QComboBox()
        configurar_combo(self.cmb_tecnico)
        self.cmb_tecnico.addItem("Todos os técnicos", None)
        btn_pesquisar = QtWidgets.QPushButton("Pesquisar")
        btn_pesquisar.clicked.connect(self._pesquisar)

        filtros.addWidget(QtWidgets.QLabel("Situação:"))
        filtros.addWidget(self.cmb_situacao)
        filtros.addWidget(QtWidgets.QLabel("Técnico:"))
        filtros.addWidget(self.cmb_tecnico, 1)
        filtros.addWidget(self.cmb_periodo)
        filtros.addWidget(btn_pesquisar)
        layout.addLayout(filtros)

        # --- KPIs ---
        kpis = QtWidgets.QHBoxLayout()
        kpis.setSpacing(0)
        for indice, (sit, rotulo) in enumerate(_KPIS):
            card = QtWidgets.QFrame()
            card.setObjectName("kpiCard")
            card.setProperty(
                "segment",
                "first" if indice == 0 else "last" if indice == len(_KPIS) - 1 else "middle",
            )
            card.setProperty("active", "false")
            card.setProperty("clickable", "true")
            card.setProperty("statusColor", _COR_STATUS[sit])
            card.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda event, s=sit: self._filtrar_por_card(s)  # type: ignore[method-assign]
            cl = QtWidgets.QVBoxLayout(card)
            cl.setContentsMargins(24, 14, 24, 14)
            cl.setSpacing(8)
            linha_rotulo = QtWidgets.QHBoxLayout()
            dot = QtWidgets.QLabel()
            dot.setObjectName("statusDot")
            dot.setProperty("statusColor", _COR_STATUS[sit])
            dot.setFixedSize(10, 10)
            lbl_t = QtWidgets.QLabel(rotulo)
            lbl_t.setObjectName("telaSubtitulo")
            linha_rotulo.addWidget(dot)
            linha_rotulo.addWidget(lbl_t)
            linha_rotulo.addStretch(1)
            lbl_n = QtWidgets.QLabel("0")
            lbl_n.setObjectName("telaTitulo")
            lbl_n.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
            cl.addLayout(linha_rotulo)
            cl.addWidget(lbl_n)
            kpis.addWidget(card, 1)
            self._kpi_labels[sit] = lbl_n
            self._kpi_cards[sit] = card
        layout.addLayout(kpis)

        # --- grid ---
        self.tabela = QtWidgets.QTableWidget(0, 12)
        configurar_grid(self.tabela)
        self.tabela.setItemDelegateForColumn(6, StatusBadgeDelegate(self.tabela))
        self.tabela.setHorizontalHeaderLabels(
            [
                "Nº O.S.", "Cód.Cliente", "Cliente", "Placa veículo", "Descrição do veículo",
                "KM", "Situação", "Dt Cadastro", "Dt Prev. Term.", "Vl Serviços",
                "Vl Produtos", "Vl Total",
            ]
        )
        cab = self.tabela.horizontalHeader()
        for col in range(self.tabela.columnCount()):
            cab.setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeMode.Interactive)
        cab.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tabela.setColumnWidth(0, 100)
        self.tabela.setColumnWidth(1, 100)
        self.tabela.setColumnWidth(2, 390)
        self.tabela.setColumnWidth(3, 100)
        self.tabela.setColumnWidth(4, 250)
        self.tabela.setColumnWidth(5, 80)
        self.tabela.setColumnWidth(6, 100)
        self.tabela.setColumnWidth(7, 100)
        self.tabela.setColumnWidth(8, 105)
        self.tabela.setColumnWidth(9, 100)
        self.tabela.setColumnWidth(10, 100)
        self.tabela.setColumnWidth(11, 100)
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.doubleClicked.connect(lambda *_: self._abrir())
        layout.addWidget(self.tabela, 1)

        # --- acoes ---
        acoes = QtWidgets.QHBoxLayout()
        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setObjectName("telaSubtitulo")
        btn_iniciar = QtWidgets.QPushButton("Iniciar execução")
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
        btn_abrir = QtWidgets.QPushButton("Editar")
        btn_abrir.clicked.connect(self._abrir)
        acoes.addWidget(self.lbl_status, 1)
        for b in (btn_iniciar, btn_concluir, btn_reabrir, btn_faturar, btn_cancelar, btn_abrir):
            acoes.addWidget(b)
        layout.addLayout(acoes)

    # ----------------------------------------------------------------- helpers
    def _offline(self) -> bool:
        if ConexaoOracle.instance().offline:
            self.lbl_status.setText("Sem conexão com o banco (modo dev). Operações indisponíveis.")
            return True
        return False

    def _carregar_tecnicos(self) -> None:
        atual = self.cmb_tecnico.currentData()
        self.cmb_tecnico.blockSignals(True)
        self.cmb_tecnico.clear()
        self.cmb_tecnico.addItem("Todos os técnicos", None)
        if ConexaoOracle.instance().offline:
            self.cmb_tecnico.blockSignals(False)
            return
        try:
            for tec in TecnicoRepo().listar_ativos():
                self.cmb_tecnico.addItem(f"{tec['matricula']} - {tec['nome']}", tec["matricula"])
        except Exception:  # noqa: BLE001
            pass  # combo fica só com "Todos"; não quebra a tela
        idx = self.cmb_tecnico.findData(atual)
        if idx >= 0:
            self.cmb_tecnico.setCurrentIndex(idx)
        self.cmb_tecnico.blockSignals(False)

    def recarregar_configuracoes(self) -> None:
        self._carregar_tecnicos()
        self._pesquisar()

    def _periodo(self):
        return _intervalo(self._periodo_chave)

    def _alterar_periodo(self, _indice: int = -1) -> None:
        self._periodo_chave = self.cmb_periodo.currentData()
        self._pesquisar()

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
            self._atualizar_cards_selecionados()
            return
        dt_ini, dt_fim = self._periodo()
        cod_func = self.cmb_tecnico.currentData()
        try:
            repo = obter_os_repo()
            self._ordens = repo.listar(
                situacao=int(self.cmb_situacao.currentData()) if self.cmb_situacao.currentData() else None,
                cod_func=cod_func,
                dt_ini=dt_ini,
                dt_fim=dt_fim,
            )
            contagem = repo.contar_por_situacao(cod_func=cod_func, dt_ini=dt_ini, dt_fim=dt_fim)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Acompanhamento", f"Falha ao pesquisar:\n{exc}")
            return
        self._preencher_tabela()
        total = sum(contagem.values())
        for sit, lbl in self._kpi_labels.items():
            lbl.setText(str(total if sit is None else contagem.get(int(sit), 0)))
        self.lbl_status.setText(f"{len(self._ordens)} O.S.")
        self._atualizar_cards_selecionados()

    def _filtrar_por_card(self, situacao: SituacaoOS | None) -> None:
        indice = 0 if situacao is None else self.cmb_situacao.findData(situacao)
        if indice >= 0:
            self.cmb_situacao.setCurrentIndex(indice)
        self._pesquisar()

    def _atualizar_cards_selecionados(self) -> None:
        selecionado = self.cmb_situacao.currentData()
        for sit, card in self._kpi_cards.items():
            ativo = sit == selecionado
            card.setProperty("active", "true" if ativo else "false")
            card.style().unpolish(card)
            card.style().polish(card)
            for label in card.findChildren(QtWidgets.QLabel):
                label.setProperty("activeCard", "true" if ativo else "false")
                label.style().unpolish(label)
                label.style().polish(label)

    def _preencher_tabela(self) -> None:
        self.tabela.setRowCount(0)
        for os_ in self._ordens:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            self.tabela.setItem(linha, 0, QtWidgets.QTableWidgetItem(str(os_.num_os or "")))
            self.tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(str(os_.cod_cli or "")))
            self.tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(os_.cliente_nome or ""))
            self.tabela.setItem(linha, 3, QtWidgets.QTableWidgetItem(os_.placa_veiculo or ""))
            self.tabela.setItem(linha, 4, QtWidgets.QTableWidgetItem(os_.descricao_veiculo or ""))
            self.tabela.setItem(linha, 5, QtWidgets.QTableWidgetItem(str(os_.km or "")))
            self.tabela.setItem(linha, 6, self._item_situacao(os_.situacao))
            dt_cad = os_.dt_cadastro.strftime("%d/%m/%Y") if os_.dt_cadastro else ""
            self.tabela.setItem(linha, 7, QtWidgets.QTableWidgetItem(dt_cad))
            dt_prev = os_.dt_prev_term.strftime("%d/%m/%Y") if os_.dt_prev_term else ""
            self.tabela.setItem(linha, 8, QtWidgets.QTableWidgetItem(dt_prev))
            self._set_valor(linha, 9, os_.vl_total_servico)
            self._set_valor(linha, 10, os_.vl_total_produto)
            self._set_valor(linha, 11, os_.vl_total)

    def _set_valor(self, linha: int, coluna: int, valor) -> None:  # noqa: ANN001
        item = QtWidgets.QTableWidgetItem(f"{valor:,.2f}")
        item.setTextAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.tabela.setItem(linha, coluna, item)

    def _item_situacao(self, situacao: SituacaoOS) -> QtWidgets.QTableWidgetItem:
        item = QtWidgets.QTableWidgetItem(_ROTULO_SITUACAO.get(situacao, ""))
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Weight.Bold))
        fundo, texto = _COR_BADGE.get(situacao, ("#f3f4f6", "#374151"))
        item.setForeground(QtGui.QColor(texto))
        item.setData(QtCore.Qt.ItemDataRole.UserRole, (fundo, texto))
        return item

    def _mudar_situacao(self, nova: SituacaoOS) -> None:
        if self._offline():
            return
        os_ = self._os_selecionada()
        if os_ is None or os_.num_os is None:
            QtWidgets.QMessageBox.information(self, "Acompanhamento", "Selecione uma O.S. na lista.")
            return
        if os_.situacao == SituacaoOS.CANCELADA:
            QtWidgets.QMessageBox.information(
                self, "Acompanhamento", "O.S. cancelada não pode mudar de situação."
            )
            return
        try:
            obter_os_repo().alterar_situacao(os_.num_os, int(nova))
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Acompanhamento", f"Falha ao alterar situação:\n{exc}")
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
            obter_os_repo().cancelar(os_.num_os, motivo.strip())
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

