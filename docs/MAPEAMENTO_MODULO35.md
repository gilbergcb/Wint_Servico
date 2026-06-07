# Mapeamento do Módulo 35 (Serviço/Oficina) do Winthor

> Documento gerado a partir da leitura do banco real (MCP `oracle-dev`, somente
> `SELECT`/`describe`). As tabelas nativas estavam **vazias** no ambiente
> consultado (instalação limpa), portanto os domínios de `SITUACAO`/`TIPOOS`
> abaixo são inferidos do schema e da documentação do produto, não de dados.

## 1. Visão geral do fluxo nativo

O módulo 35 trabalha com duas frentes que se cruzam na Ordem de Serviço (OS):
os **serviços** (mão de obra, faturados como serviço / NFS-e ou nota de serviço)
e os **produtos/peças** (faturados como venda de mercadoria, com baixa de
estoque e nota fiscal de produto). O coração é `PCORDEMSERVICO` (cabeçalho).

Fluxo (orçamento → OS → itens → faturamento → financeiro):

- **Orçamento (opcional)** — `PCORDEMORCAMENTO` (cabeçalho) + `PCORDEMORCAMENTOI`
  (itens de serviço do orçamento). Ao aprovar, o orçamento vira OS
  (`PCORDEMSERVICO.NUMORCAMENTO` aponta de volta para o orçamento de origem).
- **Abertura da OS** — insere em `PCORDEMSERVICO`. Define `CODCLI`, `CODFILIAL`,
  `TIPOOS` (→ `PCTIPOORDEMSERVICO`), `SITUACAO`, veículo (`CODOSVEICULO` →
  `PCOSVEICULO`), cobrança/plano de pagamento (`CODCOB`/`CODPLPAG`).
  A trigger `TRG_INTEGRA_OSMOBILE_PCOS` (AFTER INSERT) replica a OS para
  `PCOSMOBILE_ORDEMSERVICO` (integração com o app OS Mobile).
- **Itens de serviço** — `PCORDEMSERVICOI` (mão de obra/serviços, com técnico
  `CODFUNC`, comissão, retenção de ISS/INSS, levantamento).
- **Itens de produto/peça** — `PCITEMSERVICO` (peças, equipamentos, lote, série,
  depósito). É a tabela de produtos consumidos na OS.
- **Participantes** — `PCORDEMSERVICOPARTICIP` (cliente, RCA, supervisor,
  funcionário/técnico) — quem participa e como é remunerado/comissionado.
- **Faturamento** — gera **transações de venda** (`NUMTRANSVENDASERV` para
  serviço, `NUMTRANSVENDAPROD` para produto, `NUMTRANSVENDAFECHA` para o
  fechamento) e o pedido (`NUMPED`). Cada transação materializa:
  - `PCNFSAID` (nota fiscal de saída) — carrega `NUMTRANSVENDA` **e** `NUMOS`,
    ligando a nota de volta à OS;
  - `PCMOV` (movimentação de estoque/itens) — vinculada por `NUMTRANSVENDA`
    (e `NUMTRANSITEM`), faz a baixa de estoque das peças.
  - `PCLOGFATURAMENTOORDEMSERVICO` registra o log (NUMOS, NUMPED, mensagem).
- **Financeiro** — conforme `GERARCONTASRECEBERSERV`/`GERARCONTASRECEBERPROD`
  (flags na OS, herdadas de `PCTIPOORDEMSERVICO.GERARCONTRECEBER*`), o
  faturamento gera títulos em **`PCPREST`** (contas a receber). `NUMNOTAPREF`
  guarda o número da nota da prefeitura (NFS-e) quando aplicável.

Diagrama (lista):

