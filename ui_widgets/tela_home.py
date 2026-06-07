"""Tela: Inicio (painel/dashboard).

Mostra a quantidade de O.S. (cards por situacao) e O.S. por servico, com
seletor de periodo pre-definido: Hoje, Semana atual, Mes atual, Trimestre atual.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PyQt6 import QtCore, QtWidgets

from core.conexao_oracle import ConexaoOracle
from core.ordem_servico_repo import OrdemServicoRepo
from core.relatorio_repo import RelatorioRepo
from modelos.ordem_servico import SituacaoOS
from ui_widgets.theme import marcar_botao

_PERIODOS = [("hoje", "Hoje"), ("semana", "Semana atual"), ("mes", "Mes atual"), ("trimestre", "Trimestre atual")]

_CARDS = [
    (None, "Total O.S."),
    (SituacaoOS.ABERTA, "Abertas"),
    (SituacaoOS.EM_EXECUCAO, "Em execucao"),
    (SituacaoOS.CONCLUIDA, "Concluidas"),
    (SituacaoOS.FATURADA, "Faturadas"),
]


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
    else:  # trimestre atual
        mes_ini = ((hoje.month - 1) // 3) * 3 + 1
        ini = date(hoje.year, mes_ini, 1)
        prox = mes_ini + 3
        fim = date(hoje.year + 1, 1, 1) if prox > 12 else date(hoje.year, prox, 1)
    minimo = datetime.min.time()
    return datetime.combine(ini, minimo), datetime.combine(fim, minimo)


class TelaHome(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._os_repo = OrdemServicoRepo()
        self._rel_repo = RelatorioRepo()
        self._periodo = "mes"
        self._cards: dict[object, QtWidgets.QLabel] = {}
        self._btns: dict[str, QtWidgets.QPushButton] = {}
        self._montar_ui()
        QtCore.QTimer.singleShot(0, self._atualizar)

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        topo = QtWidgets.QHBoxLayout()
        titulo = QtWidgets.QLabel("Inicio")
        titulo.setObjectName("telaTitulo")
        topo.addWidget(titulo)
        topo.addStretch(1)
        for chave, rotulo in _PERIODOS:
            b = QtWidgets.QPushButton(rotulo)
            b.setCheckable(True)
            b.setChecked(chave == self._periodo)
            marcar_botao(b, "seg")
            b.clicked.connect(lambda _=False, c=chave: self._set_periodo(c))
            topo.addWidget(b)
            self._btns[chave] = b
        layout.addLayout(topo)

        self.lbl_periodo = QtWidgets.QLabel("")
        self.lbl_periodo.setObjectName("telaSubtitulo")
        layout.addWidget(self.lbl_periodo)

        # --- cards de quantidade ---
        cards = QtWidgets.QHBoxLayout()
        for chave, rotulo in _CARDS:
            card = QtWidgets.QFrame()
            card.setObjectName("kpiCard")
            cl = QtWidgets.QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            n = QtWidgets.QLabel("0")
            n.setObjectName("telaTitulo")
            n.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            t = QtWidgets.QLabel(rotulo)
            t.setObjectName("telaSubtitulo")
            t.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(n)
            cl.addWidget(t)
            cards.addWidget(card, 1)
            self._cards[chave] = n
        layout.addLayout(cards)

        # --- O.S. por servico ---
        sub = QtWidgets.QLabel("O.S. por servico (mais executados no periodo)")
        sub.setObjectName("telaSubtitulo")
        layout.addWidget(sub)
        self.tabela = QtWidgets.QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(["Cod.Servico", "Descricao", "Qtde", "Vl Total"])
        self.tabela.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.tabela, 1)

    # ----------------------------------------------------------------- logica
    def _set_periodo(self, chave: str) -> None:
        self._periodo = chave
        for c, b in self._btns.items():
            b.setChecked(c == chave)
        self._atualizar()

    def _atualizar(self) -> None:
        dt_ini, dt_fim = _intervalo(self._periodo)
        self.lbl_periodo.setText(
            f"Periodo: {dt_ini.strftime('%d/%m/%Y')} a {(dt_fim - timedelta(days=1)).strftime('%d/%m/%Y')}"
        )
        if ConexaoOracle.instance().offline:
            self.lbl_periodo.setText("Sem conexao com o banco (modo dev).")
            for lbl in self._cards.values():
                lbl.setText("-")
            self.tabela.setRowCount(0)
            return
        try:
            contagem = self._os_repo.contar_por_situacao(dt_ini=dt_ini, dt_fim=dt_fim)
            _, linhas = self._rel_repo.servicos_mais_executados(dt_ini, dt_fim, limite=10)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Inicio", f"Falha ao carregar painel:\n{exc}")
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
