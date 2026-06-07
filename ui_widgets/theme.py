"""Tema visual da aplicacao (PyQt6)."""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

TEMA_CLARO = "light"
TEMA_ESCURO = "dark"
TEMA_PADRAO = TEMA_CLARO
SETTINGS_ORG = "GilbergCB"
SETTINGS_APP = "WintServico"


def configurar_alta_dpi() -> None:
    """No Qt6 o High-DPI scaling e automatico; mantemos pixmaps nitidos."""
    try:
        QtWidgets.QApplication.setAttribute(
            QtCore.Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True
        )
    except AttributeError:
        pass


def carregar_tema_preferido() -> str:
    tema = QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP).value("tema", TEMA_PADRAO, str)
    return tema if tema in {TEMA_CLARO, TEMA_ESCURO} else TEMA_PADRAO


def salvar_tema_preferido(tema: str) -> None:
    QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("tema", tema)


def tema_atual(app: QtWidgets.QApplication | None = None) -> str:
    app = app or QtWidgets.QApplication.instance()
    if app is None:
        return TEMA_PADRAO
    tema = app.property("tema")
    return tema if tema in {TEMA_CLARO, TEMA_ESCURO} else TEMA_PADRAO


def alternar_tema(app: QtWidgets.QApplication) -> str:
    novo_tema = TEMA_ESCURO if tema_atual(app) == TEMA_CLARO else TEMA_CLARO
    aplicar_tema(app, novo_tema)
    salvar_tema_preferido(novo_tema)
    return novo_tema


def aplicar_tema(app: QtWidgets.QApplication, tema: str | None = None) -> None:
    tema = tema or carregar_tema_preferido()
    if tema not in {TEMA_CLARO, TEMA_ESCURO}:
        tema = TEMA_PADRAO
    app.setStyle("Fusion")
    app.setFont(QtGui.QFont("Segoe UI", 9))
    app.setProperty("tema", tema)
    app.setStyleSheet(STYLESHEET + (DARK_STYLESHEET if tema == TEMA_ESCURO else ""))


def marcar_botao(botao: QtWidgets.QPushButton, variante: str) -> None:
    botao.setProperty("variant", variante)
    botao.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    botao.style().unpolish(botao)
    botao.style().polish(botao)


STYLESHEET = """
QWidget {
    color: #1f2937;
    background: #f4f7fb;
    font-family: "Segoe UI";
    font-size: 9pt;
}

QMainWindow, QDialog {
    background: #f4f7fb;
}

QWidget#mainShell {
    background: #f4f7fb;
}

QFrame#sideMenu {
    background: #ffffff;
    border-right: 1px solid #d8e0ea;
}

QFrame#kpiCard {
    background: #ffffff;
    border: 1px solid #d8e0ea;
    border-radius: 10px;
}

QStatusBar {
    background: #fbfdff;
    border-top: 1px solid #d8e0ea;
    color: #64748b;
}

QLabel#telaTitulo {
    color: #0f172a;
    font-size: 15pt;
    font-weight: 700;
}

QLabel#telaSubtitulo {
    color: #64748b;
    font-size: 10pt;
}

QLabel {
    background: transparent;
    color: #334155;
}

QPushButton {
    min-height: 26px;
    padding: 6px 14px;
    border-radius: 7px;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #1f2937;
    font-weight: 600;
}

QPushButton:hover {
    background: #f8fafc;
    border-color: #94a3b8;
}

QPushButton:pressed {
    background: #e2e8f0;
}

QPushButton[variant="nav"] {
    text-align: left;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    background: transparent;
    color: #334155;
}

QPushButton[variant="nav"]:hover {
    background: #eff6ff;
}

QPushButton[variant="nav"]:checked {
    background: #2563eb;
    color: #ffffff;
}

QToolButton[variant="nav"] {
    text-align: left;
    border: none;
    border-radius: 8px;
    padding: 8px 11px;
    background: transparent;
    color: #334155;
    font-weight: 600;
    font-size: 9pt;
}

QToolButton[variant="nav"]:hover {
    background: #eff6ff;
}

QToolButton[variant="nav"]:checked {
    background: #2563eb;
    color: #ffffff;
}

QPushButton[variant="seg"] {
    border-radius: 7px;
    padding: 5px 14px;
}

QPushButton[variant="seg"]:checked {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
}

QPushButton[variant="primary"] {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
}

QPushButton[variant="primary"]:hover {
    background: #1d4ed8;
}

QToolButton#themeToggleButton {
    width: 28px;
    height: 28px;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    background: #ffffff;
    color: #1e40af;
}

QToolButton#themeToggleButton:hover {
    background: #dbeafe;
    border-color: #93c5fd;
}
"""


DARK_STYLESHEET = """
QWidget {
    color: #e6edf3;
    background: transparent;
}

QMainWindow, QDialog {
    background: #0d1117;
}

QWidget#mainShell {
    background: #0d1117;
}

QFrame#sideMenu {
    background: #151b23;
    border-right: 1px solid #303a48;
}

QFrame#kpiCard {
    background: #151b23;
    border: 1px solid #303a48;
    border-radius: 10px;
}

QStatusBar {
    background: #111720;
    border-top: 1px solid #303a48;
    color: #9aa7b5;
}

QLabel#telaTitulo {
    color: #f4f7fb;
}

QLabel#telaSubtitulo {
    color: #9aa7b5;
}

QLabel {
    color: #d7dee8;
    background: transparent;
}

QPushButton {
    border: 1px solid #303a48;
    background: #151b23;
    color: #e6edf3;
}

QPushButton:hover {
    background: #1c2430;
    border-color: #5b8cff;
}

QPushButton[variant="nav"] {
    background: transparent;
    color: #d7dee8;
    border: none;
}

QPushButton[variant="nav"]:hover {
    background: #172746;
}

QPushButton[variant="nav"]:checked {
    background: #3f6fe5;
    color: #ffffff;
}

QToolButton[variant="nav"] {
    text-align: left;
    border: none;
    border-radius: 8px;
    padding: 8px 11px;
    background: transparent;
    color: #d7dee8;
    font-weight: 600;
}

QToolButton[variant="nav"]:hover {
    background: #172746;
}

QToolButton[variant="nav"]:checked {
    background: #3f6fe5;
    color: #ffffff;
}

QPushButton[variant="seg"]:checked {
    background: #3f6fe5;
    border-color: #5b8cff;
    color: #ffffff;
}

QPushButton[variant="primary"] {
    background: #3f6fe5;
    border-color: #5b8cff;
    color: #ffffff;
}

QToolButton#themeToggleButton {
    border: 1px solid #303a48;
    background: #151b23;
    color: #d7dee8;
}

QToolButton#themeToggleButton:hover {
    background: #172746;
    border-color: #5b8cff;
}
"""
