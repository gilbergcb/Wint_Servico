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
from core.combos_repo import CombosRepo
from core.conexao_oracle import ConexaoOracle
from core.os_repo_factory import obter_os_repo
from core.parametro_repo import ParametroRepo
from core.pedido_repo import PedidoRepo
from core.permissao_repo import CONTROLE_DISPENSA_PEDIDO, PermissaoRepo
from core.tecnico_repo import TecnicoRepo
from modelos.item_produto import ItemProduto
from modelos.item_servico import ItemServico
from modelos.ordem_servico import OrdemServico, SituacaoOS
from servicos.calculadora_os import calcular_totais
from ui_widgets.cliente_lookup_dialog import ClienteLookupDialog
from ui_widgets.item_produto_dialog import ItemProdutoDialog
from ui_widgets.item_servico_dialog import ItemServicoDialog
from ui_widgets.pedido_lookup_dialog import PedidoLookupDialog
from ui_widgets.theme import (
    configurar_botao_busca,
    configurar_combo,
    configurar_descricao_lookup,
    configurar_grid,
    marcar_botao,
    rotulo_campo,
)
from ui_widgets.veiculo_dialog import VeiculoDialog

_SITUACOES = [
    (SituacaoOS.ABERTA, "Aberta"),
    (SituacaoOS.EM_EXECUCAO, "Em execução"),
    (SituacaoOS.CANCELADA, "Cancelada"),
    (SituacaoOS.CONCLUIDA, "Concluída"),
    (SituacaoOS.FATURADA, "Faturada"),
]


