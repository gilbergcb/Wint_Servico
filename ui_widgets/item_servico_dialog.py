"""Dialog de inclusao/edicao de um item de servico da O.S. (PCM_OS_SERVICO).

Escolhe um servico do catalogo (PCM_SERVICO) e um tecnico ativo (PCEMPR),
ambos carregados em combos de forma offline-segura. Calcula
``preco = qtde * punit - vl_desconto``.
"""
from __future__ import annotations

from decimal import Decimal

from PyQt6 import QtCore, QtWidgets

from core.servico_repo import ServicoRepo
from core.tecnico_repo import TecnicoRepo
from modelos.item_servico import ItemServico
from servicos.calculadora_os import calcular_preco_item
from ui_widgets.theme import configurar_combo


class ItemServicoDialog(QtWidgets.QDialog):
    """Formulario de um ItemServico. Devolve o ItemServico em ``item``."""

    def __init__(self, item: ItemServico | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._item = item or ItemServico()
        self.setWindowTitle("Editar serviço da O.S." if item is not None else "Adicionar serviço")
        self.resize(540, 0)
        self._montar_ui()
        self._carregar_combos()
        self._carregar(self._item)
        self._recalcular()

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.cmb_servico = QtWidgets.QComboBox()
        configurar_combo(self.cmb_servico)
        self.cmb_servico.currentIndexChanged.connect(self._servico_alterado)
        form.addRow("Serviço:", self.cmb_servico)

        self.txt_descricao = QtWidgets.QLineEdit()
        self.txt_descricao.setMaxLength(100)
        form.addRow("Descrição*:", self.txt_descricao)

        self.cmb_tecnico = QtWidgets.QComboBox()
        configurar_combo(self.cmb_tecnico)
        form.addRow("Técnico:", self.cmb_tecnico)

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
        form.addRow("Preço unitário:", self.spin_punit)

        self.spin_desconto = QtWidgets.QDoubleSpinBox()
        self.spin_desconto.setRange(0, 9_999_999)
        self.spin_desconto.setDecimals(2)
        self.spin_desconto.setPrefix("R$ ")
        self.spin_desconto.valueChanged.connect(self._recalcular)
        form.addRow("Desconto:", self.spin_desconto)

        self.lbl_total = QtWidgets.QLabel("R$ 0,00")
        form.addRow("Total do item:", self.lbl_total)

        self.spin_comissao = QtWidgets.QDoubleSpinBox()
        self.spin_comissao.setRange(0, 100)
        self.spin_comissao.setDecimals(2)
        self.spin_comissao.setSuffix(" %")
        form.addRow("% Comissão:", self.spin_comissao)

        self.chk_reteriss = QtWidgets.QCheckBox("Reter ISS")
        form.addRow("", self.chk_reteriss)

        self.spin_aliqiss = QtWidgets.QDoubleSpinBox()
        self.spin_aliqiss.setRange(0, 100)
        self.spin_aliqiss.setDecimals(2)
        self.spin_aliqiss.setSuffix(" %")
        form.addRow("Alíquota ISS retida:", self.spin_aliqiss)

        self.dt_inicio = QtWidgets.QDateTimeEdit()
        self.dt_inicio.setCalendarPopup(True)
        self.dt_inicio.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.chk_inicio = QtWidgets.QCheckBox("Definir")
        linha_ini = QtWidgets.QHBoxLayout()
        linha_ini.addWidget(self.dt_inicio, 1)
        linha_ini.addWidget(self.chk_inicio)
        form.addRow("Dt início:", linha_ini)

        self.dt_final = QtWidgets.QDateTimeEdit()
        self.dt_final.setCalendarPopup(True)
        self.dt_final.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.chk_final = QtWidgets.QCheckBox("Definir")
        linha_fim = QtWidgets.QHBoxLayout()
        linha_fim.addWidget(self.dt_final, 1)
        linha_fim.addWidget(self.chk_final)
        form.addRow("Dt final:", linha_fim)

        self.txt_titulo = QtWidgets.QLineEdit()
        self.txt_titulo.setMaxLength(100)
        form.addRow("Título levantamento:", self.txt_titulo)

        self.txt_detalhe = QtWidgets.QPlainTextEdit()
        self.txt_detalhe.setFixedHeight(64)
        form.addRow("Detalhe levantamento:", self.txt_detalhe)

        layout.addLayout(form)

        botoes = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Confirmar")
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botoes.accepted.connect(self._confirmar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _carregar_combos(self) -> None:
        # Catálogo de serviços (offline-seguro)
        self.cmb_servico.addItem("(livre / sem catálogo)", None)
        try:
            for s in ServicoRepo().listar(ativo=True):
                self.cmb_servico.addItem(f"{s.cod_servico} - {s.descricao}", s)
        except Exception:  # noqa: BLE001
            pass  # offline ou falha: combo só com a opção livre

        # Técnicos ativos (offline-seguro)
        self.cmb_tecnico.addItem("(nenhum)", None)
        try:
            for t in TecnicoRepo().listar_ativos():
                self.cmb_tecnico.addItem(f"{t['matricula']} - {t['nome']}", t["matricula"])
        except Exception:  # noqa: BLE001
            pass

    def _servico_alterado(self) -> None:
        servico = self.cmb_servico.currentData()
        if servico is None:
            return
        if not self.txt_descricao.text().strip():
            self.txt_descricao.setText(servico.descricao or "")
        if self.spin_punit.value() == 0:
            self.spin_punit.setValue(float(servico.preco_padrao or 0))
        self.chk_reteriss.setChecked(bool(servico.reter_iss))
        if servico.perc_aliq_iss:
            self.spin_aliqiss.setValue(float(servico.perc_aliq_iss))
        self._recalcular()

    def _carregar(self, item: ItemServico) -> None:
        # selecionar serviço do catálogo se aplicável
        if item.cod_servico is not None:
            for i in range(self.cmb_servico.count()):
                dado = self.cmb_servico.itemData(i)
                if dado is not None and dado.cod_servico == item.cod_servico:
                    self.cmb_servico.setCurrentIndex(i)
                    break
        self.txt_descricao.setText(item.descricao or "")
        if item.cod_func is not None:
            idx = self.cmb_tecnico.findData(item.cod_func)
            if idx >= 0:
                self.cmb_tecnico.setCurrentIndex(idx)
        self.spin_qtde.setValue(float(item.qtde or 0) or 1)
        self.spin_punit.setValue(float(item.punit or 0))
        self.spin_desconto.setValue(float(item.vl_desconto or 0))
        self.spin_comissao.setValue(float(item.perc_comissao or 0))
        self.chk_reteriss.setChecked(bool(item.reter_iss))
        self.spin_aliqiss.setValue(float(item.perc_aliq_iss_retida or 0))
        if item.dt_inicio is not None:
            self.chk_inicio.setChecked(True)
            self.dt_inicio.setDateTime(QtCore.QDateTime(item.dt_inicio))
        else:
            self.dt_inicio.setDateTime(QtCore.QDateTime.currentDateTime())
        if item.dt_final is not None:
            self.chk_final.setChecked(True)
            self.dt_final.setDateTime(QtCore.QDateTime(item.dt_final))
        else:
            self.dt_final.setDateTime(QtCore.QDateTime.currentDateTime())
        self.txt_titulo.setText(item.titulo_levantamento or "")
        self.txt_detalhe.setPlainText(item.detalhe_levantamento or "")

    def _recalcular(self) -> None:
        preco = calcular_preco_item(
            Decimal(str(self.spin_qtde.value())),
            Decimal(str(self.spin_punit.value())),
            Decimal(str(self.spin_desconto.value())),
        )
        self.lbl_total.setText(f"R$ {preco:,.2f}")

    def _confirmar(self) -> None:
        descricao = self.txt_descricao.text().strip()
        if not descricao:
            QtWidgets.QMessageBox.warning(self, "Validação", "Informe a descrição do serviço.")
            self.txt_descricao.setFocus()
            return

        item = self._item
        servico = self.cmb_servico.currentData()
        item.cod_servico = servico.cod_servico if servico is not None else None
        item.cod_prod = servico.cod_prod if servico is not None else None
        item.cod_func = self.cmb_tecnico.currentData()
        item.descricao = descricao
        item.qtde = Decimal(str(self.spin_qtde.value()))
        item.punit = Decimal(str(self.spin_punit.value()))
        item.vl_desconto = Decimal(str(self.spin_desconto.value()))
        item.preco = calcular_preco_item(item.qtde, item.punit, item.vl_desconto)
        item.perc_comissao = Decimal(str(self.spin_comissao.value()))
        item.comissao = (item.preco * item.perc_comissao / Decimal("100")).quantize(Decimal("0.01"))
        item.reter_iss = self.chk_reteriss.isChecked()
        item.perc_aliq_iss_retida = Decimal(str(self.spin_aliqiss.value()))
        item.dt_inicio = self.dt_inicio.dateTime().toPyDateTime() if self.chk_inicio.isChecked() else None
        item.dt_final = self.dt_final.dateTime().toPyDateTime() if self.chk_final.isChecked() else None
        item.titulo_levantamento = self.txt_titulo.text().strip() or None
        item.detalhe_levantamento = self.txt_detalhe.toPlainText().strip() or None
        self.accept()

    @property
    def item(self) -> ItemServico:
        return self._item

