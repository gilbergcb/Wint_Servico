"""Dialog de Configuracao da rotina.

Mostra o estado da conexao e permite:
  - Testar a conexao com o banco;
  - Criar/atualizar os objetos do banco (PCM_*) em ambientes novos, executando
    o DDL de forma idempotente via core.instalador_bd.
"""
from __future__ import annotations

import os

from PyQt6 import QtCore, QtGui, QtWidgets

import parametros_winthor
from core.conexao_oracle import ConexaoOracle
from core.instalador_bd import aplicar_ddl
from core.parametro_repo import (
    CHAVE_MODO_OPERACAO,
    CHAVE_PEDIDO_OBRIGATORIO,
    CHAVE_SETOR_TECNICOS,
    CHAVE_TIPO_FATURAMENTO,
    FATURAMENTO_INTERNO,
    FATURAMENTO_WINTHOR,
    MODO_PCM,
    MODO_WINTHOR,
    NAO,
    SIM,
    ParametroRepo,
)
from core.setor_repo import SetorRepo
from ui_widgets.setor_lookup_dialog import SetorLookupDialog
from ui_widgets.theme import configurar_botao_busca, configurar_combo, configurar_descricao_lookup


class ConfiguracaoDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuração da rotina")
        self.resize(640, 480)
        self._montar_ui()
        self._atualizar_status()

    def _montar_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        titulo = QtWidgets.QLabel("Configuração")
        titulo.setObjectName("telaTitulo")
        layout.addWidget(titulo)

        # --- estado da conexao ---
        grupo = QtWidgets.QGroupBox("Conexão")
        form = QtWidgets.QFormLayout(grupo)
        self.lbl_modo = QtWidgets.QLabel("-")
        self.lbl_dsn = QtWidgets.QLabel("-")
        self.lbl_usuario = QtWidgets.QLabel("-")
        self.lbl_estado = QtWidgets.QLabel("-")
        form.addRow("Modo:", self.lbl_modo)
        form.addRow("DSN:", self.lbl_dsn)
        form.addRow("Usuário:", self.lbl_usuario)
        form.addRow("Estado:", self.lbl_estado)
        layout.addWidget(grupo)

        # --- modo de operacao (perfil do cliente) ---
        grupo_modo = QtWidgets.QGroupBox("Modo de operação (perfil do cliente)")
        ml = QtWidgets.QVBoxLayout(grupo_modo)
        self.cmb_modo = QtWidgets.QComboBox()
        configurar_combo(self.cmb_modo)
        self.cmb_modo.addItem("Tabelas próprias (PCM_*)", MODO_PCM)
        self.cmb_modo.addItem("100% Winthor (módulo 35)", MODO_WINTHOR)
        aviso_modo = QtWidgets.QLabel(
            "Define onde a rotina grava: tabelas próprias PCM_* ou as nativas do "
            "módulo 35 (PCORDEMSERVICO/...). Alterar com O.S. já cadastradas pode "
            "deixar dados em backends diferentes - troque com a base vazia ou após migração."
        )
        aviso_modo.setWordWrap(True)
        aviso_modo.setObjectName("telaSubtitulo")
        linha_modo = QtWidgets.QHBoxLayout()
        self.btn_salvar_modo = QtWidgets.QPushButton("Salvar")
        self.btn_salvar_modo.setAutoDefault(False)
        self.btn_salvar_modo.setDefault(False)
        self.btn_salvar_modo.clicked.connect(self._salvar_modo)
        linha_modo.addWidget(self.cmb_modo, 1)
        linha_modo.addWidget(self.btn_salvar_modo)
        ml.addLayout(linha_modo)
        ml.addWidget(aviso_modo)
        layout.addWidget(grupo_modo)

        # --- faturamento ---
        grupo_fat = QtWidgets.QGroupBox("Faturamento")
        fl = QtWidgets.QFormLayout(grupo_fat)
        self.cmb_faturamento = QtWidgets.QComboBox()
        configurar_combo(self.cmb_faturamento)
        self.cmb_faturamento.addItem("Interno (tabelas próprias - PCM_OS_FATURA)", FATURAMENTO_INTERNO)
        self.cmb_faturamento.addItem("Winthor (conta a receber - PCPREST)", FATURAMENTO_WINTHOR)
        self.btn_salvar_fat = QtWidgets.QPushButton("Salvar")
        self.btn_salvar_fat.setAutoDefault(False)
        self.btn_salvar_fat.setDefault(False)
        self.btn_salvar_fat.clicked.connect(self._salvar_faturamento)
        linha_fat = QtWidgets.QHBoxLayout()
        linha_fat.addWidget(self.cmb_faturamento, 1)
        linha_fat.addWidget(self.btn_salvar_fat)
        fl.addRow("Tipo:", linha_fat)
        layout.addWidget(grupo_fat)

        # --- regras da O.S. ---
        grupo_os = QtWidgets.QGroupBox("Ordem de Serviço")
        ol = QtWidgets.QVBoxLayout(grupo_os)
        self.chk_pedido_obrig = QtWidgets.QCheckBox(
            "Exigir pedido de venda do Winthor na O.S. (todos os usuários)"
        )
        self.spin_setor_tecnicos = QtWidgets.QSpinBox()
        self.spin_setor_tecnicos.setRange(0, 999999)
        self.spin_setor_tecnicos.setSpecialValueText("(todos)")
        self.spin_setor_tecnicos.setToolTip("Filtra técnicos ativos pelo campo PCEMPR.CODSETOR.")
        self.spin_setor_tecnicos.editingFinished.connect(self._atualizar_nome_setor)
        self.lbl_setor_tecnicos = QtWidgets.QLabel("Todos os setores")
        self.lbl_setor_tecnicos.setMinimumWidth(260)
        configurar_descricao_lookup(self.lbl_setor_tecnicos)
        self.btn_buscar_setor = QtWidgets.QPushButton("...")
        configurar_botao_busca(self.btn_buscar_setor)
        self.btn_buscar_setor.clicked.connect(self._buscar_setor_tecnicos)
        ajuda = QtWidgets.QLabel(
            "Usuários com acesso ao controle de dispensa no Winthor (PCCONTROI) "
            "podem gravar a O.S. sem informar o pedido."
        )
        ajuda.setWordWrap(True)
        ajuda.setObjectName("telaSubtitulo")
        linha_os = QtWidgets.QHBoxLayout()
        self.btn_salvar_os = QtWidgets.QPushButton("Salvar")
        self.btn_salvar_os.setAutoDefault(False)
        self.btn_salvar_os.setDefault(False)
        self.btn_salvar_os.clicked.connect(self._salvar_regras_os)
        linha_os.addWidget(self.chk_pedido_obrig, 1)
        linha_os.addWidget(self.btn_salvar_os)
        linha_setor = QtWidgets.QHBoxLayout()
        linha_setor.addWidget(QtWidgets.QLabel("Setor de técnicos:"))
        linha_setor.addWidget(self.spin_setor_tecnicos)
        linha_setor.addWidget(self.btn_buscar_setor)
        linha_setor.addWidget(self.lbl_setor_tecnicos, 1)
        ol.addLayout(linha_os)
        ol.addLayout(linha_setor)
        ol.addWidget(ajuda)
        layout.addWidget(grupo_os)

        # --- instalacao de objetos ---
        grupo_db = QtWidgets.QGroupBox("Objetos do banco (tabelas PCM_*)")
        gl = QtWidgets.QVBoxLayout(grupo_db)
        info = QtWidgets.QLabel(
            "Cria/atualiza todas as tabelas, sequences, triggers e indices da "
            "rotina. Operação idempotente: objetos já existentes são ignorados."
        )
        info.setWordWrap(True)
        info.setObjectName("telaSubtitulo")
        gl.addWidget(info)

        botoes_db = QtWidgets.QHBoxLayout()
        self.btn_testar = QtWidgets.QPushButton("Testar conexão")
        self.btn_testar.setAutoDefault(False)
        self.btn_testar.setDefault(False)
        self.btn_testar.clicked.connect(self._testar_conexao)
        self.btn_instalar = QtWidgets.QPushButton("Criar/atualizar objetos do banco")
        self.btn_instalar.setAutoDefault(False)
        self.btn_instalar.setDefault(False)
        self.btn_instalar.clicked.connect(self._instalar)
        botoes_db.addWidget(self.btn_testar)
        botoes_db.addStretch(1)
        botoes_db.addWidget(self.btn_instalar)
        gl.addLayout(botoes_db)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Saída da instalação aparecerá aqui...")
        self.log.setFont(QtGui.QFont("Consolas", 9))
        gl.addWidget(self.log, 1)
        layout.addWidget(grupo_db, 1)

        botoes = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        btn_fechar = botoes.button(QtWidgets.QDialogButtonBox.StandardButton.Close)
        btn_fechar.setText("Fechar")
        btn_fechar.setAutoDefault(False)
        btn_fechar.setDefault(False)
        btn_fechar.clicked.connect(self.close)
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
            self.cmb_faturamento.setEnabled(False)
            self.btn_salvar_fat.setEnabled(False)
            self.chk_pedido_obrig.setEnabled(False)
            self.spin_setor_tecnicos.setEnabled(False)
            self.btn_buscar_setor.setEnabled(False)
            self.btn_salvar_os.setEnabled(False)
            self.cmb_modo.setEnabled(False)
            self.btn_salvar_modo.setEnabled(False)
        else:
            self.lbl_estado.setText("Conectado")
            self.btn_instalar.setEnabled(True)
            self.cmb_faturamento.setEnabled(True)
            self.btn_salvar_fat.setEnabled(True)
            self.chk_pedido_obrig.setEnabled(True)
            self.spin_setor_tecnicos.setEnabled(True)
            self.btn_buscar_setor.setEnabled(True)
            self.btn_salvar_os.setEnabled(True)
            self.cmb_modo.setEnabled(True)
            self.btn_salvar_modo.setEnabled(True)
            self._carregar_modo()
            self._carregar_faturamento()
            self._carregar_regras_os()

    # ------------------------------------------------------------------ modo operacao
    def _carregar_modo(self) -> None:
        try:
            modo = ParametroRepo().modo_operacao()
        except Exception as exc:  # noqa: BLE001
            self.log.appendPlainText(f"[AVISO] Não foi possível ler o modo de operação: {exc}")
            return
        idx = self.cmb_modo.findData(modo)
        if idx >= 0:
            self.cmb_modo.setCurrentIndex(idx)

    def _salvar_modo(self) -> None:
        if ConexaoOracle.instance().offline:
            QtWidgets.QMessageBox.information(self, "Modo de operação", "Sem conexão com o banco.")
            return
        modo = self.cmb_modo.currentData()
        if modo == MODO_WINTHOR:
            resp = QtWidgets.QMessageBox.question(
                self, "Modo de operação",
                "Operar 100% nas tabelas nativas do módulo 35 ainda está em "
                "implementação. Deseja salvar o parâmetro mesmo assim?",
            )
            if resp != QtWidgets.QMessageBox.StandardButton.Yes:
                return
        usuario = (parametros_winthor.USUARIOWT or "").strip() or None
        try:
            ParametroRepo().salvar(CHAVE_MODO_OPERACAO, modo, usuario)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Modo de operação", f"Falha ao salvar:\n{exc}")
            return
        QtWidgets.QMessageBox.information(
            self, "Modo de operação", f"Modo salvo: {self.cmb_modo.currentText()}."
        )

    # ------------------------------------------------------------------ faturamento
    def _carregar_faturamento(self) -> None:
        try:
            tipo = ParametroRepo().tipo_faturamento()
        except Exception as exc:  # noqa: BLE001
            self.log.appendPlainText(f"[AVISO] Não foi possível ler o parâmetro de faturamento: {exc}")
            return
        idx = self.cmb_faturamento.findData(tipo)
        if idx >= 0:
            self.cmb_faturamento.setCurrentIndex(idx)

    def _salvar_faturamento(self) -> None:
        if ConexaoOracle.instance().offline:
            QtWidgets.QMessageBox.information(self, "Faturamento", "Sem conexão com o banco.")
            return
        tipo = self.cmb_faturamento.currentData()
        usuario = (parametros_winthor.USUARIOWT or "").strip() or None
        try:
            ParametroRepo().salvar(CHAVE_TIPO_FATURAMENTO, tipo, usuario)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Faturamento", f"Falha ao salvar:\n{exc}")
            return
        QtWidgets.QMessageBox.information(
            self, "Faturamento", f"Tipo de faturamento salvo: {self.cmb_faturamento.currentText()}."
        )

    # ------------------------------------------------------------------ regras O.S.
    def _carregar_regras_os(self) -> None:
        try:
            obrigatorio = ParametroRepo().pedido_obrigatorio()
            setor = ParametroRepo().setor_tecnicos()
        except Exception as exc:  # noqa: BLE001
            self.log.appendPlainText(f"[AVISO] Não foi possível ler as regras da O.S.: {exc}")
            return
        self.chk_pedido_obrig.setChecked(obrigatorio)
        self.spin_setor_tecnicos.setValue(setor or 0)
        self._atualizar_nome_setor()

    def _atualizar_nome_setor(self) -> None:
        cod_setor = self.spin_setor_tecnicos.value()
        if cod_setor <= 0:
            self.lbl_setor_tecnicos.setText("Todos os setores")
            return
        if ConexaoOracle.instance().offline:
            self.lbl_setor_tecnicos.setText(f"Setor {cod_setor}")
            return
        try:
            setor = SetorRepo().obter(cod_setor)
        except Exception:  # noqa: BLE001
            self.lbl_setor_tecnicos.setText(f"Setor {cod_setor}")
            return
        self.lbl_setor_tecnicos.setText(setor["nome"] if setor else "Setor não encontrado")

    def _buscar_setor_tecnicos(self) -> None:
        if ConexaoOracle.instance().offline:
            QtWidgets.QMessageBox.information(self, "Setor de técnicos", "Sem conexão com o banco.")
            return
        dlg = SetorLookupDialog(self)
        if dlg.exec() and dlg.selecionado:
            self.spin_setor_tecnicos.setValue(dlg.selecionado["cod_setor"])
            self.lbl_setor_tecnicos.setText(dlg.selecionado["nome"] or "")

    def _salvar_regras_os(self) -> None:
        if ConexaoOracle.instance().offline:
            QtWidgets.QMessageBox.information(self, "Ordem de Serviço", "Sem conexão com o banco.")
            return
        valor = SIM if self.chk_pedido_obrig.isChecked() else NAO
        setor = self.spin_setor_tecnicos.value()
        usuario = (parametros_winthor.USUARIOWT or "").strip() or None
        try:
            ParametroRepo().salvar(CHAVE_PEDIDO_OBRIGATORIO, valor, usuario)
            ParametroRepo().salvar(CHAVE_SETOR_TECNICOS, str(setor or ""), usuario)
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Ordem de Serviço", f"Falha ao salvar:\n{exc}")
            return
        self._atualizar_nome_setor()
        estado = "exigido" if valor == SIM else "opcional"
        filtro = f" Setor de técnicos: {setor}." if setor else " Técnicos: todos os setores."
        QtWidgets.QMessageBox.information(
            self, "Ordem de Serviço", f"Pedido de venda agora está {estado} na O.S.{filtro}"
        )

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
            self.log.appendPlainText(f"[FALHA] Conexão: {exc}")
            QtWidgets.QMessageBox.critical(self, "Testar conexão", f"Falha:\n{exc}")
            return
        self._atualizar_status()
        self.log.appendPlainText(f"[OK] Conectado a {schema}\n     {banner}")
        QtWidgets.QMessageBox.information(self, "Testar conexão", f"Conectado a {schema}.\n{banner}")

    def _instalar(self) -> None:
        conn = ConexaoOracle.instance()
        if conn.offline:
            QtWidgets.QMessageBox.information(self, "Configuração", "Sem conexão com o banco.")
            return
        resp = QtWidgets.QMessageBox.question(
            self,
            "Criar/atualizar objetos",
            "Executar o DDL e criar/atualizar os objetos da rotina no banco "
            f"'{self.lbl_dsn.text()}'?\n\nObjetos existentes serão mantidos.",
        )
        if resp != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CursorShape.WaitCursor))
        try:
            res = aplicar_ddl(conn.conectar())
        except Exception as exc:  # noqa: BLE001
            QtWidgets.QApplication.restoreOverrideCursor()
            self.log.appendPlainText(f"[FALHA] Instalação abortada: {exc}")
            QtWidgets.QMessageBox.critical(self, "Configuração", f"Falha ao instalar:\n{exc}")
            return
        QtWidgets.QApplication.restoreOverrideCursor()
        self.log.clear()
        self.log.appendPlainText("\n".join(res.linhas))
        self.log.appendPlainText(f"\n=== {res.resumo} ===")
        icone = QtWidgets.QMessageBox.Icon.Information if res.ok else QtWidgets.QMessageBox.Icon.Warning
        cx = QtWidgets.QMessageBox(icone, "Configuração", res.resumo, parent=self)
        cx.exec()

