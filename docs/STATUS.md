# Status do projeto — Wint_servico

Última atualização: 2026-06-06

Rotina desktop do módulo de Serviço (oficina / borracharia) para o ERP Winthor.
Stack: **PyQt6 + python-oracledb (dual-mode thin/thick) + SQLAlchemy Core**,
tabelas próprias **`PCM_*`**, empacotável como **.exe 64-bit** (PyInstaller).

## Fases

| Fase | Módulo | Status |
|------|--------|--------|
| 1 | **Cadastro de Serviço** (`PCM_SERVICO`, vínculo lógico a `PCPRODUT`) | ✅ Implementado e testado |
| 2 | **Ordem de Serviço** (cabeçalho + itens serviço/produto + veículo) | ✅ Implementado e testado |
| 3 | **Acompanhamento** (KPIs por situação, avanço de status) | ✅ Implementado e testado |
| 4 | **Faturamento próprio** (`PCM_OS_FATURA`; sem tocar nativas) | ✅ Implementado e testado e2e |
| 5 | **NFS-e** (emissão própria, certificado A1) | ⏳ **Pendente** |
| 6 | **Relatórios** (O.S. por situação, comissões, serviços; export CSV) | ✅ Implementado e testado |

### Extras implementados
- ✅ **Início / Dashboard** — quantidade de O.S. e O.S. por serviço, com período Hoje/Semana/Mês/Trimestre.
- ✅ **Configuração** — instalador idempotente do DDL (`Criar/atualizar objetos do banco`) para provisionar ambientes novos; testar conexão.
- ✅ **Menu lateral** colapsável (auto-hide) com ícones SVG e tema claro/escuro.

## Para iniciar a Fase 5 (NFS-e) — definições necessárias
- **Município** emissor (define o padrão/layout: ABRASF, Ginfes, Padrão Nacional…).
- **Provedor**: PyNFe direto ou gateway (PlugNotas / Focus / eNotas).
- **Certificado digital A1** (.pfx) e senha.
- Interface já pronta para plugar o provedor: `servicos/integrador_nfse.py`; tabela `PCM_NFSE` já existe.

## Pendências menores / TODO
- Confirmar o mecanismo de "produto-serviço" em `PCPRODUT` (não há coluna `SERVICO`); hoje o lookup filtra por código/descrição.
- **Filial padrão** da O.S.: hoje é campo editável no cabeçalho; definir se deriva do usuário/menu Winthor.
- Título financeiro a receber: fora de escopo atual (faturamento não gera título).
- `COD_ROTINA` genérico = `9520` (provisório; trocar se houver código oficial).

## Ambiente
- Teste: **Oracle 10g 10.2.0.3.0** em `192.168.1.253:1521/LOCAL` (usuário `LOCAL`).
- Conexão validada em **thick** com **Instant Client 23 x64** (`C:\instantclientx64\instantclient_23_0`).
- Produção: **thin** (Oracle 12.1+, sem Instant Client).

## Como rodar (dev)
```
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env   &  ajuste credenciais/modo
abrir_app.bat
```

## Scripts utilitários (`scripts/`)
- `_testar_conexao.py` — valida conexão thick + engine + se `PCM_SERVICO` existe.
- `_aplicar_ddl.py` — aplica/atualiza os objetos `PCM_*` (idempotente).
- `_testar_crud.py` — CRUD ponta a ponta das Fases 1 e 2 (cria e limpa dados).
- `_testar_faturamento.py` — e2e do faturamento (Fase 4).
- `_smoke_test.py` — sobe a UI offscreen/offline e valida construção das telas.

## Próximo passo sugerido
Fase 5 (NFS-e). Sugestão: criar branch `feature/nfse` antes de começar.
