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


def configurar_grid(tabela: QtWidgets.QTableWidget) -> None:
    tabela.verticalHeader().setVisible(False)
    tabela.setAlternatingRowColors(True)
    tabela.setShowGrid(False)
    tabela.setWordWrap(False)
    tabela.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    tabela.verticalHeader().setDefaultSectionSize(46)
    tabela.horizontalHeader().setMinimumHeight(40)


class _ComboPopupCompacto(QtWidgets.QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):  # noqa: ANN001, N802
        if hint == QtWidgets.QStyle.StyleHint.SH_ComboBox_Popup:
            return 0
        return super().styleHint(hint, option, widget, returnData)


def configurar_combo(
    combo: QtWidgets.QComboBox,
    destaque: bool = False,
    itens_visiveis: int = 9,
) -> None:
    if not combo.objectName():
        combo.setObjectName("filtroEscolha")
    if destaque:
        combo.setObjectName("periodoFiltro")
    combo.setMaxVisibleItems(itens_visiveis)
    combo.setStyle(_ComboPopupCompacto(combo.style()))
    combo._popup_compacto_style = combo.style()  # type: ignore[attr-defined]
    view = combo.view()
    view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    view.setMaximumHeight((itens_visiveis * 26) + 10)
    combo.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)


def configurar_botao_busca(botao: QtWidgets.QAbstractButton) -> None:
    from ui_widgets import icones

    botao.setObjectName("lookupButton")
    botao.setText("")
    botao.setIcon(icones.icone("buscar", "#1f2937", 24))
    botao.setIconSize(QtCore.QSize(20, 20))
    botao.setFixedSize(34, 34)
    botao.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)


def configurar_descricao_lookup(label: QtWidgets.QLabel) -> None:
    label.setObjectName("lookupDescricao")
    label.setMinimumHeight(34)
    label.setIndent(10)


def rotulo_campo(texto: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(texto.upper())
    label.setObjectName("fieldLabel")
    return label


class StatusBadgeDelegate(QtWidgets.QStyledItemDelegate):
    """Desenha um badge arredondado dentro da celula de status."""

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        badge = index.data(QtCore.Qt.ItemDataRole.UserRole)
        if not badge:
            super().paint(painter, option, index)
            return

        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        texto = opt.text
        fundo, cor_texto = badge
        opt.text = ""

        painter.save()
        style = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        largura = min(opt.rect.width() - 18, max(112, opt.fontMetrics.horizontalAdvance(texto) + 44))
        altura = min(28, opt.rect.height() - 12)
        badge_rect = QtCore.QRect(
            opt.rect.x() + (opt.rect.width() - largura) // 2,
            opt.rect.y() + (opt.rect.height() - altura) // 2,
            largura,
            altura,
        )
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(fundo))
        painter.drawRoundedRect(badge_rect, altura / 2, altura / 2)
        painter.setPen(QtGui.QColor(cor_texto))
        fonte = QtGui.QFont(opt.font)
        fonte.setBold(True)
        painter.setFont(fonte)
        painter.drawText(badge_rect, QtCore.Qt.AlignmentFlag.AlignCenter, texto)
        painter.restore()


