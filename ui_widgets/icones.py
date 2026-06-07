"""Icones SVG do menu lateral, renderizados em QIcon com cor por tema/estado.

Os mesmos tracados do mockup docs/mockups/menu_lateral.html. Renderizados via
QSvgRenderer (sem arquivos externos), recoloridos conforme o tema. Para os
itens de navegacao usamos QIcon com dois estados: Off (cor normal) e On (branco,
quando o item esta selecionado/checked).
"""
from __future__ import annotations

from PyQt6 import QtCore, QtGui
from PyQt6.QtSvg import QSvgRenderer

# Marcacao interna (paths) de cada icone, viewBox 0 0 24 24.
_PATHS: dict[str, str] = {
    "home": '<path d="M4 11l8-6 8 6"/><path d="M6 10v9h12v-9"/><path d="M10 19v-5h4v5"/>',
    "cadastro": '<path d="M14.7 6.3a4 4 0 0 1-5 5L5 16l3 3 4.7-4.7a4 4 0 0 0 5-5z"/><circle cx="16" cy="8" r="1.3"/>',
    "os": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4h6v3H9z"/><path d="M8 11h8M8 15h6"/>',
    "acompanhamento": '<path d="M4 13h4l2 5 4-12 2 7h4"/>',
    "relatorios": '<path d="M5 20V10M12 20V4M19 20v-7"/>',
    "config": '<circle cx="12" cy="12" r="3"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4"/>',
    "lua": '<path d="M20 14.5A8 8 0 1 1 9.5 4 6.5 6.5 0 0 0 20 14.5z"/>',
    "sol": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
}


def _pixmap(nome: str, cor: str, tam: int = 22) -> QtGui.QPixmap:
    inner = _PATHS.get(nome, "")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{cor}" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">{inner}</svg>'
    )
    renderer = QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    dpr = 2  # nitidez em telas HiDPI
    pm = QtGui.QPixmap(tam * dpr, tam * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pm)
    # limites em coordenadas LOGICAS (tam x tam); com DPR>1 o backing e maior
    # so para nitidez. Sem este retangulo o SVG sai cortado/desproporcional.
    renderer.render(painter, QtCore.QRectF(0, 0, tam, tam))
    painter.end()
    return pm


def icone(nome: str, cor: str, tam: int = 22) -> QtGui.QIcon:
    """QIcon de cor unica (para botoes simples)."""
    return QtGui.QIcon(_pixmap(nome, cor, tam))


def icone_nav(nome: str, cor_off: str, cor_on: str, tam: int = 22) -> QtGui.QIcon:
    """QIcon com estado Off (cor normal) e On (selecionado, ex.: branco)."""
    ic = QtGui.QIcon()
    ic.addPixmap(_pixmap(nome, cor_off, tam), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
    ic.addPixmap(_pixmap(nome, cor_on, tam), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
    return ic
