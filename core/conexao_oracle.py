"""Conexao Oracle DUAL-MODE (thin/thick) compativel com o menu Winthor.

Modo selecionado pela env var ``SVC_DB_MODE``:
  - ``thin``  (default): sem Instant Client. Exige servidor Oracle 12.1+.
  - ``thick``: inicializa o Instant Client a partir de
    ``SVC_ORACLE_CLIENT_LIB_DIR``.

IMPORTANTE (ambiente de teste Oracle 10g 10.2.0.3.0, 32-bit):
  - O modo thin NAO funciona com 10g -> use ``SVC_DB_MODE=thick``.
  - Para o thick falar com 10g, o Instant Client deve ser 11.2 ou 12.x
    (NAO 19c) e 32-bit (alvo do .exe).
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import oracledb
from dotenv import load_dotenv

import parametros_winthor

load_dotenv()
log = logging.getLogger(__name__)

MODO_THIN = "thin"
MODO_THICK = "thick"


class ConexaoOracle:
    _instance: Optional["ConexaoOracle"] = None

    def __init__(self) -> None:
        self._conn: Optional[oracledb.Connection] = None
        self.offline = False
        self.erro_conexao = ""
        self.usuario = ""
        self.dsn = ""
        self.origem = ""
        self.modo = (os.environ.get("SVC_DB_MODE") or MODO_THIN).strip().lower()

    @classmethod
    def instance(cls) -> "ConexaoOracle":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolver_credenciais(self) -> tuple[str, str, str, str]:
        parametros_winthor.carregar_parametros()
        if parametros_winthor.CHAMADO_PELO_MENU:
            return (
                parametros_winthor.USUARIOBD,
                parametros_winthor.SENHABD,
                parametros_winthor.ALIASBD,
                "menu Winthor",
            )

        if not getattr(sys, "frozen", False):
            user = os.environ.get("SVC_DB_USER")
            pwd = os.environ.get("SVC_DB_PWD")
            dsn = os.environ.get("SVC_DB_DSN")
            if user and pwd and dsn:
                return user, pwd, dsn, ".env (dev)"

        raise RuntimeError(
            "Conexao nao informada. Abra pelo menu Winthor ou configure "
            "SVC_DB_USER/SVC_DB_PWD/SVC_DB_DSN em desenvolvimento."
        )

    def _inicializar_thick(self) -> None:
        """Inicializa o Instant Client (modo thick), uma unica vez."""
        if getattr(oracledb, "_thick_initialized", False):
            return
        lib_dir = (os.environ.get("SVC_ORACLE_CLIENT_LIB_DIR") or "").strip() or None
        config_dir = (os.environ.get("TNS_ADMIN") or "").strip() or lib_dir
        kwargs: dict[str, str] = {}
        if lib_dir:
            kwargs["lib_dir"] = lib_dir
        if config_dir:
            kwargs["config_dir"] = config_dir
        log.info("Inicializando Oracle Client (thick): %s", lib_dir or "PATH/registro")
        oracledb.init_oracle_client(**kwargs)
        oracledb._thick_initialized = True  # type: ignore[attr-defined]

    def conectar(self) -> oracledb.Connection:
        if self.offline:
            raise RuntimeError("Aplicacao em modo desenvolvimento sem banco.")
        if self._conn is not None:
            return self._conn

        if self.modo == MODO_THICK:
            self._inicializar_thick()
        elif self.modo != MODO_THIN:
            raise RuntimeError(
                f"SVC_DB_MODE invalido: {self.modo!r}. Use 'thin' ou 'thick'."
            )

        user, pwd, dsn, origem = self._resolver_credenciais()
        self._conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
        self.usuario = user
        self.dsn = dsn
        self.origem = origem

        with self._conn.cursor() as cur:
            cur.execute("alter session set nls_numeric_characters = ',.'")
            cur.execute("alter session set nls_date_format = 'dd/mm/yyyy'")
            cur.execute(
                "begin dbms_application_info.set_module(:modulo, :acao); end;",
                {"modulo": "SVC_OFICINA", "acao": "INICIAR_APP"},
            )
        return self._conn

    def marcar_offline(self, erro: Exception | str) -> None:
        self._conn = None
        self.offline = True
        self.erro_conexao = str(erro)
        self.usuario = "offline"
        self.dsn = "sem banco"
        self.origem = "dev"

    @property
    def conn(self) -> oracledb.Connection:
        if self._conn is None:
            return self.conectar()
        return self._conn

    def fechar(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