```
PCORDEMORCAMENTO ─┬─ PCORDEMORCAMENTOI            (orçamento → itens serviço)
                  │
                  ▼ (aprovação: NUMORCAMENTO)
PCORDEMSERVICO ───┬─ PCORDEMSERVICOI              (itens de SERVIÇO / mão de obra)
 (cabeçalho OS)   ├─ PCITEMSERVICO                (itens de PRODUTO / peça)
                  ├─ PCORDEMSERVICOPARTICIP       (participantes/comissão)
                  ├─ PCOSVEICULO ── PCOSVEICULOMODELO ── PCOSVEICULOMARCA
                  │                              └─ PCOSVEICULOCOMBUSTIVEL
                  └─ PCTIPOORDEMSERVICO           (tipo de OS: flags de geração)
                  │
                  ▼ faturamento (NUMTRANSVENDASERV / NUMTRANSVENDAPROD / NUMPED)
PCNFSAID (nota, traz NUMOS) ── PCMOV (baixa estoque) ── PCPREST (contas a receber)
                  │
                  └─ PCLOGFATURAMENTOORDEMSERVICO (log)   NUMNOTAPREF → NFS-e
```

## 2. Tabelas nativas — colunas relevantes

### 2.1 PCORDEMSERVICO — cabeçalho da OS (PK: `NUMOS`)
Já mapeada (ver enunciado). Único NOT NULL físico: `NUMOS`. Sequence:
`DFSEQ_PCORDEMSERVICO`. Trigger AFTER INSERT `TRG_INTEGRA_OSMOBILE_PCOS`.
Campos-chave de faturamento: `NUMTRANSVENDASERV`, `NUMTRANSVENDAPROD`,
`NUMTRANSVENDAFECHA`, `NUMPED`, `NUMORCAMENTO`, `NUMNOTAPREF`,
`GERARCONTASRECEBERSERV/PROD`, `NUMEROLANCAMENTO`.

### 2.2 PCORDEMSERVICOI — itens de SERVIÇO (PK: `NUMOSSERVICO`)
NOT NULL físicos: `NUMOSSERVICO`, `DTINICIO`. Sequence: `DFSEQ_PCORDEMSERVICOI`.
A PK é o **próprio item** (`NUMOSSERVICO`), não a OS; `NUMOS` é FK lógica.
Colunas: `NUMOS`, `CODPROD`, `CODFUNC` (técnico), `QTDE`, `PUNIT`, `PRECO`,
`RETERISS`, `PERCALIQISSRETIDA`, `COMISSAO`, `PERCCOMISSAO`, `TEMPOSERVICO`,
`TITULOLEVANTAMENTO`, `DETALHELEVANTAMENTO` + retenções (INSS/CPRB/SLL).

### 2.3 PCITEMSERVICO — itens de PRODUTO/PEÇA da OS
PK composta: `NUMOSSERVICO, CODPROD, CODEQUIPAMENTO, NUMSERIEEQUIP, NUMLOTE`.

| Coluna | Tipo | NN | Significado |
|---|---|---|---|
| NUMOSSERVICO | NUMBER(6) | N | Nº da OS (mesmo domínio de NUMOS) |
| CODPROD | NUMBER(6) | N | Produto/peça (→ PCPRODUT) |
| QTDE | NUMBER(22,8) | Y | Quantidade |
| PVENDA | NUMBER(22,8) | Y | Preço de venda |
| PTABELA / PERCDESC | NUMBER | Y | Preço tabela / % desconto |
| CODFILIALRETIRA | VARCHAR2(2) | Y | Filial de retirada |
| CODEQUIPAMENTO | NUMBER(6) | N | Equipamento (parte da PK; usar 0 default) |
| NUMLOTE | VARCHAR2(15) | N | Lote (parte da PK) |
| NUMSERIEEQUIP | VARCHAR2(30) | N | Nº série do equipamento (parte da PK) |
| CODDEPOSITO | NUMBER(10) | Y | Depósito de estoque |
| DEMONSTRACAO / EQUIPAMENTO | VARCHAR2(1) | Y | Flags |
| OBSERVACAODOPRODUTO | VARCHAR2(1000) | Y | Observação |

> Atenção: `CODEQUIPAMENTO`, `NUMLOTE`, `NUMSERIEEQUIP` são **NOT NULL e fazem
> parte da PK** — para peça comum sem lote/série é preciso preencher com valores
> default (ex.: 0 / espaço) para inserir.

