"""Widget base reutilizado pelas telas stub (titulo + subtitulo placeholder)."""
from __future__ import annotations

from PyQt6 import QtCore, QtWidgets


class TelaBase(QtWidgets.QWidget):
    """QWidget simples com titulo e subtitulo centralizados.

    As telas reais (Fases 1+) substituirao o corpo abaixo do cabecalho.
    """

    def __init__(
        self,
        titulo: str,
        subtitulo: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(6)

        lbl_titulo = QtWidgets.QLabel(titulo)
        lbl_titulo.setObjectName("telaTitulo")
        lbl_sub = QtWidgets.QLabel(subtitulo)
        lbl_sub.setObjectName("telaSubtitulo")
        lbl_sub.setWordWrap(True)

        layout.addWidget(lbl_titulo)
        layout.addWidget(lbl_sub)

        placeholder = QtWidgets.QLabel("Modulo em construcao.")
        placeholder.setObjectName("telaSubtitulo")
        placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(placeholder)
        layout.addStretch(2)