STYLESHEET = """
QWidget {
    color: #1f2937;
    background: #ffffff;
    font-family: "Segoe UI";
    font-size: 9pt;
}

QMainWindow, QDialog {
    background: #ffffff;
}

QWidget#mainShell {
    background: #ffffff;
}

QFrame#sideMenu {
    background: #ffffff;
    border-right: 1px solid #d8e0ea;
}

QFrame#kpiCard {
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 8px;
}

QFrame#kpiCard[segment="first"] {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}

QFrame#kpiCard[segment="middle"] {
    border-radius: 0;
    border-left: none;
}

QFrame#kpiCard[segment="last"] {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    border-left: none;
}

QFrame#kpiCard[clickable="true"] {
    cursor: pointer;
}

QFrame#kpiCard[active="true"][statusColor="blue"] {
    background: #0d7be8;
    border-color: #0d7be8;
}

QFrame#kpiCard[active="true"][statusColor="orange"] {
    background: #ff980f;
    border-color: #ff980f;
}

QFrame#kpiCard[active="true"][statusColor="yellow"] {
    background: #facc15;
    border-color: #facc15;
}

QFrame#kpiCard[active="true"][statusColor="red"] {
    background: #ef4444;
    border-color: #ef4444;
}

QFrame#kpiCard[active="true"][statusColor="light_green"] {
    background: #86efac;
    border-color: #86efac;
}

QFrame#kpiCard[active="true"][statusColor="dark_green"] {
    background: #15803d;
    border-color: #15803d;
}

QLabel#statusDot {
    min-width: 10px;
    max-width: 10px;
    min-height: 10px;
    max-height: 10px;
    border-radius: 5px;
}

QLabel#statusDot[statusColor="blue"] {
    background: #0d7be8;
}

QLabel#statusDot[statusColor="orange"] {
    background: #ff980f;
}

QLabel#statusDot[statusColor="yellow"] {
    background: #facc15;
}

QLabel#statusDot[statusColor="red"] {
    background: #ef4444;
}

QLabel#statusDot[statusColor="light_green"] {
    background: #86efac;
}

QLabel#statusDot[statusColor="dark_green"] {
    background: #15803d;
}

QStatusBar {
    background: #fbfdff;
    border-top: 1px solid #d8e0ea;
    color: #64748b;
}

QLabel#telaTitulo {
    color: #020617;
    font-size: 15pt;
    font-weight: 700;
}

QLabel#telaSubtitulo {
    color: #64748b;
    font-size: 10pt;
}

QLabel {
    background: transparent;
    color: #111827;
}

QFrame#kpiCard[active="true"] QLabel,
QFrame#kpiCard[active="true"] QLabel#telaTitulo,
QFrame#kpiCard[active="true"] QLabel#telaSubtitulo {
    color: #ffffff;
}

QFrame#kpiCard[active="true"] QLabel#statusDot {
    background: transparent;
    border: 3px solid #ffffff;
    color: transparent;
}

QLabel[activeCard="true"],
QLabel#telaTitulo[activeCard="true"],
QLabel#telaSubtitulo[activeCard="true"] {
    color: #ffffff;
}

QLabel#statusDot[activeCard="true"] {
    background: transparent;
    border: 3px solid #ffffff;
    color: transparent;
}

QGroupBox {
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    margin-top: 14px;
    padding: 14px 12px 10px 12px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 5px;
    padding: 2px 8px;
    background: #f3f4f6;
    color: #020617;
    font-weight: 700;
}

QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QComboBox {
    min-height: 34px;
    border: 1px solid #bfd0e4;
    border-radius: 6px;
    padding: 0 10px;
    background: #f9fbfe;
    color: #020617;
    selection-background-color: #0ea5e9;
    selection-color: #ffffff;
}

QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateEdit:focus, QDateTimeEdit:focus, QComboBox:focus {
    border-color: #0ea5e9;
    background: #ffffff;
}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled,
QDateEdit:disabled, QDateTimeEdit:disabled, QComboBox:disabled {
    background: #f3f6fa;
    color: #8b97a8;
    border-color: #d1dbe8;
}

QComboBox::drop-down, QDateEdit::drop-down, QDateTimeEdit::drop-down {
    border: none;
    width: 34px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    border: none;
    width: 24px;
}

QComboBox#filtroEscolha, QComboBox#periodoFiltro {
    min-height: 34px;
    border: 1px solid #0ea5e9;
    border-radius: 6px;
    padding: 0 36px 0 12px;
    background: #f9fbfe;
    color: #020617;
    font-size: 9pt;
}

QComboBox#periodoFiltro {
    min-height: 38px;
    background: #ffffff;
    font-size: 10pt;
}

QComboBox#filtroEscolha:hover, QComboBox#periodoFiltro:hover {
    background: #ffffff;
    border-color: #0284c7;
}

QComboBox#filtroEscolha:focus, QComboBox#periodoFiltro:focus {
    border-color: #0284c7;
}

QComboBox#filtroEscolha::drop-down, QComboBox#periodoFiltro::drop-down {
    width: 34px;
    border: none;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}

QComboBox#filtroEscolha QAbstractItemView, QComboBox#periodoFiltro QAbstractItemView {
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background: #ffffff;
    color: #111827;
    padding: 3px 0;
    outline: 0;
    selection-background-color: #dbeafe;
    selection-color: #020617;
    show-decoration-selected: 1;
}

QComboBox#filtroEscolha QAbstractItemView::item, QComboBox#periodoFiltro QAbstractItemView::item {
    min-height: 22px;
    padding: 2px 8px;
}

QComboBox#filtroEscolha QAbstractItemView::item:selected,
QComboBox#periodoFiltro QAbstractItemView::item:selected {
    background: #dbeafe;
    color: #020617;
}

QPushButton#lookupButton, QToolButton#lookupButton {
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    padding: 0;
    border: 1px solid #bfd0e4;
    border-radius: 6px;
    background: #f9fbfe;
}

QPushButton#lookupButton:hover, QToolButton#lookupButton:hover {
    background: #ffffff;
    border-color: #0ea5e9;
}

QLabel#lookupDescricao {
    min-height: 34px;
    border: 1px solid #bfd0e4;
    border-radius: 6px;
    background: #f3f6fa;
    color: #475569;
}

QLabel#fieldLabel {
    color: #020617;
    font-size: 8pt;
    font-weight: 700;
    background: transparent;
}

QPushButton {
    min-height: 30px;
    padding: 6px 16px;
    border-radius: 9px;
    border: 1px solid #cbd5e1;
    background: #f8fafc;
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
    border-radius: 18px;
    padding: 7px 20px;
    background: #f6f7f9;
    border-color: #f6f7f9;
}

QPushButton[variant="seg"]:checked {
    background: #0ea5e9;
    border-color: #0ea5e9;
    color: #ffffff;
}

QPushButton[variant="primary"] {
    background: #0ea5e9;
    border-color: #0ea5e9;
    color: #ffffff;
}

QPushButton[variant="primary"]:hover {
    background: #0284c7;
}

QTabWidget::pane {
    border: none;
    border-top: 1px solid #e5e7eb;
    top: -1px;
}

QTabBar::tab {
    min-height: 30px;
    padding: 7px 20px;
    margin: 0 2px 8px 0;
    border-radius: 18px;
    background: #f6f7f9;
    color: #111827;
}

QTabBar::tab:selected {
    background: #0ea5e9;
    color: #ffffff;
}

QTableWidget {
    background: #ffffff;
    alternate-background-color: #fafafa;
    border: 1px solid #e5e7eb;
    border-radius: 0;
    selection-background-color: #eeeeee;
    selection-color: #020617;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #eef0f3;
}

QTableWidget::item:selected {
    background: #eeeeee;
    color: #020617;
    border-top: 1px dotted #111827;
    border-bottom: 1px dotted #111827;
    outline: none;
}

QTableWidget::item:focus {
    border-top: 1px dotted #111827;
    border-bottom: 1px dotted #111827;
    outline: none;
}

QHeaderView::section {
    background: #f8fafc;
    color: #111827;
    border: none;
    border-right: 1px solid #e5e7eb;
    border-bottom: 1px solid #dbe2ea;
    padding: 8px 10px;
    font-weight: 600;
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
