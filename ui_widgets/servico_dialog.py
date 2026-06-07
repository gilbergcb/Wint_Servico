"""Dialog de inclusao/edicao de servico (PCM_SERVICO) - espelha a 3501."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from PyQt6 import QtCore, QtWidgets

import parametros_winthor
from modelos.servico import Servico
from ui_widgets.produto_lookup_dialog import ProdutoLookupDialog


class ServicoDialog(QtWidgets.QDialog):
    """Formulario de cadastro/edicao de um servico do catalogo PCM_SERVICO."""

    def __init__(self, servico: Servico | None = None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._servico = servico or Servico()
        editando = servico is not None and servico.cod_servico is not None
        self.setWindowTitle("Editar servico" if editando else "Incluir servico")
        self.resize(520, 0)
        self._montar_ui()
        self._carregar(self._servico)

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.lbl_codigo = QtWidgets.QLabel("(novo)")
        form.addRow("Codigo:", self.lbl_codigo)

        self.txt_descricao = QtWidgets.QLineEdit()
        self.txt_descricao.setMaxLength(100)
        form.addRow("Descricao*:", self.txt_descricao)

        # Produto vinculado (Opcao A) + lookup
        linha_prod = QtWidgets.QHBoxLayout()
        self.spin_codprod = QtWidgets.QSpinBox()
        self.spin_codprod.setRange(0, 999999)
        self.spin_codprod.setSpecialValueText("(nenhum)")
        self.lbl_prod_desc = QtWidgets.QLabel("")
        self.lbl_prod_desc.setObjectName("telaSubtitulo")
        btn_lookup = QtWidgets.QPushButton("...")
        btn_lookup.setFixedWidth(34)
        btn_lookup.clicked.connect(self._buscar_produto)
        linha_prod.addWidget(self.spin_codprod)
        linha_prod.addWidget(btn_lookup)
        linha_prod.addWidget(self.lbl_prod_desc, 1)
        form.addRow("Produto vinculado:", linha_prod)

        self.txt_filial = QtWidgets.QLineEdit()
        self.txt_filial.setMaxLength(2)
        self.txt_filial.setFixedWidth(60)
        form.addRow("Filial:", self.txt_filial)

        self.spin_preco = QtWidgets.QDoubleSpinBox()
        self.spin_preco.setRange(0, 9_999_999)
        self.spin_preco.setDecimals(2)
        self.spin_preco.setPrefix("R$ ")
        form.addRow("Preco padrao:", self.spin_preco)

        self.spin_tempo = QtWidgets.QSpinBox()
        self.spin_tempo.setRange(0, 999999)
        self.spin_tempo.setSuffix(" min")
        form.addRow("Tempo estimado:", self.spin_tempo)

        self.chk_reteriss = QtWidgets.QCheckBox("Reter ISS")
        form.addRow("", self.chk_reteriss)

        self.spin_iss = QtWidgets.QDoubleSpinBox()
        self.spin_iss.setRange(0, 100)
        self.spin_iss.setDecimals(2)
        self.spin_iss.setSuffix(" %")
        form.addRow("Aliquota ISS:", self.spin_iss)

        self.chk_ativo = QtWidgets.QCheckBox("Ativo")
        self.chk_ativo.setChecked(True)
        form.addRow("", self.chk_ativo)

        self.txt_obs = QtWidgets.QPlainTextEdit()
        self.txt_obs.setFixedHeight(64)
        form.addRow("Observacoes:", self.txt_obs)

        layout.addLayout(form)

        botoes = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Save).setText("Gravar")
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botoes.accepted.connect(self._gravar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def _carregar(self, s: Servico) -> None:
        if s.cod_servico is not None:
            self.lbl_codigo.setText(str(s.cod_servico))
        self.txt_descricao.setText(s.descricao or "")
        self.spin_codprod.setValue(s.cod_prod or 0)
        self.txt_filial.setText(s.cod_filial or "")
        self.spin_preco.setValue(float(s.preco_padrao or 0))
        self.spin_tempo.setValue(int(s.tempo_estimado_min or 0))
        self.chk_reteriss.setChecked(bool(s.reter_iss))
        self.spin_iss.setValue(float(s.perc_aliq_iss or 0))
        self.chk_ativo.setChecked(bool(s.ativo))
        self.txt_obs.setPlainText(s.obs or "")

    def _buscar_produto(self) -> None:
        dlg = ProdutoLookupDialog(self)
        if dlg.exec() and dlg.selecionado:
            self.spin_codprod.setValue(dlg.selecionado["cod_prod"])
            self.lbl_prod_desc.setText(dlg.selecionado["descricao"] or "")
            if not self.txt_descricao.text().strip():
                self.txt_descricao.setText(dlg.selecionado["descricao"] or "")

    def _gravar(self) -> None:
        descricao = self.txt_descricao.text().strip()
        if not descricao:
            QtWidgets.QMessageBox.warning(self, "Validacao", "Informe a descricao do servico.")
            self.txt_descricao.setFocus()
            return
        try:
            preco = Decimal(str(self.spin_preco.value()))
            iss = Decimal(str(self.spin_iss.value()))
        except (InvalidOperation, ValueError):
            QtWidgets.QMessageBox.warning(self, "Validacao", "Valores numericos invalidos.")
            return

        s = self._servico
        s.descricao = descricao
        s.cod_prod = self.spin_codprod.value() or None
        s.cod_filial = self.txt_filial.text().strip() or None
        s.preco_padrao = preco
        s.tempo_estimado_min = self.spin_tempo.value() or None
        s.reter_iss = self.chk_reteriss.isChecked()
        s.perc_aliq_iss = iss
        s.ativo = self.chk_ativo.isChecked()
        s.obs = self.txt_obs.toPlainText().strip() or None
        s.usuario_cad = (parametros_winthor.USUARIOWT or "").strip() or None
        self.accept()

    @property
    def servico(self) -> Servico:
        return self._servico
