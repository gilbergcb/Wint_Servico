"""Smoke test temporario: monta a UI offline sem entrar no loop de eventos."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["SVC_DEV_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6 import QtWidgets  # noqa: E402

import parametros_winthor  # noqa: E402
from core.conexao_oracle import ConexaoOracle  # noqa: E402
from ui_widgets.main_window import MainWindow  # noqa: E402
from ui_widgets.theme import aplicar_tema, configurar_alta_dpi  # noqa: E402


def main() -> int:
    parametros_winthor.carregar_parametros()
    ConexaoOracle.instance().marcar_offline("smoke test (sem banco)")

    configurar_alta_dpi()
    app = QtWidgets.QApplication(sys.argv)
    aplicar_tema(app)

    win = MainWindow()
    win.show()
    app.processEvents()

    # navega por todos os modulos para garantir que cada tela instancia
    qtde = win.stack.count()
    for i in range(qtde):
        win._selecionar(i)
        app.processEvents()

    # exercita o auto-hide do menu (expande, fixa, colapsa)
    win._expandir()
    win._toggle_pin()
    win._toggle_pin()
    win._colapsar()
    app.processEvents()

    print(f"OK: MainWindow montada; {qtde} modulos navegaveis; titulo={win.windowTitle()!r}")
    print(f"OK: descricao_rotina={parametros_winthor.descricao_rotina()!r}")

    # exercita a construcao do dialog de edicao de O.S. (offline) + seus item-dialogs
    from ui_widgets.tela_os_edicao import TelaOSEdicao
    from ui_widgets.item_servico_dialog import ItemServicoDialog
    from ui_widgets.item_produto_dialog import ItemProdutoDialog

    dlg_os = TelaOSEdicao(None)
    app.processEvents()
    ItemServicoDialog(None)
    ItemProdutoDialog(None)
    app.processEvents()
    print("OK: TelaOSEdicao + ItemServicoDialog + ItemProdutoDialog construidos (offline)")

    from ui_widgets.configuracao_dialog import ConfiguracaoDialog
    ConfiguracaoDialog()
    app.processEvents()
    print("OK: ConfiguracaoDialog construido (offline)")

    # tambem valida o import do engine SQLAlchemy (sem conectar)
    from core import db_engine  # noqa

    print("OK: core.db_engine importavel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