### 2.4 PCORDEMSERVICOPARTICIP — participantes (PK: `NUMOS, CODIGO, TIPO`)
| Coluna | Tipo | NN | Significado |
|---|---|---|---|
| NUMOS | NUMBER(6) | N | OS |
| CODIGO | NUMBER(6) | N | Código do participante (RCA/func/supervisor) |
| TIPO | VARCHAR2(1) | N | Tipo de participante (C/R/S/F…) |
| CODCLI | NUMBER(9) | Y | Cliente associado |
| COMENTARIO | VARCHAR2(500) | Y | Observação |

### 2.5 PCTIPOORDEMSERVICO — tipos de OS (PK: `CODTIPO`)
Define o comportamento da OS. Flags `VARCHAR2(1)` S/N:
`GERARCONTRECEBERSERVICO`, `GERARCONTRECEBERPRODUTO`, `PARTICIPANTECLIENTE`,
`PARTICIPANTERCA`, `PARTICIPANTESUPERVISOR`, `PARTICIPANTEFUNC`, `OSCOMODATO`,
`PERMITEFATOSABERTA`, `GERAREMESSCOMODATO`, `ALTERASTATUSOS`, `GERARNOTATV1`.
`DESCRICAO` VARCHAR2(40). É a tabela que parametriza o tipo (`TIPOOS` na OS
referencia `CODTIPO`).

### 2.6 PCORDEMORCAMENTO — orçamento, cabeçalho (PK: `NUMORCAMENTO`)
Espelha a OS no formato orçamento. Colunas: `CODCOB`, `CODPLPAG`, `CODCLI`,
`CODRCA`, `CODEMITENTE`, `SITUACAO` NUMBER(1), `TIPOOS`, `CODFILIAL`,
`NUMTRANSVENDASERV`, `NUMTRANSVENDAPROD`, `NUMPED`, `NUMOSPRIMARIA`,
`CODPRODPRINC`, comodato (`NUMTRANVENDACOMODATO`, `REMESSACOMODATO`,
`NUMCONTRATOCOMODATO`…), `OBS` CLOB. Sem sequence dedicada localizada (usa
numerador da rotina / `DFSEQ_ORCAMENTOENTREGA` p/ entrega).

### 2.7 PCORDEMORCAMENTOI — itens de serviço do orçamento (PK: `NUMOSORCAMENTO`*)
\* O banco **não tem PK física** declarada nesta tabela. `NUMOSORCAMENTO` é o
identificador do item (NOT NULL); `NUMORCAMENTO` é FK lógica para o cabeçalho.
Espelha `PCORDEMSERVICOI`: `CODPROD`, `CODFUNC`, `PRECO`, `PUNIT`, `QTDE`,
`DTINICIO` (NN), `DTFINAL`, `RETERISS`, `PERCALIQISSRETIDA`, `COMISSAO`,
`PERCCOMISSAO`, `STATUS` NUMBER(1), `PERCSLL`.

### 2.8 PCOSVEICULO — veículo (PK: `CODOSVEICULO`) — sequence `SEQ_PCOSVEICULO`
NOT NULL: `CODOSVEICULO`, `PLACA`, `CODOSMODELO`, `ANO`, `CODOSCOMBUSTIVEL`,
`DTCADASTRO`. Demais: `MOTOR`, `OBS`. **Não há `CODCLI` nem `MARCA` direta** —
a marca vem por `PCOSVEICULOMODELO.CODOSMARCA`; não há vínculo nativo
veículo↔cliente (a associação cliente é feita pela OS, via `CODCLI`).

### 2.9 Tabelas de apoio do veículo
- `PCOSVEICULOMARCA` (PK `CODOSMARCA`; `MARCA`) — seq `SEQ_PCOSVEICULOMARCA`.
- `PCOSVEICULOMODELO` (PK `CODOSMARCA, CODOSMODELO`; `MODELO`) — seq
  `SEQ_PCOSVEICULOMODELO`. **Modelo pertence a uma marca.**
