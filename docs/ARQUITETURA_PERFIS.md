# Arquitetura dos dois perfis de operação (MODO_OPERACAO)

A rotina passa a suportar **dois perfis de cliente**, escolhidos em
**Configuração → Modo de operação** e persistidos em `PCM_PARAM`
(chave `MODO_OPERACAO`):

| Valor | Significado | Backend de persistência |
|-------|-------------|--------------------------|
| `PCM` (default) | Tabelas próprias | `PCM_OS`, `PCM_OS_SERVICO`, `PCM_OS_PRODUTO`, `PCM_OS_FATURA`, ... |
| `WINTHOR` | 100% módulo 35 | `PCORDEMSERVICO`, `PCORDEMSERVICOI`, `PCITEMSERVICO`, transação de venda → `PCNFSAID`/`PCMOV`/`PCPREST` |

Mapeamento detalhado das tabelas nativas: ver [MAPEAMENTO_MODULO35.md](MAPEAMENTO_MODULO35.md).

## Costura (seam) — ponto único de troca

`core/os_repo_factory.py` → `obter_os_repo()` devolve o repositório de O.S. do
perfil ativo. **Toda a UI/serviços devem obter o repositório por aqui**, nunca
instanciando `OrdemServicoRepo` direto, para que a troca de perfil seja
transparente.

- `PCM` → `OrdemServicoRepo` (atual, tabelas `PCM_*`).
- `WINTHOR` → `OrdemServicoRepoWinthor` (`core/ordem_servico_repo_winthor.py`).

A UI de O.S. e os dashboards (`tela_os_lista`, `tela_os_edicao`, `tela_home`,
`tela_acompanhamento`) já obtêm o repositório via `obter_os_repo()` de forma
lazy (após o guard de offline, para não tocar o banco no startup).

## Plano de implementação do backend WINTHOR (fases)

1. **CRUD de cabeçalho/itens nativo — ✅ FEITO** — `OrdemServicoRepoWinthor`
   espelha `OrdemServicoRepo`: grava `PCORDEMSERVICO` (NUMOS via
   `DFSEQ_PCORDEMSERVICO`), serviços em `PCORDEMSERVICOI` (`DFSEQ_PCORDEMSERVICOI`,
   `DTINICIO` default SYSDATE), produtos em `PCITEMSERVICO`. **Limitações
   conhecidas:** peças são filhas da linha de serviço (FK `PCITEMSERVICO ->
   PCORDEMSERVICOI`) → todas vinculadas à 1ª linha de serviço (exige ≥1 serviço);
   PK composta com defaults `CODEQUIPAMENTO=0`/`NUMLOTE=' '`/`NUMSERIEEQUIP=' '`
   (2 produtos com mesmo `CODPROD` colidem); sem desconto por item; `TIPOOS`
   texto↔numérico. SELECTs validados no banco; INSERT/UPDATE pendentes de teste
   em runtime na VM. `PCOSMOBILE_ORDEMSERVICO` existe (trigger mobile OK).
2. **Tipo de O.S.** — mapear nosso `TIPOOS` (texto) para `PCTIPOORDEMSERVICO.CODTIPO`
   (numérico, herda flags de geração de contas a receber/participantes).
3. **Veículo** — `PCOSVEICULO` (PK `CODOSVEICULO`, seq `SEQ_PCOSVEICULO`) com
   marca/modelo normalizados em `PCOSVEICULOMARCA/MODELO`.
4. **Faturamento nativo** — em vez de `PCM_OS_FATURA`, gerar `NUMPED` + transação
   de venda (`NUMTRANSVENDASERV/PROD/FECHA`) → `PCNFSAID`/`PCMOV` e, conforme
   `GERARCONTASRECEBER*`, títulos em `PCPREST`. Reaproveitar procedure/numeradores
   do ERP (não usar sequence própria). Liga-se ao parâmetro `TIPO_FATURAMENTO`.
5. **Catálogo/leitura** — serviço = produto em `PCPRODUT`; participantes/técnicos
   em `PCORDEMSERVICOPARTICIP`; orçamento `PCORDEMORCAMENTO(I)` → O.S.

## Decisões já tomadas

- Perfil é **global** (parâmetro único para a instalação/cliente), não por usuário.
- Trocar de perfil com O.S. já cadastradas pode deixar dados em backends
  diferentes — trocar com base vazia ou após migração (aviso na tela).
- Faturamento (`TIPO_FATURAMENTO`) e pedido obrigatório (`PEDIDO_OBRIGATORIO`)
  permanecem como parâmetros próprios; no perfil WINTHOR o faturamento passa a
  ser o nativo (fase 4).
