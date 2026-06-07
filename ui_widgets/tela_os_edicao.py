"""Dialog: Edicao/Digitacao de Ordem de Servico (espelha a 3509 de digitacao).

Cabecalho (cliente, RCA, veiculo, KM, cobranca, plano de pagamento, dt prev.
termino, situacao, obs) + abas Servicos / Produtos / Observacoes, com
totalizadores recalculados via calculadora_os. Ao Confirmar, monta a
``OrdemServico`` e grava cabecalho + itens via ``OrdemServicoRepo``.
"""
from __future__ import annotations

from decimal import Decimal

from PyQt6 import QtCore, QtWidgets

import parametros_winthor
from core.cliente_repo import ClienteRepo
from core.conexao_oracle import ConexaoOracle
from core.ordem_servico_repo import OrdemServicoRepo
from modelos.item_produto import ItemProduto
from modelos.item_servico import ItemServico
from modelos.ordem_servico import OrdemServico, SituacaoOS
from servicos.calculadora_os import calcular_totais
from ui_widgets.cliente_lookup_dialog import ClienteLookupDialog
from ui_widgets.item_produto_dialog import ItemProdutoDialog
from ui_widgets.item_servico_dialog import ItemServicoDialog
from ui_widgets.theme import marcar_botao
from ui_widgets.veiculo_dialog import VeiculoDialog

_SITUACOES = [
    (SituacaoOS.ABERTA, "Aberta"),
    (SituacaoOS.EM_EXECUCAO, "Em execucao"),
    (SituacaoOS.CONCLUIDA, "Concluida"),
    (SituacaoOS.FATURADA, "Faturada"),
    (SituacaoOS.CANCELADA, "Cancelada"),
]


