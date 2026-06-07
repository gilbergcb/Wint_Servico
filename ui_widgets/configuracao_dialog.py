"""Dialog de Configuracao da rotina.

Mostra o estado da conexao e permite:
  - Testar a conexao com o banco;
  - Criar/atualizar os objetos do banco (PCM_*) em ambientes novos, executando
    o DDL de forma idempotente via core.instalador_bd.
"""
from __future__ import annotations

import os

from PyQt6 import QtCore, QtGui, QtWidgets

from core.conexao_oracle import ConexaoOracle
from core.instalador_bd import aplicar_ddl


class ConfiguracaoDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuracao da rotina")
        self.resize(640, 480)
        self._montar_ui()
        self._atualizar_status()

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Configuracao")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        # --- estado da conexao ---
        grupo = QtWidgets.QGroupBox("Conexao")
        form = QtWidgets.QFormLayout(grupo)
        self.lbl_modo = QtWidgets.QLabel("-")
        self.lbl_dsn = QtWidgets.QLabel("-")
        self.lbl_usuario = QtWidgets.QLabel("-")
        self.lbl_estado = QtWidgets.QLabel("-")
        form.addRow("Modo:", self.lbl_modo)
        form.addRow("DSN:", self.lbl_dsn)
        form.addRow("Usuario:", self.lbl_usuario)
        form.addRow("Estado:", self.lbl_estado)
        layout.addWidget(grupo)

        # --- instalacao de objetos ---
        grupo_db = QtWidgets.QGroupBox("Objetos do banco (tabelas PCM_*)")
        gl = QtWidgets.QVBoxLayout(grupo_db)
        info = QtWidgets.QLabel(
            "Cria/atualiza todas as tabelas, sequences, triggers e indices da "
            "rotina. Operacao idempotente: objetos ja existentes sao ignorados."
        )
        info.setWordWrap(True)
        info.setObjectName("telaSubtitulo")
        gl.addWidget(info)

        botoes_db = QtWidgets.QHBoxLayout()
        self.btn_testar = QtWidgets.QPushButton("Testar conexao")
        self.btn_testar.clicked.connect(self._testar_conexao)
        self.btn_instalar = QtWidgets.QPushButton("Criar/atualizar objetos do banco")
        self.btn_instalar.clicked.connect(self._instalar)
        botoes_db.addWidget(self.btn_testar)
        botoes_db.addStretch(1)
        botoes_db.addWidget(self.btn_instalar)
        gl.addLayout(botoes_db)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Saida da instalacao aparecera aqui...")
        self.log.setFont(QtGui.QFont("Consolas", 9))
        gl.addWidget(self.log, 1)
        layout.addWidget(grupo_db, 1)

        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Close).setText("Fechar")
        botoes.rejected.connect(self.reject)
        botoes.accepted.connect(self.accept)
        layout.addWidget(botoes)

    # ------------------------------------------------------------------ status
    def _atualizar_status(self) -> None:
        conn = ConexaoOracle.instance()
        self.lbl_modo.setText(conn.modo or "-")
        self.lbl_dsn.setText(os.environ.get("SVC_DB_DSN") or conn.dsn or "-")
        self.lbl_usuario.setText(conn.usuario or os.environ.get("SVC_DB_USER") or "-")
        if conn.offline:
            self.lbl_estado.setText("OFFLINE (modo dev sem banco)")
            self.btn_instalar.setEnabled(False)
        else:
            self.lbl_estado.setText("Conectado")
            self.btn_instalar.setEnabled(True)

    # ------------------------------------------------------------------ acoes
    def _testar_conexao(self) -> None:
        conn = ConexaoOracle.instance()
        try:
            c = conn.conectar()
            with c.cursor() as cur:
                cur.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
                banner = cur.fetchone()[0]
                cur.execute("SELECT USER FROM DUAL")
                schema = cur.fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            self.log.appendPlainText(f"[FALHA] Conexao: {exc}")
            QtWidgets.QMessageBox.critical(self, "Testar conexao", f"Falha:\n{exc}")
            return
        self._atualizar_status()
        self.log.appendPlainText(f"[OK] Conectado a {schema}\n     {banner}")
        QtWidgets.QMessageBox.information(self, "Testar conexao", f"Conectado a {schema}.\n{banner}")

    def _instalar(self) -> None:
        conn = ConexaoOracle.instance()
        if conn.offline:
            QtWidgets.QMessageBox.information(self, "Configuracao", "Sem conexao com o banco.")
            return
        resp = QtWidgets.QMessageBox.question(
            self,
            "Criar/atualizar objetos",
            "Executar o DDL e criar/atualizar os objetos da rotina no banco "
            f"'{self.lbl_dsn.text()}'?\n\nObjetos existentes serao mantidos.",
        )
        if resp != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        try:
            res = aplicar_ddl(conn.conectar())
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QApplication.restoreOverrideCursor()
            self.log.appendPlainText(f"[FALHA] Instalacao abortada: {exc}")
            QtWidgets.QMessageBox.critical(self, "Configuracao", f"Falha ao instalar:\n{exc}")
            return
        QtWidgets.QApplication.restoreOverrideCursor()
        self.log.clear()
        self.log.appendPlainText("\n".join(res.linhas))
        self.log.appendPlainText(f"\n=== {res.resumo} ===")
        icone = QtWidgets.QMessageBox.Icon.Information if res.ok else QtWidgets.QMessageBox.Icon.Warning
        cx = QtWidgets.QMessageBox(icone, "Configuracao", res.resumo, parent=self)
        cx.exec()
