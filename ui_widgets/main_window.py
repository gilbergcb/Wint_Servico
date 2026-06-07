"""Janela principal: shell com menu lateral colapsavel (auto-hide) e icones.

O menu fica recolhido (so icones, largura RAIL) e expande no hover (largura
PANEL). Clicar no logo fixa/solta o menu aberto (pin). Icones SVG recoloridos
conforme o tema; item selecionado em azul com icone branco.
"""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets

import parametros_winthor
from core.conexao_oracle import ConexaoOracle
from ui_widgets import icones
from ui_widgets.theme import TEMA_ESCURO, alternar_tema, tema_atual

from .tela_acompanhamento import TelaAcompanhamento
from .tela_cadastro_servico import TelaCadastroServico
from .tela_home import TelaHome
from .tela_os_lista import TelaOSLista
from .tela_relatorios import TelaRelatorios

_RAIL = 72
_PANEL = 248
_COR_OFF_CLARO = "#334155"
_COR_OFF_ESCURO = "#d7dee8"
_COR_ON = "#ffffff"


class _Sidebar(QtWidgets.QFrame):
    """QFrame que avisa entrada/saida do mouse (para o auto-hide)."""

    def __init__(self, ao_entrar, ao_sair) -> None:
        super().__init__()
        self._ao_entrar = ao_entrar
        self._ao_sair = ao_sair

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self._ao_entrar()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._ao_sair()
        super().leaveEvent(event)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(parametros_winthor.TITULO_ROTINA)
        self.setWindowIcon(QtWidgets.QApplication.windowIcon())
        self.resize(1120, 720)
        self.setMinimumSize(940, 600)
        self._pinned = False
        self._nav_btns: list[QtWidgets.QToolButton] = []
        self._montar_ui()
        self._aplicar_icones()
        self._status_conexao()

    # --------------------------------------------------------------------- UI
    def _montar_ui(self) -> None:
        central = QtWidgets.QWidget()
        central.setObjectName("mainShell")
        raiz = QtWidgets.QHBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        self.sidebar = _Sidebar(self._expandir, self._colapsar)
        self.sidebar.setObjectName("sideMenu")
        self.sidebar.setFixedWidth(_RAIL)
        menu_layout = QtWidgets.QVBoxLayout(self.sidebar)
        menu_layout.setContentsMargins(10, 12, 10, 12)
        menu_layout.setSpacing(4)

        # marca / logo (clique fixa o menu)
        self.brand = QtWidgets.QToolButton()
        self.brand.setProperty("variant", "nav")
        self.brand.setText("Servico / Oficina")
        self.brand.setIcon(QtGui.QIcon(self._logo_pixmap()))
        self.brand.setIconSize(QtCore.QSize(30, 30))
        self.brand.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.brand.setToolTip("Fixar/recolher menu")
        self.brand.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.brand.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.brand.setMinimumHeight(46)
        self.brand.clicked.connect(self._toggle_pin)
        menu_layout.addWidget(self.brand)
        menu_layout.addSpacing(8)

        # --- navegacao ---
        self.stack = QtWidgets.QStackedWidget()
        modulos = [
            ("home", "Inicio", TelaHome()),
            ("cadastro", "Cadastro de Servico", TelaCadastroServico()),
            ("os", "Ordens de Servico", TelaOSLista()),
            ("acompanhamento", "Acompanhamento", TelaAcompanhamento()),
            ("relatorios", "Relatorios", TelaRelatorios()),
        ]
        for indice, (icone_nome, rotulo, widget) in enumerate(modulos):
            self.stack.addWidget(widget)
            botao = self._criar_botao(icone_nome, rotulo, checkable=True)
            botao.clicked.connect(lambda _=False, i=indice: self._selecionar(i))
            menu_layout.addWidget(botao)
            self._nav_btns.append(botao)

        menu_layout.addStretch(1)

        # --- rodape: configuracao + tema ---
        self.btn_config = self._criar_botao("config", "Configuracao", checkable=False)
        self.btn_config.clicked.connect(self._abrir_configuracao)
        menu_layout.addWidget(self.btn_config)

        self.btn_tema = self._criar_botao("lua", "Tema claro/escuro", checkable=False)
        self.btn_tema.clicked.connect(self._alternar_tema)
        menu_layout.addWidget(self.btn_tema)

        raiz.addWidget(self.sidebar)
        raiz.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        # animacao de largura do menu
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        self._anim.valueChanged.connect(lambda v: self.sidebar.setFixedWidth(int(v)))

        self._selecionar(0)

    def _criar_botao(self, icone_nome: str, rotulo: str, *, checkable: bool) -> QtWidgets.QToolButton:
        b = QtWidgets.QToolButton()
        b.setProperty("variant", "nav")
        b.setText(rotulo)
        b.setToolTip(rotulo)
        b.setCheckable(checkable)
        b.setIconSize(QtCore.QSize(22, 22))
        b.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        b.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        b.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        b.setMinimumHeight(44)
        b._icone_nome = icone_nome  # type: ignore[attr-defined]
        return b

    @staticmethod
    def _logo_pixmap(tam: int = 30) -> QtGui.QPixmap:
        dpr = 2
        pm = QtGui.QPixmap(tam * dpr, tam * dpr)
        pm.setDevicePixelRatio(dpr)
        pm.fill(QtCore.Qt.GlobalColor.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        p.setBrush(QtGui.QColor("#2563eb"))
        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, tam, tam, 8, 8)
        p.setPen(QtGui.QColor("#ffffff"))
        f = QtGui.QFont("Segoe UI", 13, QtGui.QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(QtCore.QRectF(0, 0, tam, tam), QtCore.Qt.AlignmentFlag.AlignCenter, "S")
        p.end()
        return pm

    # ------------------------------------------------------------------ icones
    def _aplicar_icones(self) -> None:
        escuro = tema_atual() == TEMA_ESCURO
        cor_off = _COR_OFF_ESCURO if escuro else _COR_OFF_CLARO
        for b in self._nav_btns:
            b.setIcon(icones.icone_nav(b._icone_nome, cor_off, _COR_ON))  # type: ignore[attr-defined]
        self.btn_config.setIcon(icones.icone("config", cor_off))
        self.btn_tema.setIcon(icones.icone("sol" if escuro else "lua", cor_off))

    # ----------------------------------------------------------------- auto-hide
    def _animar(self, alvo: int) -> None:
        self._anim.stop()
        self._anim.setStartValue(self.sidebar.width())
        self._anim.setEndValue(alvo)
        self._anim.start()

    def _set_estilo_botoes(self, expandido: bool) -> None:
        estilo = (
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            if expandido
            else QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        for b in (self.brand, *self._nav_btns, self.btn_config, self.btn_tema):
            b.setToolButtonStyle(estilo)

    def _expandir(self) -> None:
        self._set_estilo_botoes(True)
        self._animar(_PANEL)

    def _colapsar(self) -> None:
        if self._pinned:
            return
        self._set_estilo_botoes(False)
        self._animar(_RAIL)

    def _toggle_pin(self) -> None:
        self._pinned = not self._pinned
        if self._pinned:
            self._expandir()
        else:
            self._set_estilo_botoes(False)
            self._animar(_RAIL)

    # ------------------------------------------------------------------ navegacao
    def _selecionar(self, indice: int) -> None:
        self.stack.setCurrentIndex(indice)
        for i, botao in enumerate(self._nav_btns):
            botao.setChecked(i == indice)

    @QtCore.pyqtSlot()
    def _abrir_configuracao(self) -> None:
        from .configuracao_dialog import ConfiguracaoDialog

        ConfiguracaoDialog(self).exec()

    @QtCore.pyqtSlot()
    def _alternar_tema(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        alternar_tema(app)
        self._aplicar_icones()

    def _status_conexao(self) -> None:
        conn = ConexaoOracle.instance()
        if conn.offline:
            self.statusBar().showMessage(f"Modo dev sem banco - {conn.erro_conexao}")
        else:
            usuario = parametros_winthor.USUARIOWT.strip()
            sufixo = f" ({conn.modo})" if conn.modo else ""
            self.statusBar().showMessage(
                (f"Conectado: {usuario}" if usuario else "Conectado") + sufixo
            )