- `PCOSVEICULOCOMBUSTIVEL` (`CODOSCOMBUSTIVEL`, `COMBUSTIVEL`) — domínio fixo.

### 2.10 PCSERVICO — catálogo de "serviços/ofertas" (PK: `CODSERVICO`)
Tabela de catálogo/oferta (estilo licenciamento/serviços adquiridos):
`IDSERVICO`, `NOME`, `DESCRICAO`, `MODELOPRECIFICACAO`, `PRECO` (VARCHAR2),
`DATAVALIDADE`, `ADQUIRIDO`/`UTILIZADO`/`OFERTAEXPIROU` (CHAR(1) NN),
`TIPOSERVICO`, `DATAAQUISICAO`, `QUANTIDADE`. **Não é** o catálogo de mão de
obra da OS — não tem aliquota de ISS nem vínculo a CODPROD. No fluxo da OS, o
"serviço" faturável é um **PRODUTO** (`PCPRODUT`) referenciado pelo item
(`PCORDEMSERVICOI.CODPROD`).

### 2.11 PCLOGFATURAMENTOORDEMSERVICO — log de faturamento
Colunas simples: `NUMOS`, `NUMPED`, `MENSAGEM` VARCHAR2(100). Apenas auditoria.

### 2.12 PCTERMOUSOSERVICO — termo de uso (PK: `CODTERMOUSO`)
`CNPJ`, `USUARIOLOGADO`, `DATA`, `TIPOSERVICO`, `DESTINO`, `ACEITO` CHAR(1),
`ARQUIVO` CLOB. Sequence `DFSEQ_PCTERMOUSOSERVICO`. Controle de aceite de termo,
periférico ao fluxo operacional.

## 3. Sequences e triggers nativos relevantes

| Objeto | Tipo | Observação |
|---|---|---|
| DFSEQ_PCORDEMSERVICO | SEQUENCE | numerador de `NUMOS` |
| DFSEQ_PCORDEMSERVICOI | SEQUENCE | numerador de `NUMOSSERVICO` (item serviço) |
| DFSEQ_PCTERMOUSOSERVICO | SEQUENCE | termo de uso |
| SEQ_PCOSVEICULO | SEQUENCE | numerador `CODOSVEICULO` |
| SEQ_PCOSVEICULOMARCA / SEQ_PCOSVEICULOMODELO | SEQUENCE | marca/modelo |
| DFSEQ_ORCAMENTOENTREGA | SEQUENCE | entrega de orçamento |
| TRG_INTEGRA_OSMOBILE_PCOS | TRIGGER (AFTER INSERT em PCORDEMSERVICO) | replica a OS para `PCOSMOBILE_ORDEMSERVICO` (app mobile). Não numera nem fatura. |

> Não há sequence localizada especificamente para `PCITEMSERVICO` nem para
> `NUMPED`/transações de venda — o número do pedido e as transações de venda
> são gerados pela própria rotina de faturamento do Winthor (numeradores
> globais `PCCONSUM`/procedures internas), não por sequence dedicada da OS.

## 4. Comparativo PCM_* (nossas) × nativa do módulo 35

