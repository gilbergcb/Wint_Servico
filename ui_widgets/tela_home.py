"""Tela: Início (painel/dashboard).

Mostra a quantidade de O.S. (cards por situação) e O.S. por serviço, com
seletor de período predefinido.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PyQt6 import QtCore, QtWidgets

from core.conexao_oracle import ConexaoOracle
from core.os_repo_factory import obter_os_repo
from core.relatorio_repo import RelatorioRepo
from modelos.ordem_servico import SituacaoOS
from ui_widgets.theme import configurar_combo, configurar_grid

_PERIODOS = [
    ("hoje", "Hoje"),
    ("semana", "Semana Atual"),
    ("mes", "Mês Atual"),
    ("trimestre", "Trimestre Atual"),
    ("ano", "Ano Atual"),
]

_CARDS = [
    (None, "Todos"),
    (SituacaoOS.ABERTA, "Abertas"),
    (SituacaoOS.EM_EXECUCAO, "Em execução"),
    (SituacaoOS.CANCELADA, "Canceladas"),
    (SituacaoOS.CONCLUIDA, "Concluídas"),
    (SituacaoOS.FATURADA, "Faturadas"),
]

_COR_STATUS = {
    None: "blue",
    SituacaoOS.ABERTA: "orange",
    SituacaoOS.EM_EXECUCAO: "yellow",
    SituacaoOS.CANCELADA: "red",
    SituacaoOS.CONCLUIDA: "light_green",
    SituacaoOS.FATURADA: "dark_green",
}


def _intervalo(chave: str) -> tuple[datetime, datetime]:
    hoje = date.today()
    if chave == "hoje":
        ini, fim = hoje, hoje + timedelta(days=1)
    elif chave == "semana":
        ini = hoje - timedelta(days=hoje.weekday())  # segunda-feira
        fim = ini + timedelta(days=7)
    elif chave == "mes":
        ini = hoje.replace(day=1)
        fim = date(ini.year + 1, 1, 1) if ini.month == 12 else date(ini.year, ini.month + 1, 1)
    elif chave == "trimestre":
        mes_ini = ((hoje.month - 1) // 3) * 3 + 1
        ini = date(hoje.year, mes_ini, 1)
        prox = mes_ini + 3
        fim = date(hoje.year + 1, 1, 1) if prox > 12 else date(hoje.year, prox, 1)
    else:  # ano atual
        ini = date(hoje.year, 1, 1)
        fim = date(hoje.year + 1, 1, 1)
    minimo = datetime.min.time()
    return datetime.combine(ini, minimo), datetime.combine(fim, minimo)


class TelaHome(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._rel_repo = RelatorioRepo()
        self._periodo = "mes"
        self._cards: dict[object, QtWidgets.QLabel] = {}
        self._montar_ui()
        QtCore.QTimer.singleShot(0, self._atualizar)

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        topo = QtWidgets.QHBoxLayout()
        titulo = QtWidgets.QLabel("Início")
        titulo.setObjectName("telaTitulo")
        topo.addWidget(titulo)
        topo.addStretch(1)
        self.cmb_periodo = QtWidgets.QComboBox()
        configurar_combo(self.cmb_periodo, destaque=True)
        for chave, rotulo in _PERIODOS:
            self.cmb_periodo.addItem(rotulo, chave)
        self.cmb_periodo.setCurrentIndex(self.cmb_periodo.findData(self._periodo))
        self.cmb_periodo.setFixedWidth(176)
        self.cmb_periodo.currentIndexChanged.connect(self._set_periodo)
        topo.addWidget(self.cmb_periodo)
        layout.addLayout(topo)

        self.lbl_periodo = QtWidgets.QLabel("")
        self.lbl_periodo.setObjectName("telaSubtitulo")
        layout.addWidget(self.lbl_periodo)

        # --- cards de quantidade ---
        cards = QtWidgets.QHBoxLayout()
        for chave, rotulo in _CARDS:
            card = QtWidgets.QFrame()
            card.setObjectName("kpiCard")
            card.setProperty("active", "false")
            card.setProperty("statusColor", _COR_STATUS[chave])
            cl = QtWidgets.QVBoxLayout(card)
            cl.setContentsMargins(24, 14, 24, 14)
            cl.setSpacing(8)
            linha_rotulo = QtWidgets.QHBoxLayout()
            dot = QtWidgets.QLabel()
            dot.setObjectName("statusDot")
            dot.setProperty("statusColor", _COR_STATUS[chave])
            dot.setFixedSize(10, 10)
            t = QtWidgets.QLabel(rotulo)
            t.setObjectName("telaSubtitulo")
            linha_rotulo.addWidget(dot)
            linha_rotulo.addWidget(t)
            linha_rotulo.addStretch(1)
            n = QtWidgets.QLabel("0")
            n.setObjectName("telaTitulo")
            n.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
            cl.addLayout(linha_rotulo)
            cl.addWidget(n)
            cards.addWidget(card, 1)
            self._cards[chave] = n
        layout.addLayout(cards)

        # --- O.S. por serviço ---
        sub = QtWidgets.QLabel("O.S. por serviço (mais executados no período)")
        sub.setObjectName("telaSubtitulo")
        layout.addWidget(sub)
        self.tabela = QtWidgets.QTableWidget(0, 4)
        configurar_grid(self.tabela)
        self.tabela.setHorizontalHeaderLabels(["Cód.Serviço", "Descrição", "Qtde", "Vl Total"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.doubleClicked.connect(lambda *_: self._abrir_ordens_servico())
        layout.addWidget(self.tabela, 1)

    # ----------------------------------------------------------------- logica
    def _set_periodo(self, _indice: int = -1) -> None:
        self._periodo = self.cmb_periodo.currentData()
        self._atualizar()

    def _atualizar(self) -> None:
        dt_ini, dt_fim = _intervalo(self._periodo)
        self.lbl_periodo.setText(
            f"Período: {dt_ini.strftime('%d/%m/%Y')} a {(dt_fim - timedelta(days=1)).strftime('%d/%m/%Y')}"
        )
        if ConexaoOracle.instance().offline:
            self.lbl_periodo.setText("Sem conexão com o banco (modo dev).")
            for lbl in self._cards.values():
                lbl.setText("-")
            self.tabela.setRowCount(0)
            return
        try:
            contagem = obter_os_repo().contar_por_situacao(dt_ini=dt_ini, dt_fim=dt_fim)
            _, linhas = self._rel_repo.servicos_mais_executados(dt_ini, dt_fim, limite=10)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Início", f"Falha ao carregar painel:\n{exc}")
            return
        total = sum(contagem.values())
        for chave, lbl in self._cards.items():
            lbl.setText(str(total if chave is None else contagem.get(int(chave), 0)))
        self._preencher(linhas)

    def _preencher(self, linhas: list[list]) -> None:
        self.tabela.setRowCount(0)
        for valores in linhas:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            for col, valor in enumerate(valores):
                item = QtWidgets.QTableWidgetItem(str(valor))
                if col in (2, 3):
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                self.tabela.setItem(linha, col, item)

    def _abrir_ordens_servico(self) -> None:
        linha = self.tabela.currentRow()
        if linha < 0:
            return
        item_cod = self.tabela.item(linha, 0)
        if item_cod is None:
            return
        try:
            cod_servico = int(item_cod.text())
        except ValueError:
            return
        descricao = self.tabela.item(linha, 1).text() if self.tabela.item(linha, 1) else ""
        dt_ini, dt_fim = _intervalo(self._periodo)
        try:
            cabecalho, linhas = self._rel_repo.ordens_por_servico(cod_servico, dt_ini, dt_fim)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Ordens de serviço", f"Falha ao carregar O.S.:\n{exc}")
            return

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(f"O.S. do serviço {cod_servico}")
        dlg.resize(820, 460)
        layout = QtWidgets.QVBoxLayout(dlg)

        titulo = QtWidgets.QLabel(f"{cod_servico} - {descricao}")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        periodo = QtWidgets.QLabel(
            f"Período: {dt_ini.strftime('%d/%m/%Y')} a {(dt_fim - timedelta(days=1)).strftime('%d/%m/%Y')}"
        )
        periodo.setObjectName("telaSubtitulo")
        layout.addWidget(periodo)

        tabela = QtWidgets.QTableWidget(0, len(cabecalho))
        configurar_grid(tabela)
        tabela.setHorizontalHeaderLabels(cabecalho)
        tabela.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        tabela.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        for valores in linhas:
            row = tabela.rowCount()
            tabela.insertRow(row)
            for col, valor in enumerate(valores):
                item = QtWidgets.QTableWidgetItem(str(valor))
                if col in (0, 2, 5):
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                tabela.setItem(row, col, item)
        layout.addWidget(tabela, 1)

        status = QtWidgets.QLabel(f"{len(linhas)} ordem(ns) de serviço")
        status.setObjectName("telaSubtitulo")
        layout.addWidget(status)

        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText("Fechar")
        botoes.rejected.connect(dlg.reject)
        layout.addWidget(botoes)
        dlg.exec()

