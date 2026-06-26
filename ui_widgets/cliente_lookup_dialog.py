"""Dialog de busca/selecao de cliente em PCCLIENT (nativa, somente leitura)."""
from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from core.cliente_repo import ClienteRepo
from ui_widgets.theme import configurar_grid


class ClienteLookupDialog(QtWidgets.QDialog):
    """Permite pesquisar um cliente e devolver dict{cod_cli, nome, cgc}."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Localizar cliente")
        self.resize(560, 420)
        self._repo = ClienteRepo()
        self._selecionado: dict | None = None
        self._montar_ui()

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        linha = QtWidgets.QHBoxLayout()
        self.txt_busca = QtWidgets.QLineEdit()
        self.txt_busca.setPlaceholderText("Código ou nome do cliente...")
        self.txt_busca.returnPressed.connect(self._pesquisar)
        btn = QtWidgets.QPushButton("Pesquisar")
        btn.clicked.connect(self._pesquisar)
        linha.addWidget(self.txt_busca, 1)
        linha.addWidget(btn)
        layout.addLayout(linha)

        self.tabela = QtWidgets.QTableWidget(0, 3)
        configurar_grid(self.tabela)
        self.tabela.setHorizontalHeaderLabels(["Código", "Nome", "CNPJ/CPF"])
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
        try:
            resultados = self._repo.buscar(self.txt_busca.text())
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Busca de cliente", f"Falha ao buscar:\n{exc}")
            return
        self.tabela.setRowCount(0)
        for item in resultados:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            it_cod = QtWidgets.QTableWidgetItem(str(item["cod_cli"]))
            it_cod.setData(QtCore.Qt.ItemDataRole.UserRole, item)
            self.tabela.setItem(linha, 0, it_cod)
            self.tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(item["nome"] or ""))
            self.tabela.setItem(linha, 2, QtWidgets.QTableWidgetItem(item.get("cgc") or ""))
        if not resultados:
            QtWidgets.QMessageBox.information(self, "Busca de cliente", "Nenhum cliente encontrado.")

    def _confirmar(self) -> None:
        linha = self.tabela.currentRow()
        if linha < 0:
            QtWidgets.QMessageBox.information(self, "Seleção", "Selecione um cliente na lista.")
            return
        self._selecionado = self.tabela.item(linha, 0).data(QtCore.Qt.ItemDataRole.UserRole)
        self.accept()

    @property
    def selecionado(self) -> dict | None:
        return self._selecionado

