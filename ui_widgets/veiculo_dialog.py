"""Dialog de cadastro/edicao de veiculo (PCM_OS_VEICULO) + busca por placa."""
from __future__ import annotations

from PyQt6 import QtCore, QtWidgets

from core.veiculo_repo import VeiculoRepo
from modelos.veiculo import Veiculo


class VeiculoDialog(QtWidgets.QDialog):
    """Formulario de cadastro/edicao de um veiculo. Devolve ``Veiculo``."""

    def __init__(
        self,
        veiculo: Veiculo | None = None,
        cod_cli: int | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = VeiculoRepo()
        self._veiculo = veiculo or Veiculo(cod_cli=cod_cli)
        if self._veiculo.cod_cli is None and cod_cli is not None:
            self._veiculo.cod_cli = cod_cli
        editando = veiculo is not None and veiculo.cod_veiculo is not None
        self.setWindowTitle("Editar veiculo" if editando else "Cadastrar veiculo")
        self.resize(520, 0)
        self._montar_ui()
        self._carregar(self._veiculo)

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self.lbl_codigo = QtWidgets.QLabel("(novo)")
        form.addRow("Codigo:", self.lbl_codigo)

        # Placa + botao de busca por placa
        linha_placa = QtWidgets.QHBoxLayout()
        self.txt_placa = QtWidgets.QLineEdit()
        self.txt_placa.setMaxLength(10)
        btn_buscar = QtWidgets.QPushButton("Buscar placa")
        btn_buscar.clicked.connect(self._buscar_placa)
        linha_placa.addWidget(self.txt_placa, 1)
        linha_placa.addWidget(btn_buscar)
        form.addRow("Placa:", linha_placa)

        self.spin_codcli = QtWidgets.QSpinBox()
        self.spin_codcli.setRange(0, 99999999)
        self.spin_codcli.setSpecialValueText("(nenhum)")
        form.addRow("Cod. cliente:", self.spin_codcli)

        self.txt_modelo = QtWidgets.QLineEdit()
        self.txt_modelo.setMaxLength(60)
        form.addRow("Modelo:", self.txt_modelo)

        self.txt_marca = QtWidgets.QLineEdit()
        self.txt_marca.setMaxLength(60)
        form.addRow("Marca:", self.txt_marca)

        self.spin_ano = QtWidgets.QSpinBox()
        self.spin_ano.setRange(0, 9999)
        self.spin_ano.setSpecialValueText("(n/d)")
        form.addRow("Ano:", self.spin_ano)

        self.txt_combustivel = QtWidgets.QLineEdit()
        self.txt_combustivel.setMaxLength(20)
        form.addRow("Combustivel:", self.txt_combustivel)

        self.txt_motor = QtWidgets.QLineEdit()
        self.txt_motor.setMaxLength(30)
        form.addRow("Motor:", self.txt_motor)

        self.txt_cor = QtWidgets.QLineEdit()
        self.txt_cor.setMaxLength(30)
        form.addRow("Cor:", self.txt_cor)

        self.txt_chassi = QtWidgets.QLineEdit()
        self.txt_chassi.setMaxLength(30)
        form.addRow("Chassi:", self.txt_chassi)

        self.spin_km = QtWidgets.QSpinBox()
        self.spin_km.setRange(0, 9999999)
        form.addRow("KM atual:", self.spin_km)

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

    def _carregar(self, v: Veiculo) -> None:
        if v.cod_veiculo is not None:
            self.lbl_codigo.setText(str(v.cod_veiculo))
        self.txt_placa.setText(v.placa or "")
        self.spin_codcli.setValue(v.cod_cli or 0)
        self.txt_modelo.setText(v.modelo or "")
        self.txt_marca.setText(v.marca or "")
        self.spin_ano.setValue(v.ano or 0)
        self.txt_combustivel.setText(v.combustivel or "")
        self.txt_motor.setText(v.motor or "")
        self.txt_cor.setText(v.cor or "")
        self.txt_chassi.setText(v.chassi or "")
        self.spin_km.setValue(v.km_atual or 0)
        self.txt_obs.setPlainText(v.obs or "")

    def _buscar_placa(self) -> None:
        placa = self.txt_placa.text().strip()
        if not placa:
            QtWidgets.QMessageBox.information(self, "Buscar placa", "Informe a placa.")
            return
        try:
            encontrado = self._repo.buscar_por_placa(placa)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "Buscar placa", f"Falha ao buscar:\n{exc}")
            return
        if encontrado is None:
            QtWidgets.QMessageBox.information(self, "Buscar placa", "Veiculo nao encontrado.")
            return
        self._veiculo = encontrado
        self._carregar(encontrado)

    def _gravar(self) -> None:
        v = self._veiculo
        v.placa = self.txt_placa.text().strip().upper() or None
        v.cod_cli = self.spin_codcli.value() or None
        v.modelo = self.txt_modelo.text().strip() or None
        v.marca = self.txt_marca.text().strip() or None
        v.ano = self.spin_ano.value() or None
        v.combustivel = self.txt_combustivel.text().strip() or None
        v.motor = self.txt_motor.text().strip() or None
        v.cor = self.txt_cor.text().strip() or None
        v.chassi = self.txt_chassi.text().strip() or None
        v.km_atual = self.spin_km.value() or None
        v.obs = self.txt_obs.toPlainText().strip() or None
        self.accept()

    @property
    def veiculo(self) -> Veiculo:
        return self._veiculo