class TelaOSEdicao(QtWidgets.QDialog):
    def __init__(self, num_os: int | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._repo = obter_os_repo()
        self._num_os = num_os
        self._novo = num_os is None
        self._os = OrdemServico()
        self._servicos: list[ItemServico] = []
        self._produtos: list[ItemProduto] = []
        self.setWindowTitle(f"O.S. {num_os}" if num_os else "Nova Ordem de Serviço")
        self.resize(980, 700)
        self._montar_ui()
        QtCore.QTimer.singleShot(0, self._carregar_inicial)

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Ordem de Serviço")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        # --- cabecalho ---
        grupo = QtWidgets.QWidget()
        grupo_layout = QtWidgets.QVBoxLayout(grupo)
        grupo_layout.setContentsMargins(0, 0, 0, 0)
        grupo_layout.setSpacing(6)

        identificacao = QtWidgets.QGroupBox("Dados ordem de serviço")
        form = QtWidgets.QGridLayout(identificacao)
        form.setContentsMargins(12, 10, 12, 12)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)

        operacao = QtWidgets.QGroupBox("Condição de pagamento")
        form_op = QtWidgets.QGridLayout(operacao)
        form_op.setContentsMargins(12, 10, 12, 12)
        form_op.setHorizontalSpacing(8)
        form_op.setVerticalSpacing(7)

        self.cmb_filial = QtWidgets.QComboBox()
        configurar_combo(self.cmb_filial)
        self.cmb_filial.addItem("— selecione —", None)
        self.cmb_filial.setMaximumWidth(180)
        form.addWidget(rotulo_campo("Filial"), 0, 0)
        form.addWidget(self.cmb_filial, 1, 0)

        self.txt_num_os = QtWidgets.QLineEdit()
        self.txt_num_os.setReadOnly(True)
        self.txt_num_os.setMinimumWidth(120)
        self.txt_num_os.setText(str(self._num_os) if self._num_os is not None else "(novo)")
        form.addWidget(rotulo_campo("Nº OS"), 0, 1)
        form.addWidget(self.txt_num_os, 1, 1)

        self.dt_inclusao = QtWidgets.QDateEdit(calendarPopup=True)
        self.dt_inclusao.setDisplayFormat("dd/MM/yyyy")
        self.dt_inclusao.setDate(QtCore.QDate.currentDate())
        self.dt_inclusao.setEnabled(False)
        form.addWidget(rotulo_campo("Dt. Inclusão"), 0, 2)
        form.addWidget(self.dt_inclusao, 1, 2)

        self.spin_cliente = QtWidgets.QSpinBox()
        self.spin_cliente.setRange(0, 99999999)
        self.spin_cliente.setSpecialValueText("0")
        self.spin_cliente.setMaximumWidth(180)
        self.lbl_cliente = QtWidgets.QLabel("")
        configurar_descricao_lookup(self.lbl_cliente)
        btn_cli = QtWidgets.QPushButton("...")
        configurar_botao_busca(btn_cli)
        btn_cli.clicked.connect(self._buscar_cliente)
        form.addWidget(rotulo_campo("Cliente *"), 2, 0)
        form.addWidget(rotulo_campo("Razão social"), 2, 2)
        form.addWidget(self.spin_cliente, 3, 0)
        form.addWidget(btn_cli, 3, 1)
        form.addWidget(self.lbl_cliente, 3, 2, 1, 4)

        self.spin_rca = QtWidgets.QSpinBox()
        self.spin_rca.setRange(0, 999999)
        self.spin_rca.setSpecialValueText("0")
        self.spin_rca.setMaximumWidth(180)
        self.lbl_rca = QtWidgets.QLabel("")
        configurar_descricao_lookup(self.lbl_rca)
        btn_rca = QtWidgets.QPushButton("...")
        configurar_botao_busca(btn_rca)
        btn_rca.clicked.connect(self._buscar_rca)
        form.addWidget(rotulo_campo("Vendedor *"), 4, 0)
        form.addWidget(rotulo_campo("Nome"), 4, 2)
        form.addWidget(self.spin_rca, 5, 0)
        form.addWidget(btn_rca, 5, 1)
        form.addWidget(self.lbl_rca, 5, 2, 1, 4)

        self.spin_veiculo = QtWidgets.QSpinBox()
        self.spin_veiculo.setRange(0, 2147483647)  # limite do QSpinBox (int 32-bit)
        self.spin_veiculo.setSpecialValueText("0")
        self.spin_veiculo.setMaximumWidth(180)
        self.lbl_veiculo = QtWidgets.QLabel("")
        configurar_descricao_lookup(self.lbl_veiculo)
        btn_veic = QtWidgets.QPushButton("...")
        configurar_botao_busca(btn_veic)
        btn_veic.clicked.connect(self._abrir_veiculo)
        form.addWidget(rotulo_campo("Veículo"), 6, 0)
        form.addWidget(rotulo_campo("Descrição do veículo"), 6, 2)
        form.addWidget(self.spin_veiculo, 7, 0)
        form.addWidget(btn_veic, 7, 1)
        form.addWidget(self.lbl_veiculo, 7, 2, 1, 4)

        self.spin_pedido = QtWidgets.QSpinBox()
        self.spin_pedido.setRange(0, 2147483647)  # limite do QSpinBox (int 32-bit)
        self.spin_pedido.setSpecialValueText("0")
        self.spin_pedido.setMaximumWidth(180)
        self.lbl_pedido = QtWidgets.QLabel("")
        configurar_descricao_lookup(self.lbl_pedido)
        btn_ped = QtWidgets.QPushButton("...")
        configurar_botao_busca(btn_ped)
        btn_ped.clicked.connect(self._buscar_pedido)
        form.addWidget(rotulo_campo("Pedido venda *"), 8, 0)
        form.addWidget(rotulo_campo("Pedido"), 8, 2)
        form.addWidget(self.spin_pedido, 9, 0)
        form.addWidget(btn_ped, 9, 1)
        form.addWidget(self.lbl_pedido, 9, 2, 1, 4)

        self.spin_km = QtWidgets.QSpinBox()
        self.spin_km.setRange(0, 9999999)
        self.spin_km.setMaximumWidth(180)
        form.addWidget(rotulo_campo("Quilometragem"), 10, 0)
        form.addWidget(self.spin_km, 11, 0)

        self.cmb_cob = QtWidgets.QComboBox()
        configurar_combo(self.cmb_cob)
        self.cmb_cob.addItem("— selecione —", None)
        form_op.addWidget(rotulo_campo("Cobrança *"), 0, 0)
        form_op.addWidget(self.cmb_cob, 1, 0)

        self.cmb_plpag = QtWidgets.QComboBox()
        configurar_combo(self.cmb_plpag)
        self.cmb_plpag.addItem("— selecione —", None)
        form_op.addWidget(rotulo_campo("Plano de pagamento *"), 0, 1)
        form_op.addWidget(self.cmb_plpag, 1, 1)

        linha_prev = QtWidgets.QHBoxLayout()
        self.dt_prev = QtWidgets.QDateTimeEdit()
        self.dt_prev.setCalendarPopup(True)
        self.dt_prev.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.dt_prev.setDateTime(QtCore.QDateTime.currentDateTime())
        self.dt_prev.setMinimumWidth(130)
        self.chk_prev = QtWidgets.QCheckBox("Definir")
        linha_prev.addWidget(self.dt_prev, 1)
        linha_prev.addSpacing(10)
        linha_prev.addWidget(self.chk_prev)
        form.addWidget(rotulo_campo("Dt prev. término"), 0, 3)
        form.addLayout(linha_prev, 1, 3)

        self.cmb_situacao = QtWidgets.QComboBox()
        configurar_combo(self.cmb_situacao)
        for sit, rotulo in _SITUACOES:
            self.cmb_situacao.addItem(rotulo, sit)
        form.addWidget(rotulo_campo("Situação OS"), 0, 4)
        form.addWidget(self.cmb_situacao, 1, 4)

        form.setColumnMinimumWidth(0, 180)
        form.setColumnMinimumWidth(1, 34)
        form.setColumnMinimumWidth(2, 420)
        form.setColumnStretch(2, 1)
        form.setColumnStretch(3, 1)
        form.setColumnStretch(4, 1)
        form.setColumnStretch(5, 1)
        form_op.setColumnStretch(0, 1)
        form_op.setColumnStretch(1, 2)
        grupo_layout.addWidget(identificacao)
        grupo_layout.addWidget(operacao)

        layout.addWidget(grupo)

        # --- abas ---
        self.abas = QtWidgets.QTabWidget()
        self.abas.addTab(self._montar_aba_servicos(), "Serviços")
        self.abas.addTab(self._montar_aba_produtos(), "Produtos")
        self.abas.addTab(self._montar_aba_obs(), "Observações")
        layout.addWidget(self.abas, 1)

        # --- totalizadores ---
        rodape = QtWidgets.QHBoxLayout()
        self.lbl_vl_serv = QtWidgets.QLabel("Vl Serviços: R$ 0,00")
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
        configurar_grid(self.tab_serv)
        self.tab_serv.setHorizontalHeaderLabels(["Serviço", "Descrição", "Qtde", "P.Unit", "Total"])
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
        configurar_grid(self.tab_prod)
        self.tab_prod.setHorizontalHeaderLabels(["Cód.Prod", "Descrição", "Qtde", "P.Unit", "Total"])
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
                self, "Sem conexão", "Sem conexão com o banco (modo dev). Operação indisponível."
            )
            return True
        return False

    # ------------------------------------------------------------- carga inicial
    def _carregar_inicial(self) -> None:
        self._carregar_combos_financeiros()
        self._selecionar_combo(self.cmb_filial, self._os.cod_filial)
        if self._num_os is None:
            if not ConexaoOracle.instance().offline:
                try:
                    self._num_os = self._repo.proximo_num_os()
                    self.txt_num_os.setText(str(self._num_os))
                except Exception as exc:  # noqa: BLE001
                    QtWidgets.QMessageBox.warning(
                        self, "Número da O.S.", f"Falha ao carregar próximo número:\n{exc}"
                    )
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
            QtWidgets.QMessageBox.warning(self, "Carregar O.S.", "O.S. não encontrada.")
            return
        self._os = carregado
        self._servicos = list(carregado.servicos)
        self._produtos = list(carregado.produtos)
        self._preencher_cabecalho(carregado)
        self._preencher_servicos()
        self._preencher_produtos()
        self._recalcular_totais()

    def _carregar_combos_financeiros(self) -> None:
        if ConexaoOracle.instance().offline:
            return
        try:
            repo = CombosRepo()
            self.cmb_filial.blockSignals(True)
            self.cmb_cob.blockSignals(True)
            self.cmb_plpag.blockSignals(True)
            self.cmb_filial.clear()
            self.cmb_cob.clear()
            self.cmb_plpag.clear()
            self.cmb_filial.addItem("— selecione —", None)
            self.cmb_cob.addItem("— selecione —", None)
            self.cmb_plpag.addItem("— selecione —", None)
            for cod, rotulo in repo.filiais():
                self.cmb_filial.addItem(rotulo, cod)
            for cod, rotulo in repo.cobrancas():
                self.cmb_cob.addItem(rotulo, cod)
            for cod, rotulo in repo.planos_pagto():
                self.cmb_plpag.addItem(rotulo, cod)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(
                self, "Condição de pagamento", f"Falha ao carregar cobrança/plano:\n{exc}"
            )
        finally:
            self.cmb_filial.blockSignals(False)
            self.cmb_cob.blockSignals(False)
            self.cmb_plpag.blockSignals(False)

    @staticmethod
    def _selecionar_combo(combo: QtWidgets.QComboBox, valor) -> None:  # noqa: ANN001
        if valor is None:
            combo.setCurrentIndex(0)
            return
        valor_txt = str(valor)
        for indice in range(combo.count()):
            dado = combo.itemData(indice)
            if dado is not None and str(dado) == valor_txt:
                combo.setCurrentIndex(indice)
                return
        combo.setCurrentIndex(0)

    def _preencher_cabecalho(self, os_: OrdemServico) -> None:
        self.spin_cliente.setValue(os_.cod_cli or 0)
        self.txt_num_os.setText(str(os_.num_os or ""))
        if os_.dt_cadastro is not None:
            self.dt_inclusao.setDate(
                QtCore.QDate(os_.dt_cadastro.year, os_.dt_cadastro.month, os_.dt_cadastro.day)
            )
        self.spin_pedido.setValue(os_.num_ped or 0)
        if os_.num_ped:
            self.lbl_pedido.setText(f"Pedido {os_.num_ped}")
        self._selecionar_combo(self.cmb_filial, os_.cod_filial)
        self.spin_rca.setValue(os_.cod_rca or 0)
        self.spin_veiculo.setValue(os_.cod_veiculo or 0)
        self.lbl_veiculo.setText(" / ".join(x for x in (os_.placa_veiculo, os_.descricao_veiculo) if x))
        self.spin_km.setValue(os_.km or 0)
        self._selecionar_combo(self.cmb_cob, os_.cod_cob)
        self._selecionar_combo(self.cmb_plpag, os_.cod_plpag)
        if os_.dt_prev_term is not None:
            self.chk_prev.setChecked(True)
            self.dt_prev.setDateTime(QtCore.QDateTime(os_.dt_prev_term))
        idx = self.cmb_situacao.findData(os_.situacao)
        if idx >= 0:
            self.cmb_situacao.setCurrentIndex(idx)
        self.spin_desconto.setValue(float(os_.vl_desconto or 0))
        self.txt_obs.setPlainText(os_.obs or "")
        self.lbl_cliente.setText(os_.cliente_nome or (f"Cliente {os_.cod_cli}" if os_.cod_cli else ""))
        if os_.cod_rca:
            try:
                rca = TecnicoRepo().obter(os_.cod_rca)
                self.lbl_rca.setText(rca["nome"] if rca else "")
            except Exception:  # noqa: BLE001
                self.lbl_rca.setText("")

    # ------------------------------------------------------------------ cliente
    def _buscar_cliente(self) -> None:
        if self._offline():
            return
        dlg = ClienteLookupDialog(self)
        if dlg.exec() and dlg.selecionado:
            self.spin_cliente.setValue(dlg.selecionado["cod_cli"])
            self.lbl_cliente.setText(dlg.selecionado["nome"] or "")

    def _buscar_rca(self) -> None:
        if self._offline():
            return
        try:
            tecnicos = TecnicoRepo().listar_ativos()
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "RCA", f"Falha ao buscar RCA:\n{exc}")
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Localizar RCA")
        dlg.resize(520, 380)
        layout = QtWidgets.QVBoxLayout(dlg)
        tabela = QtWidgets.QTableWidget(0, 2)
        configurar_grid(tabela)
        tabela.setHorizontalHeaderLabels(["Código", "Nome"])
        tabela.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        tabela.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tabela.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        tabela.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        for item in tecnicos:
            row = tabela.rowCount()
            tabela.insertRow(row)
            cod = QtWidgets.QTableWidgetItem(str(item["matricula"]))
            cod.setData(QtCore.Qt.ItemDataRole.UserRole, item)
            tabela.setItem(row, 0, cod)
            tabela.setItem(row, 1, QtWidgets.QTableWidgetItem(item["nome"] or ""))
        layout.addWidget(tabela)
        botoes = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(botoes)

        def confirmar() -> None:
            row = tabela.currentRow()
            if row < 0:
                QtWidgets.QMessageBox.information(dlg, "RCA", "Selecione um RCA.")
                return
            selecionado = tabela.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole)
            self.spin_rca.setValue(selecionado["matricula"])
            self.lbl_rca.setText(selecionado["nome"] or "")
            dlg.accept()

        tabela.doubleClicked.connect(lambda *_: confirmar())
        botoes.accepted.connect(confirmar)
        botoes.rejected.connect(dlg.reject)
        dlg.exec()

    # ------------------------------------------------------------------ pedido
    def _buscar_pedido(self) -> None:
        if self._offline():
            return
        cod_cli = self.spin_cliente.value() or None
        if cod_cli is None:
            QtWidgets.QMessageBox.information(
                self, "Pedido de venda", "Selecione o cliente antes de buscar o pedido."
            )
            return
        dlg = PedidoLookupDialog(cod_cli, self)
        if dlg.exec() and dlg.selecionado:
            self.spin_pedido.setValue(dlg.selecionado["num_ped"])
            self.lbl_pedido.setText(f"Pedido {dlg.selecionado['num_ped']}")

    def _pedido_obrigatorio(self) -> bool:
        """Regra global (PEDIDO_OBRIGATORIO) com excecao por usuario.

        Usuario com ACESSO ao controle CONTROLE_DISPENSA_PEDIDO (PCCONTROI) fica
        dispensado de informar o pedido. Em caso de falha de leitura, exige o
        pedido (fail-safe).
        """
        try:
            if not ParametroRepo().pedido_obrigatorio():
                return False
            return not PermissaoRepo().tem_acesso(CONTROLE_DISPENSA_PEDIDO)
        except Exception:  # noqa: BLE001
            return True

    # ------------------------------------------------------------------ veiculo
    def _abrir_veiculo(self) -> None:
        if self._offline():
            return
        cod_cli = self.spin_cliente.value() or None
        veiculo = None
        if self.spin_veiculo.value():
            try:
                from core.veiculo_repo_factory import obter_veiculo_repo

                veiculo = obter_veiculo_repo().obter(self.spin_veiculo.value())
            except Exception:  # noqa: BLE001
                veiculo = None
        dlg = VeiculoDialog(veiculo, cod_cli, self)
        if not dlg.exec():
            return
        v = dlg.veiculo
        try:
            from core.veiculo_repo_factory import obter_veiculo_repo

            repo = obter_veiculo_repo()
            if v.cod_veiculo is None:
                v.cod_veiculo = repo.inserir(v)
            else:
                repo.atualizar(v)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Veículo", f"Falha ao gravar veículo:\n{exc}")
            return
        if v.cod_veiculo:
            self.spin_veiculo.setValue(v.cod_veiculo)
            self.lbl_veiculo.setText(
                " / ".join(
                    x for x in (
                        v.placa,
                        f"{v.marca or ''}/{v.modelo or ''}/{v.ano or ''}".strip("/"),
                    ) if x
                )
            )

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
            QtWidgets.QMessageBox.information(self, "Remover", "Selecione um serviço.")
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
        self.lbl_vl_serv.setText(f"Vl Serviços: R$ {vl_serv:,.2f}")
        self.lbl_vl_prod.setText(f"Vl Produtos: R$ {vl_prod:,.2f}")
        self.lbl_vl_total.setText(f"Vl Total: R$ {vl_total:,.2f}")

    # ------------------------------------------------------------------ gravar
    def _confirmar(self) -> None:
        if self._offline():
            return
        os_ = self._os
        os_.num_os = self._num_os
        os_.cod_filial = self.cmb_filial.currentData()
        if not os_.cod_filial:
            QtWidgets.QMessageBox.warning(self, "Validação", "Informe a filial.")
            self.cmb_filial.setFocus()
            return
        os_.cod_cli = self.spin_cliente.value() or None
        num_ped = self.spin_pedido.value() or None
        if self._pedido_obrigatorio() and num_ped is None:
            QtWidgets.QMessageBox.warning(
                self, "Validação", "Informe o pedido de venda do Winthor (obrigatório)."
            )
            self.spin_pedido.setFocus()
            return
        if num_ped is not None:
            if os_.cod_cli is None:
                QtWidgets.QMessageBox.warning(
                    self, "Validação", "Informe o cliente para validar o pedido de venda."
                )
                self.spin_cliente.setFocus()
                return
            try:
                pedido = PedidoRepo().validar(num_ped, os_.cod_cli)
            except Exception as exc:  # noqa: BLE001
                QtWidgets.QMessageBox.critical(self, "Validação", f"Falha ao validar o pedido:\n{exc}")
                return
            if pedido is None:
                QtWidgets.QMessageBox.warning(
                    self, "Validação",
                    f"Pedido {num_ped} inválido: precisa existir, não estar cancelado "
                    f"e pertencer ao cliente {os_.cod_cli}.",
                )
                self.spin_pedido.setFocus()
                return
        os_.num_ped = num_ped
        os_.cod_rca = self.spin_rca.value() or None
        os_.cod_veiculo = self.spin_veiculo.value() or None
        os_.km = self.spin_km.value() or None
        os_.cod_cob = self.cmb_cob.currentData()
        os_.cod_plpag = self.cmb_plpag.currentData()
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
            if self._novo:
                os_.num_os = self._repo.inserir(os_)
                self._novo = False
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

