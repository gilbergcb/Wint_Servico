"""Tela: Cadastro de Servico (PCM_SERVICO) - espelha a rotina 3501.

Lista/pesquisa de servicos + acoes Incluir / Editar / Inativar, abrindo o
ServicoDialog. Acesso a dados via ServicoRepo.
"""
from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from core.conexao_oracle import ConexaoOracle
from core.servico_repo import ServicoRepo
from modelos.servico import Servico
from ui_widgets.servico_dialog import ServicoDialog
from ui_widgets.theme import configurar_grid, marcar_botao


class TelaCadastroServico(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = ServicoRepo()
        self._servicos: list[Servico] = []
        self._montar_ui()

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Cadastro de Serviço")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        # --- barra de busca ---
        busca = QtWidgets.QHBoxLayout()
        self.txt_busca = QtWidgets.QLineEdit()
        self.txt_busca.setPlaceholderText("Código ou descrição do serviço...")
        self.txt_busca.returnPressed.connect(self._pesquisar)
        self.chk_somente_ativos = QtWidgets.QCheckBox("Somente ativos")
        self.chk_somente_ativos.setChecked(True)
        btn_pesquisar = QtWidgets.QPushButton("Pesquisar")
        btn_pesquisar.clicked.connect(self._pesquisar)
        busca.addWidget(self.txt_busca, 1)
        busca.addWidget(self.chk_somente_ativos)
        busca.addWidget(btn_pesquisar)
        layout.addLayout(busca)

        # --- tabela ---
        self.tabela = QtWidgets.QTableWidget(0, 5)
        configurar_grid(self.tabela)
        self.tabela.setHorizontalHeaderLabels(["Código", "Descrição", "Preço", "ISS %", "Ativo"])
        cab = self.tabela.horizontalHeader()
        cab.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tabela.doubleClicked.connect(lambda *_: self._editar())
        layout.addWidget(self.tabela, 1)

        # --- acoes ---
        acoes = QtWidgets.QHBoxLayout()
        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setObjectName("telaSubtitulo")
        btn_incluir = QtWidgets.QPushButton("Incluir")
        marcar_botao(btn_incluir, "primary")
        btn_incluir.clicked.connect(self._incluir)
        btn_editar = QtWidgets.QPushButton("Editar")
        btn_editar.clicked.connect(self._editar)
        btn_inativar = QtWidgets.QPushButton("Inativar")
        btn_inativar.clicked.connect(self._inativar)
        acoes.addWidget(self.lbl_status, 1)
        acoes.addWidget(btn_incluir)
        acoes.addWidget(btn_editar)
        acoes.addWidget(btn_inativar)
        layout.addLayout(acoes)

        QtCore.QTimer.singleShot(0, self._pesquisar)

    # ----------------------------------------------------------------- helpers
    def _offline(self) -> bool:
        if ConexaoOracle.instance().offline:
            self.lbl_status.setText("Sem conexão com o banco (modo dev). Operações indisponíveis.")
            return True
        return False

    def _servico_selecionado(self) -> Servico | None:
        linha = self.tabela.currentRow()
        if linha < 0 or linha >= len(self._servicos):
            return None
        return self._servicos[linha]

    # ------------------------------------------------------------------ acoes
    def _pesquisar(self) -> None:
        if self._offline():
            self.tabela.setRowCount(0)
            return
        ativo = True if self.chk_somente_ativos.isChecked() else None
        try:
            self._servicos = self._repo.listar(self.txt_busca.text(), ativo=ativo)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Pesquisar serviços", f"Falha ao pesquisar:\n{exc}")
            return
        self._preencher_tabela()
        self.lbl_status.setText(f"{len(self._servicos)} serviço(s)")

    def _preencher_tabela(self) -> None:
        self.tabela.setRowCount(0)
        for s in self._servicos:
            linha = self.tabela.rowCount()
            self.tabela.insertRow(linha)
            self.tabela.setItem(linha, 0, QtWidgets.QTableWidgetItem(str(s.cod_servico or "")))
            self.tabela.setItem(linha, 1, QtWidgets.QTableWidgetItem(s.descricao))
            it_preco = QtWidgets.QTableWidgetItem(f"{s.preco_padrao:,.2f}")
            it_preco.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            self.tabela.setItem(linha, 2, it_preco)
            self.tabela.setItem(linha, 3, QtWidgets.QTableWidgetItem(f"{s.perc_aliq_iss:.2f}"))
            self.tabela.setItem(linha, 4, QtWidgets.QTableWidgetItem("Sim" if s.ativo else "Não"))

    def _incluir(self) -> None:
        if self._offline():
            return
        dlg = ServicoDialog(None, self)
        if dlg.exec():
            try:
                self._repo.inserir(dlg.servico)
            except Exception as exc:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "Incluir serviço", f"Falha ao gravar:\n{exc}")
                return
            self._pesquisar()

    def _editar(self) -> None:
        if self._offline():
            return
        s = self._servico_selecionado()
        if s is None:
            QtWidgets.QMessageBox.information(self, "Editar", "Selecione um serviço na lista.")
            return
        dlg = ServicoDialog(s, self)
        if dlg.exec():
            try:
                self._repo.atualizar(dlg.servico)
            except Exception as exc:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "Editar serviço", f"Falha ao gravar:\n{exc}")
                return
            self._pesquisar()

    def _inativar(self) -> None:
        if self._offline():
            return
        s = self._servico_selecionado()
        if s is None or s.cod_servico is None:
            QtWidgets.QMessageBox.information(self, "Inativar", "Selecione um serviço na lista.")
            return
        resp = QtWidgets.QMessageBox.question(
            self, "Inativar serviço", f"Inativar o serviço '{s.descricao}'?"
        )
        if resp != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            self._repo.inativar(s.cod_servico)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Inativar serviço", f"Falha:\n{exc}")
            return
        self._pesquisar()