class TelaOSEdicao(QtWidgets.QDialog):
    def __init__(self, num_os: int | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = OrdemServicoRepo()
        self._num_os = num_os
        self._os = OrdemServico()
        self._servicos: list[ItemServico] = []
        self._produtos: list[ItemProduto] = []
        self.setWindowTitle(f"O.S. {num_os}" if num_os else "Nova Ordem de Servico")
        self.resize(880, 640)
        self._montar_ui()
        QtCore.QTimer.singleShot(0, self._carregar_inicial)

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Ordem de Servico")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        # --- cabecalho ---
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        linha_cli = QtWidgets.QHBoxLayout()
        self.spin_cliente = QtWidgets.QSpinBox()
        self.spin_cliente.setRange(0, 99999999)
        self.spin_cliente.setSpecialValueText("(nenhum)")
        self.lbl_cliente = QtWidgets.QLabel("")
        self.lbl_cliente.setObjectName("telaSubtitulo")
        btn_cli = QtWidgets.QPushButton("...")
        btn_cli.setFixedWidth(34)
        btn_cli.clicked.connect(self._buscar_cliente)
        linha_cli.addWidget(self.spin_cliente)
        linha_cli.addWidget(btn_cli)
        linha_cli.addWidget(self.lbl_cliente, 1)
        form.addRow("Cliente:", linha_cli)

        self.txt_filial = QtWidgets.QLineEdit()
        self.txt_filial.setMaxLength(2)
        self.txt_filial.setFixedWidth(60)
        form.addRow("Filial:", self.txt_filial)

        self.spin_rca = QtWidgets.QSpinBox()
        self.spin_rca.setRange(0, 999999)
        self.spin_rca.setSpecialValueText("(nenhum)")
        form.addRow("RCA:", self.spin_rca)

        linha_veic = QtWidgets.QHBoxLayout()
        self.spin_veiculo = QtWidgets.QSpinBox()
        self.spin_veiculo.setRange(0, 2147483647)  # limite do QSpinBox (int 32-bit)
        self.spin_veiculo.setSpecialValueText("(nenhum)")
        btn_veic = QtWidgets.QPushButton("Cadastrar/Buscar")
        btn_veic.clicked.connect(self._abrir_veiculo)
        linha_veic.addWidget(self.spin_veiculo)
        linha_veic.addWidget(btn_veic)
        linha_veic.addStretch(1)
        form.addRow("Veiculo:", linha_veic)

        self.spin_km = QtWidgets.QSpinBox()
        self.spin_km.setRange(0, 9999999)
        form.addRow("KM:", self.spin_km)

        self.txt_cob = QtWidgets.QLineEdit()
        self.txt_cob.setMaxLength(4)
        self.txt_cob.setFixedWidth(80)
        form.addRow("Cobranca:", self.txt_cob)

        self.spin_plpag = QtWidgets.QSpinBox()
        self.spin_plpag.setRange(0, 999999)
        self.spin_plpag.setSpecialValueText("(nenhum)")
        form.addRow("Plano pgto:", self.spin_plpag)

        linha_prev = QtWidgets.QHBoxLayout()
        self.dt_prev = QtWidgets.QDateTimeEdit()
        self.dt_prev.setCalendarPopup(True)
        self.dt_prev.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.dt_prev.setDateTime(QtCore.QDateTime.currentDateTime())
        self.chk_prev = QtWidgets.QCheckBox("Definir")
        linha_prev.addWidget(self.dt_prev, 1)
        linha_prev.addWidget(self.chk_prev)
        form.addRow("Dt prev. termino:", linha_prev)

        self.cmb_situacao = QtWidgets.QComboBox()
        for sit, rotulo in _SITUACOES:
            self.cmb_situacao.addItem(rotulo, sit)
        form.addRow("Situacao:", self.cmb_situacao)

        layout.addLayout(form)

        # --- abas ---
        self.abas = QtWidgets.QTabWidget()
        self.abas.addTab(self._montar_aba_servicos(), "Servicos")
        self.abas.addTab(self._montar_aba_produtos(), "Produtos")
        self.abas.addTab(self._montar_aba_obs(), "Observacoes")
        layout.addWidget(self.abas, 1)

        # --- totalizadores ---
        rodape = QtWidgets.QHBoxLayout()
        self.lbl_vl_serv = QtWidgets.QLabel("Vl Servicos: R$ 0,00")
        self.lbl_vl_prod = QtWidgets.QLabel("Vl Produtos: R$ 0,00")
        self.spin_desconto = QtWidgets.QDoubleSpinBox()
        self.spin_desconto.setRange(0, 9_999_999)
        self.spin_desconto.setDecimals(2)
        self.spin_desconto.setPrefix("Desc R$ ")
        self.spin_desconto.valueChanged.connect(self._recalcular_totais)
        self.lbl_vl_total = QtWidgets.QLabel("Vl Total: R$ 0,00")
        self.lbl_vl_total.setObjectName("telaTitulo")
        rodape.addWidget(self.lbl_vl_serv)
        rodape.addWidget(self.lbl_vl_prod)
        rodape.addWidget(self.spin_desconto)
        rodape.addStretch(1)
        rodape.addWidget(self.lbl_vl_total)
        layout.addLayout(rodape)

        # --- botoes ---
        botoes = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("Confirmar")
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botoes.accepted.connect(self._confirmar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _montar_aba_servicos(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        self.tab_serv = QtWidgets.QTableWidget(0, 5)
        self.tab_serv.setHorizontalHeaderLabels(["Servico", "Descricao", "Qtde", "P.Unit", "Total"])
        self.tab_serv.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.tab_serv.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_serv.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tab_serv.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tab_serv.doubleClicked.connect(lambda *_: self._editar_servico())
        lay.addWidget(self.tab_serv, 1)
        acoes = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Adicionar")
        marcar_botao(btn_add, "primary")
        btn_add.clicked.connect(self._adicionar_servico)
        btn_rem = QtWidgets.QPushButton("Remover")
        btn_rem.clicked.connect(self._remover_servico)
        acoes.addStretch(1)
        acoes.addWidget(btn_add)
        acoes.addWidget(btn_rem)
        lay.addLayout(acoes)
        return w

    def _montar_aba_produtos(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        self.tab_prod = QtWidgets.QTableWidget(0, 5)
        self.tab_prod.setHorizontalHeaderLabels(["Cod.Prod", "Descricao", "Qtde", "P.Unit", "Total"])
        self.tab_prod.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.tab_prod.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tab_prod.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tab_prod.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tab_prod.doubleClicked.connect(lambda *_: self._editar_produto())
        lay.addWidget(self.tab_prod, 1)
        acoes = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Adicionar")
        marcar_botao(btn_add, "primary")
        btn_add.clicked.connect(self._adicionar_produto)
        btn_rem = QtWidgets.QPushButton("Remover")
        btn_rem.clicked.connect(self._remover_produto)
        acoes.addStretch(1)
        acoes.addWidget(btn_add)
        acoes.addWidget(btn_rem)
        lay.addLayout(acoes)
        return w

    def _montar_aba_obs(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        self.txt_obs = QtWidgets.QPlainTextEdit()
        lay.addWidget(self.txt_obs)
        return w

    # ----------------------------------------------------------------- helpers
    def _offline(self) -> bool:
        if ConexaoOracle.instance().offline:
            QtWidgets.QMessageBox.information(
                self, "Sem conexao", "Sem conexao com o banco (modo dev). Operacao indisponivel."
            )
            return True
        return False

    # ------------------------------------------------------------- carga inicial
    def _carregar_inicial(self) -> None:
        self.txt_filial.setText(self._os.cod_filial or "")
        if self._num_os is None:
            self._recalcular_totais()
            return
        if ConexaoOracle.instance().offline:
            self._recalcular_totais()
            return
        try:
            carregado = self._repo.obter(self._num_os)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Carregar O.S.", f"Falha ao carregar:\n{exc}")
            self._recalcular_totais()
            return
        if carregado is None:
            QtWidgets.QMessageBox.warning(self, "Carregar O.S.", "O.S. nao encontrada.")
            return
        self._os = carregado
        self._servicos = list(carregado.servicos)
        self._produtos = list(carregado.produtos)
        self._preencher_cabecalho(carregado)
        self._preencher_servicos()
        self._preencher_produtos()
        self._recalcular_totais()

    def _preencher_cabecalho(self, os_: OrdemServico) -> None:
        self.spin_cliente.setValue(os_.cod_cli or 0)
        self.txt_filial.setText(os_.cod_filial or "")
        self.spin_rca.setValue(os_.cod_rca or 0)
        self.spin_veiculo.setValue(os_.cod_veiculo or 0)
        self.spin_km.setValue(os_.km or 0)
        self.txt_cob.setText(os_.cod_cob or "")
        self.spin_plpag.setValue(os_.cod_plpag or 0)
        if os_.dt_prev_term is not None:
            self.chk_prev.setChecked(True)
            self.dt_prev.setDateTime(QtCore.QDateTime(os_.dt_prev_term))
        idx = self.cmb_situacao.findData(os_.situacao)
        if idx >= 0:
            self.cmb_situacao.setCurrentIndex(idx)
        self.spin_desconto.setValue(float(os_.vl_desconto or 0))
        self.txt_obs.setPlainText(os_.obs or "")
        if os_.cod_cli:
            self.lbl_cliente.setText(f"Cliente {os_.cod_cli}")

    # ------------------------------------------------------------------ cliente
    def _buscar_cliente(self) -> None:
        if self._offline():
            return
        dlg = ClienteLookupDialog(self)
        if dlg.exec() and dlg.selecionado:
            self.spin_cliente.setValue(dlg.selecionado["cod_cli"])
            self.lbl_cliente.setText(dlg.selecionado["nome"] or "")

    # ------------------------------------------------------------------ veiculo
    def _abrir_veiculo(self) -> None:
        if self._offline():
            return
        cod_cli = self.spin_cliente.value() or None
        veiculo = None
        if self.spin_veiculo.value():
            try:
                from core.veiculo_repo import VeiculoRepo

                veiculo = VeiculoRepo().obter(self.spin_veiculo.value())
            except Exception:  # noqa: BLE001
                veiculo = None
        dlg = VeiculoDialog(veiculo, cod_cli, self)
        if not dlg.exec():
            return
        v = dlg.veiculo
        try:
            from core.veiculo_repo import VeiculoRepo

            repo = VeiculoRepo()
            if v.cod_veiculo is None:
                v.cod_veiculo = repo.inserir(v)
            else:
                repo.atualizar(v)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Veiculo", f"Falha ao gravar veiculo:\n{exc}")
            return
        if v.cod_veiculo:
            self.spin_veiculo.setValue(v.cod_veiculo)

    # ------------------------------------------------------------------ servicos
    def _adicionar_servico(self) -> None:
        dlg = ItemServicoDialog(None, self)
        if dlg.exec():
            self._servicos.append(dlg.item)
            self._preencher_servicos()
            self._recalcular_totais()

    def _editar_servico(self) -> None:
        linha = self.tab_serv.currentRow()
        if linha < 0 or linha >= len(self._servicos):
            return
        dlg = ItemServicoDialog(self._servicos[linha], self)
        if dlg.exec():
            self._preencher_servicos()
            self._recalcular_totais()

    def _remover_servico(self) -> None:
        linha = self.tab_serv.currentRow()
        if linha < 0 or linha >= len(self._servicos):
            QtWidgets.QMessageBox.information(self, "Remover", "Selecione um servico.")
            return
        del self._servicos[linha]
        self._preencher_servicos()
        self._recalcular_totais()

    def _preencher_servicos(self) -> None:
        self.tab_serv.setRowCount(0)
        for it in self._servicos:
            linha = self.tab_serv.rowCount()
            self.tab_serv.insertRow(linha)
            self.tab_serv.setItem(linha, 0, QtWidgets.QTableWidgetItem(str(it.cod_servico or "")))
            self.tab_serv.setItem(linha, 1, QtWidgets.QTableWidgetItem(it.descricao))
            self.tab_serv.setItem(linha, 2, QtWidgets.QTableWidgetItem(f"{it.qtde:,.2f}"))
            self.tab_serv.setItem(linha, 3, QtWidgets.QTableWidgetItem(f"{it.punit:,.2f}"))
            self.tab_serv.setItem(linha, 4, QtWidgets.QTableWidgetItem(f"{it.preco:,.2f}"))

    # ------------------------------------------------------------------ produtos
    def _adicionar_produto(self) -> None:
        dlg = ItemProdutoDialog(None, self)
        if dlg.exec():
            self._produtos.append(dlg.item)
            self._preencher_produtos()
            self._recalcular_totais()

    def _editar_produto(self) -> None:
        linha = self.tab_prod.currentRow()
        if linha < 0 or linha >= len(self._produtos):
            return
        dlg = ItemProdutoDialog(self._produtos[linha], self)
        if dlg.exec():
            self._preencher_produtos()
            self._recalcular_totais()

    def _remover_produto(self) -> None:
        linha = self.tab_prod.currentRow()
        if linha < 0 or linha >= len(self._produtos):
            QtWidgets.QMessageBox.information(self, "Remover", "Selecione um produto.")
            return
        del self._produtos[linha]
        self._preencher_produtos()
        self._recalcular_totais()

    def _preencher_produtos(self) -> None:
        self.tab_prod.setRowCount(0)
        for it in self._produtos:
            linha = self.tab_prod.rowCount()
            self.tab_prod.insertRow(linha)
            self.tab_prod.setItem(linha, 0, QtWidgets.QTableWidgetItem(str(it.cod_prod or "")))
            self.tab_prod.setItem(linha, 1, QtWidgets.QTableWidgetItem(it.descricao))
            self.tab_prod.setItem(linha, 2, QtWidgets.QTableWidgetItem(f"{it.qtde:,.2f}"))
            self.tab_prod.setItem(linha, 3, QtWidgets.QTableWidgetItem(f"{it.punit:,.2f}"))
            self.tab_prod.setItem(linha, 4, QtWidgets.QTableWidgetItem(f"{it.preco:,.2f}"))

    # ------------------------------------------------------------------ totais
    def _recalcular_totais(self) -> None:
        desconto = Decimal(str(self.spin_desconto.value()))
        vl_serv, vl_prod, vl_total = calcular_totais(self._servicos, self._produtos, desconto)
        self.lbl_vl_serv.setText(f"Vl Servicos: R$ {vl_serv:,.2f}")
        self.lbl_vl_prod.setText(f"Vl Produtos: R$ {vl_prod:,.2f}")
        self.lbl_vl_total.setText(f"Vl Total: R$ {vl_total:,.2f}")

    # ------------------------------------------------------------------ gravar
    def _confirmar(self) -> None:
        if self._offline():
            return
        os_ = self._os
        os_.num_os = self._num_os
        os_.cod_filial = self.txt_filial.text().strip()
        if not os_.cod_filial:
            QtWidgets.QMessageBox.warning(self, "Validacao", "Informe a filial.")
            self.txt_filial.setFocus()
            return
        os_.cod_cli = self.spin_cliente.value() or None
        os_.cod_rca = self.spin_rca.value() or None
        os_.cod_veiculo = self.spin_veiculo.value() or None
        os_.km = self.spin_km.value() or None
        os_.cod_cob = self.txt_cob.text().strip() or None
        os_.cod_plpag = self.spin_plpag.value() or None
        os_.dt_prev_term = self.dt_prev.dateTime().toPyDateTime() if self.chk_prev.isChecked() else None
        os_.situacao = self.cmb_situacao.currentData()
        os_.obs = self.txt_obs.toPlainText().strip() or None
        os_.vl_desconto = Decimal(str(self.spin_desconto.value()))

        vl_serv, vl_prod, vl_total = calcular_totais(self._servicos, self._produtos, os_.vl_desconto)
        os_.vl_total_servico = vl_serv
        os_.vl_total_produto = vl_prod
        os_.vl_total = vl_total
        os_.usuario_cad = (parametros_winthor.USUARIOWT or "").strip() or None

        try:
            if os_.num_os is None:
                os_.num_os = self._repo.inserir(os_)
            else:
                self._repo.atualizar(os_)
            self._repo.salvar_servicos(os_.num_os, self._servicos)
            self._repo.salvar_produtos(os_.num_os, self._produtos)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Gravar O.S.", f"Falha ao gravar:\n{exc}")
            return
        self._num_os = os_.num_os
        self.accept()

    @property
    def num_os(self) -> int | None:
        return self._num_os
