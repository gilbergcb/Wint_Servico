# Wint_servico - Modulo de Servico Winthor (Oficina / Borracharia)

Rotina desktop (PyQt6) para gestao de Ordens de Servico no ERP TOTVS Winthor:
cadastro de servicos, O.S., acompanhamento, faturamento, NFS-e e relatorios.
Persistencia em tabelas proprias prefixo `PCM_*`.

Veja o plano completo em [`docs/PLANO_TECNICO.md`](docs/PLANO_TECNICO.md).

## Stack
- PyQt6 + python-oracledb (dual-mode thin/thick) + SQLAlchemy Core
- Empacotamento: PyInstaller, .exe 64-bit
- Chamada pelo menu Winthor: `app.exe USUARIOWT SENHABD ALIASBD USUARIOBD CODROTINA`

## Desenvolvimento (rodar offline, sem banco)

```
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
abrir_app.bat
```

Com `SVC_DEV_OFFLINE=1` (ou rodando nao-empacotado) o app abre mesmo sem banco.

## Conexao com o banco

Configurada por env vars no `.env` (ver `.env.example`):

- `SVC_DB_MODE` = `thin` (Oracle 12.1+) ou `thick` (Instant Client).
- `SVC_ORACLE_CLIENT_LIB_DIR` = pasta do Instant Client (so no modo thick).

> Ambiente de TESTE = Oracle 10g (10.2.0.3.0): o modo `thin` NAO funciona;
> use `SVC_DB_MODE=thick` com Instant Client **11.2 ou 12.x** (NAO 19c) e
> **64-bit** (mesma bitness do .exe; conversa normalmente com o servidor 10g).

## Banco de dados

DDL das tabelas proprias em [`scripts/ddl_pcm.sql`](scripts/ddl_pcm.sql).
Decisao pendente: PCM_SERVICO vinculado a PCPRODUT (Opcao A, recomendada) vs.
catalogo standalone (Opcao B). Confirmar antes de promover ao banco.

## Build (.exe 64-bit)

Defina os CODCLIPC liberados em `codclipc_liberados.txt` e rode:

```
build.bat
```

Gera `dist\PCWNT_9520.exe` (codigo generico 9520; renomeie APP_NAME/spec se houver codigo oficial).

## Pendencias (confirmar com o usuario)
- COD_ROTINA = `9520` (generico/provisorio; trocar se houver codigo oficial).
- Opcao A vs. B de PCM_SERVICO.
- NFS-e: municipio, padrao/provedor e certificado A1.
