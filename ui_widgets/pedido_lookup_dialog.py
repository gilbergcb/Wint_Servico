"""Dialog de busca/selecao de pedido de venda em PCPEDC (nativa, leitura).

Filtra pelos pedidos NAO cancelados do cliente da O.S. num periodo (default:
ultimos 90 dias). Devolve dict{num_ped, data, vl_total}.
"""
from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from core.pedido_repo import PedidoRepo
from ui_widgets.theme import configurar_grid


class PedidoLookupDialog(QtWidgets.QDialog):
    """Pesquisa pedidos de venda validos de um cliente."""

    def __init__(self, cod_cli: int, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Localizar pedido de venda")
        self.resize(560, 440)
        self._cod_cli = cod_cli
        self._repo = PedidoRepo()
        self._selecionado: dict | None = None
        self._montar_ui()
        QtCore.QTimer.singleShot(0, self._pesquisar)

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        info = QtWidgets.QLabel(f"Pedidos não cancelados do cliente {self._cod_cli}")
        info.setObjectName("telaSubtitulo")
        layout.addWidget(info)

        linha = QtWidgets.QHBoxLayout()
        hoje = QtCore.QDate.currentDate()
        self.dt_ini = QtWidgets.QDateEdit(hoje.addDays(-90))
        self.dt_ini.setCalendarPopup(True)
        self.dt_ini.setDisplayFormat("dd/MM/yyyy")
        self.dt_fim = QtWidgets.QDateEdit(hoje)
        self.dt_fim.setCalendarPopup(True)
        self.dt_fim.setDisplayFormat("dd/MM/yyyy")
        btn = QtWidgets.QPushButton("Pesquisar")
        btn.clicked.connect(self._pesquisar)
        linha.addWidget(QtWidgets.QLabel("De:"))
        linha.addWidget(self.dt_ini)
        linha.addWidget(QtWidgets.QLabel("Até:"))
        linha.addWidget(self.dt_fim)
        linha.addStretch(1)
        linha.addWidget(btn)
        layout.addLayout(linha)

        self.tabela = QtWidgets.QTableWidget(0, 3)
        configurar_grid(self.tabela)
        self.tabela.setHorizontalHeaderLabels(["Pedido", "Data", "Vl Total"])
        self.tabela.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.doubleClicked.connect(lambda *_: self._confirmar())
        layout.addWidget(self.tabela, 1)

        botoes = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self._confirmar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _pesquisar(self) -> None:
        dt_ini = self.dt_ini.date().toPyDate()
        dt_fim = self.dt_fim.date().addDays(1).toPyDate()  # exclusivo: inclui o dia final
        try:
            resultados = self._repo.buscar(self._cod_cli, dt_ini=dt_ini, dt_fim=dt_fim)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Busca de pedido", f"Falha ao buscar:\n{exc}")
            return
        self.tabela.setRowCount(0)
        for item in resultados:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            it_num = QtWidgets.QTableWidgetItem(str(item["num_ped"]))
            it_num.setData(QtCore.Qt.ItemDataRole.UserRole, item)
            self.tabela.setItem(linha, 0, it_num)
            data = item["data"]
            self.tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(
                data.strftime("%d/%m/%Y") if data is not None else ""
            ))
            vl = item["vl_total"] or 0
            self.tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(f"{float(vl):,.2f}"))
        if not resultados:
            QtWidgets.QMessageBox.information(
                self, "Busca de pedido", "Nenhum pedido válido encontrado no período."
            )

    def _confirmar(self) -> None:
        linha = self.tabela.currentRow()
        if linha < 0:
            QtWidgets.QMessageBox.information(self, "Seleção", "Selecione um pedido na lista.")
            return
        self._selecionado = self.tabela.item(linha, 0).data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()

    @property
    def selecionado(self) -> dict | None:
        return self._selecionado

