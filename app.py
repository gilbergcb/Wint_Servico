"""Entrypoint da rotina de Servico (oficina / borracharia) Winthor."""
from __future__ import annotations

import faulthandler
import logging
import os
import sys
import traceback
from pathlib import Path

from PyQt6 import QtGui, QtWidgets

import parametros_winthor
from core.conexao_oracle import ConexaoOracle
from core.licenca_repo import LicencaRepo
from ui_widgets.main_window import MainWindow
from ui_widgets.theme import aplicar_tema, configurar_alta_dpi

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "wint_servico.log"


def configurar_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    fault_log = LOG_FILE.open("a", encoding="utf-8")
    faulthandler.enable(file=fault_log)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )


def _excepthook(exc_type, exc, tb) -> None:
    texto = "".join(traceback.format_exception(exc_type, exc, tb))
    logging.getLogger("wint_servico").critical("Excecao nao tratada:\n%s", texto)
    app = QtWidgets.QApplication.instance()
    if app is not None:
        QtWidgets.QMessageBox.critical(
            None,
            "Erro inesperado",
            f"Ocorreu um erro inesperado.\n\nDetalhes foram gravados em:\n{LOG_FILE}\n\n{exc}",
        )


def main() -> int:
    configurar_logging()
    sys.excepthook = _excepthook
    parametros_winthor.carregar_parametros()
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"WinThor.{parametros_winthor.descricao_rotina()}"
            )
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).debug("Nao foi possivel definir AppUserModelID.", exc_info=True)

    configurar_alta_dpi()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(parametros_winthor.descricao_rotina())
    aplicar_tema(app)
    icon = ROOT / "assets" / "app.ico"
    if not icon.exists():
        icon = ROOT / "assets" / "app.svg"
    if icon.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon)))

    conn = ConexaoOracle.instance()
    try:
        conn.conectar()
    except Exception as exc:  # noqa: BLE001
        permitir_offline = os.environ.get("SVC_DEV_OFFLINE") == "1" or not getattr(sys, "frozen", False)
        if not permitir_offline:
            QtWidgets.QMessageBox.critical(None, "Conexao Oracle", str(exc))
            return 1
        conn.marcar_offline(exc)
        logging.getLogger(__name__).warning("Modo dev sem banco: %s", exc)

    if not conn.offline:
        try:
            LicencaRepo().validar_empresa_liberada()
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(None, "Licenca", str(exc))
            return 1

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