### 4.1 Cabeçalho — `PCM_OS` ↔ `PCORDEMSERVICO`
| PCM_OS (nossa) | PCORDEMSERVICO (nativa) | Observação |
|---|---|---|
| NUMOS (PK) | NUMOS (PK) | seq própria `PCM_OS_SEQ` vs `DFSEQ_PCORDEMSERVICO` |
| CODFILIAL | CODFILIAL | |
| CODCLI | CODCLI | |
| CODRCA | CODRCA | |
| CODFUNCABERTURA | CODEMITENTE (≈) | nativa usa CODEMITENTE/CODRCA |
| CODVEICULO (→PCM_OS_VEICULO) | CODOSVEICULO (→PCOSVEICULO) | |
| TIPOOS VARCHAR2(2) | TIPOOS NUMBER (→ CODTIPO) | **divergência de tipo**: nativa é numérico → PCTIPOORDEMSERVICO |
| SITUACAO NUMBER(1) | SITUACAO | domínios podem divergir |
| KM | KM | |
| CODCOB / CODPLPAG | CODCOB / CODPLPAG | |
| VLTOTALSERVICO/PRODUTO/DESCONTO/TOTAL | (calculados em transação) | nativa não guarda totais no cabeçalho da mesma forma |
| DTCADASTRO/DTPREVTERM/DTFECHA/DTCANCEL | idem | |
| MOTIVOCANCEL | MOTIVOCANCEL | |
| NUMTRANSVENDASERV/PROD | NUMTRANSVENDASERV/PROD | + nativa tem NUMTRANSVENDAFECHA |
| NUMPED | NUMPED | |
| — | NUMORCAMENTO, NUMNOTAPREF, NUMEROLANCAMENTO, GERARCONTASRECEBER*, CODPRODPRINC, NUMSERIE, comodato | **sem equivalente nosso** |

### 4.2 Itens de serviço — `PCM_OS_SERVICO` ↔ `PCORDEMSERVICOI`
| PCM_OS_SERVICO | PCORDEMSERVICOI | Observação |
|---|---|---|
| NUMOSSERVICO (PK) | NUMOSSERVICO (PK) | |
| NUMOS | NUMOS | |
| CODSERVICO (→PCM_SERVICO) | — | **não existe** na nativa; nativa usa só CODPROD |
| CODPROD | CODPROD | o "serviço" nativo é um produto |
| CODFUNC | CODFUNC | técnico |
| QTDE/PUNIT/PRECO | QTDE/PUNIT/PRECO | |
| VLDESCONTO | — (via PERCDESC/transação) | |
| PERCCOMISSAO/COMISSAO | PERCCOMISSAO/COMISSAO | |
| RETERISS/PERCALIQISSRETIDA | RETERISS/PERCALIQISSRETIDA | |
| DTINICIO/DTFINAL | (DTINICIO NN na nativa) | |
| TITULO/DETALHELEVANTAMENTO | TITULO/DETALHELEVANTAMENTO | |
| — | retenções INSS/CPRB/SLL/subcontratada | sem equivalente nosso |

### 4.3 Itens de produto — `PCM_OS_PRODUTO` ↔ `PCITEMSERVICO`
| PCM_OS_PRODUTO | PCITEMSERVICO | Observação |
|---|---|---|
| NUMOSPRODUTO (PK simples) | (PK composta NUMOSSERVICO+CODPROD+CODEQUIPAMENTO+NUMSERIEEQUIP+NUMLOTE) | **modelo de PK muito diferente** |
| NUMOS | NUMOSSERVICO | nome diferente, mesmo domínio |
| CODPROD | CODPROD | |
| QTDE | QTDE | |
| PUNIT/PRECO | PVENDA/PTABELA | |
| VLDESCONTO | PERCDESC (%) | nativa usa percentual |
| BAIXAESTOQUE | — (baixa ocorre via transação/PCMOV) | |
| — | CODEQUIPAMENTO, NUMLOTE, NUMSERIEEQUIP (NN, PK), CODDEPOSITO, CODFILIALRETIRA | **obrigatórios na nativa, sem equivalente nosso** |

### 4.4 Catálogo de serviço — `PCM_SERVICO` ↔ ?
Não há equivalente nativo direto. Nativa não tem "catálogo de mão de obra" com
ISS — o serviço é um **PRODUTO em `PCPRODUT`** (decisão "Opção A" já no nosso
DDL). `PCSERVICO`/`PCITEMSERVICO` **não** cumprem esse papel (PCSERVICO é
catálogo de ofertas/licenças; PCITEMSERVICO é item de produto da OS).

