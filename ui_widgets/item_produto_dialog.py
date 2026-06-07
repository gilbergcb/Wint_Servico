"""Dialog de inclusao/edicao de um item de produto da O.S. (PCM_OS_PRODUTO).

Usa o ProdutoLookupDialog para escolher o produto (PCPRODUT) e calcula
``preco = qtde * punit - vl_desconto``.
"""
from __future__ import annotations

from decimal import Decimal

from PyQt6 import QtCore, QtWidgets

from modelos.item_produto import ItemProduto
from servicos.calculadora_os import calcular_preco_item
from ui_widgets.produto_lookup_dialog import ProdutoLookupDialog


class ItemProdutoDialog(QtWidgets.QDialog):
    """Formulario de um ItemProduto. Devolve o ItemProduto em ``item``."""

    def __init__(self, item: ItemProduto | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._item = item or ItemProduto()
        self.setWindowTitle("Editar produto da O.S." if item is not None else "Adicionar produto")
        self.resize(520, 0)
        self._montar_ui()
        self._carregar(self._item)
        self._recalcular()

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        # Produto + lookup
        linha_prod = QtWidgets.QHBoxLayout()
        self.spin_codprod = QtWidgets.QSpinBox()
        self.spin_codprod.setRange(0, 999999)
        self.spin_codprod.setSpecialValueText("(nenhum)")
        btn_lookup = QtWidgets.QPushButton("...")
        btn_lookup.setFixedWidth(34)
        btn_lookup.clicked.connect(self._buscar_produto)
        linha_prod.addWidget(self.spin_codprod)
        linha_prod.addWidget(btn_lookup)
        form.addRow("Produto*:", linha_prod)

        self.txt_descricao = QtWidgets.QLineEdit()
        self.txt_descricao.setMaxLength(100)
        form.addRow("Descricao*:", self.txt_descricao)

        self.spin_qtde = QtWidgets.QDoubleSpinBox()
        self.spin_qtde.setRange(0, 9_999_999)
        self.spin_qtde.setDecimals(4)
        self.spin_qtde.setValue(1)
        self.spin_qtde.valueChanged.connect(self._recalcular)
        form.addRow("Quantidade:", self.spin_qtde)

        self.spin_punit = QtWidgets.QDoubleSpinBox()
        self.spin_punit.setRange(0, 9_999_999)
        self.spin_punit.setDecimals(4)
        self.spin_punit.setPrefix("R$ ")
        self.spin_punit.valueChanged.connect(self._recalcular)
        form.addRow("Preco unitario:", self.spin_punit)

        self.spin_desconto = QtWidgets.QDoubleSpinBox()
        self.spin_desconto.setRange(0, 9_999_999)
        self.spin_desconto.setDecimals(2)
        self.spin_desconto.setPrefix("R$ ")
        self.spin_desconto.valueChanged.connect(self._recalcular)
        form.addRow("Desconto:", self.spin_desconto)

        self.lbl_total = QtWidgets.QLabel("R$ 0,00")
        form.addRow("Total do item:", self.lbl_total)

        self.chk_baixa = QtWidgets.QCheckBox("Baixa estoque")
        self.chk_baixa.setChecked(True)
        form.addRow("", self.chk_baixa)

        layout.addLayout(form)

        botoes = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Confirmar")
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botoes.accepted.connect(self._confirmar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _carregar(self, item: ItemProduto) -> None:
        self.spin_codprod.setValue(item.cod_prod or 0)
        self.txt_descricao.setText(item.descricao or "")
        self.spin_qtde.setValue(float(item.qtde or 0) or 1)
        self.spin_punit.setValue(float(item.punit or 0))
        self.spin_desconto.setValue(float(item.vl_desconto or 0))
        self.chk_baixa.setChecked(bool(item.baixa_estoque))

    def _buscar_produto(self) -> None:
        dlg = ProdutoLookupDialog(self)
        if dlg.exec() and dlg.selecionado:
            self.spin_codprod.setValue(dlg.selecionado["cod_prod"])
            self.txt_descricao.setText(dlg.selecionado["descricao"] or "")

    def _recalcular(self) -> None:
        preco = calcular_preco_item(
            Decimal(str(self.spin_qtde.value())),
            Decimal(str(self.spin_punit.value())),
            Decimal(str(self.spin_desconto.value())),
        )
        self.lbl_total.setText(f"R$ {preco:,.2f}")

    def _confirmar(self) -> None:
        descricao = self.txt_descricao.text().strip()
        if not self.spin_codprod.value():
            QtWidgets.QMessageBox.warning(self, "Validacao", "Selecione um produto.")
            return
        if not descricao:
            QtWidgets.QMessageBox.warning(self, "Validacao", "Informe a descricao do produto.")
            self.txt_descricao.setFocus()
            return

        item = self._item
        item.cod_prod = self.spin_codprod.value()
        item.descricao = descricao
        item.qtde = Decimal(str(self.spin_qtde.value()))
        item.punit = Decimal(str(self.spin_punit.value()))
        item.vl_desconto = Decimal(str(self.spin_desconto.value()))
        item.preco = calcular_preco_item(item.qtde, item.punit, item.vl_desconto)
        item.baixa_estoque = self.chk_baixa.isChecked()
        self.accept()

    @property
    def item(self) -> ItemProduto:
        return self._item