### 4.5 Veículo — `PCM_OS_VEICULO` ↔ `PCOSVEICULO`
| PCM_OS_VEICULO | PCOSVEICULO | Observação |
|---|---|---|
| CODVEICULO (PK) | CODOSVEICULO (PK) | |
| PLACA | PLACA (NN) | |
| MARCA (texto) | CODOSMARCA → PCOSVEICULOMARCA | nativa é **normalizada** (marca/modelo em tabela) |
| MODELO (texto) | CODOSMODELO → PCOSVEICULOMODELO | |
| COMBUSTIVEL (texto) | CODOSCOMBUSTIVEL → PCOSVEICULOCOMBUSTIVEL | |
| ANO/MOTOR/OBS | ANO/MOTOR/OBS | |
| CODCLI | — | **nativa não vincula cliente ao veículo** |
| COR/CHASSI/KMATUAL | — | sem equivalente nativo |

## 5. Lacunas e pontos de atenção para "100% Winthor"

1. **Faturamento nativo = transação de venda, não tabela própria.** Faturar a OS
   no padrão Winthor significa gerar `NUMPED`/`NUMTRANSVENDASERV`/
   `NUMTRANSVENDAPROD` e materializar `PCNFSAID` + `PCMOV` (+ `PCPREST` no
   financeiro). Isso exige reproduzir a lógica/procedure de faturamento do ERP
   (numeradores globais, tributação, baixa de estoque, geração de título). Nosso
   `PCM_OS_FATURA` é faturamento interno e **não** gera esse encadeamento.

2. **PK composta de `PCITEMSERVICO`.** Para gravar peça na OS nativa é
   obrigatório preencher `CODEQUIPAMENTO`, `NUMLOTE`, `NUMSERIEEQUIP` (todos
   NOT NULL e parte da PK) e `CODDEPOSITO`. Nosso `PCM_OS_PRODUTO` (PK simples
   `NUMOSPRODUTO`) precisaria de defaults (0/espaço) e de mapear depósito/lote
   ao migrar para a nativa.

3. **`TIPOOS` é numérico e parametrizado.** Na nativa `TIPOOS` referencia
   `PCTIPOORDEMSERVICO.CODTIPO`, que controla flags de geração de contas a
   receber, participantes e comodato. Nosso `TIPOOS VARCHAR2(2)` ('B','M') não
   mapeia para esse cadastro — é preciso criar/usar tipos em
   `PCTIPOORDEMSERVICO` e herdar as flags `GERARCONTRECEBER*`.

4. **Sequences nativas existem — usar as do Winthor, não as nossas.**
   `DFSEQ_PCORDEMSERVICO` (NUMOS), `DFSEQ_PCORDEMSERVICOI`, `SEQ_PCOSVEICULO`,
   `SEQ_PCOSVEICULOMARCA/MODELO`. `NUMPED` e as transações de venda **não** têm
   sequence própria: dependem dos numeradores globais/procedures de faturamento
   do ERP. Operar 100% nativo implica obter esses números pela rotina padrão.

5. **Catálogo de mão de obra e veículo↔cliente sem equivalente nativo.** O
   "serviço" nativo é um produto (`PCPRODUT`), então nosso `PCM_SERVICO`
   (com ISS próprio) não tem espelho — manter como camada nossa apontando para
   CODPROD. E `PCOSVEICULO` **não** guarda cliente/cor/chassi/km — esses dados
   nossos (`CODCLI`, `COR`, `CHASSI`, `KMATUAL`) ficariam órfãos ao gravar na
   nativa (KM vai no cabeçalho `PCORDEMSERVICO.KM`; marca/modelo precisam ser
   normalizados em `PCOSVEICULOMARCA/MODELO`).

6. **Trigger de integração mobile.** Toda inserção em `PCORDEMSERVICO` dispara
   `TRG_INTEGRA_OSMOBILE_PCOS`, gravando em `PCOSMOBILE_ORDEMSERVICO`. Inserções
   diretas precisam que essa tabela/integração exista (ou a trigger falhará).

7. **Tributação/retenções mais ricas na nativa.** `PCORDEMSERVICOI` tem INSS
   (CPRB), SLL, subcontratada, processo — não modelados em `PCM_OS_SERVICO`.
   Para NFS-e/retenções completas seria necessário cobrir esses campos.
