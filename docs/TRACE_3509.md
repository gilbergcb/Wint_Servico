# Trace da rotina 3509 — Inclusão de O.S. com serviço (capturado via V$SQL)

Capturado do `oracle-dev` (V$SQL/V$SQL_BIND_CAPTURE) durante a inclusão real da
**O.S. nº 2** na 3509 (PCSIS3509 v.37.0.0.16): cliente 5207, RCA 1, veículo
HPE2A24 (cadastrado na hora), KM 10000, cobrança 237, plano A VISTA, 1 serviço
`CODPROD=201198` (ALINHAMENTO), Valor R$ 120,00. Sem peças, sem faturar.

## Sequência cronológica (sessões SID 143/144, PROGRAM=PCSIS3509.EXE)

1. **Reserva do NUMOS** — `SELECT DFSEQ_PCORDEMSERVICO.NEXTVAL FROM DUAL`
2. **Reserva do NUMOSSERVICO** — `SELECT DFSEQ_PCORDEMSERVICOI.NEXTVAL [NUMOSSERVICO] FROM DUAL`
3. **Veículo (cascata normalizada)**:
   - `SEQ_PCOSVEICULOMARCA.NEXTVAL` → `INSERT INTO PCOSVEICULOMARCA (CODOSMARCA, MARCA)`
   - `SEQ_PCOSVEICULOMODELO.NEXTVAL` → `INSERT INTO PCOSVEICULOMODELO (CODOSMARCA, CODOSMODELO, MODELO)`
   - `SEQ_PCOSVEICULO.NEXTVAL` → `INSERT INTO PCOSVEICULO (CODOSVEICULO, PLACA, CODOSMODELO, ANO, CODOSCOMBUSTIVEL, MOTOR, OBS, DTCADASTRO)`
4. **Gravar O.S.** (header inserido por ÚLTIMO):
   - `DELETE FROM PCORDEMSERVICOI WHERE NUMOS = :NUMOS AND NVL(CODPROD,0) = 0` (limpa só linhas vazias)
   - `INSERT INTO PCORDEMSERVICOI (...)` — linha de serviço
   - `UPDATE PCORDEMSERVICOPARTICIP SET NUMOS = :NUMOS WHERE NUMOS = 0` (participantes temp→real)
   - `INSERT INTO PCORDEMSERVICO (...)` — cabeçalho

## Statements (colunas exatas)

**PCORDEMSERVICO** (`sql_id=gah1k3ff93a19`):
```
INSERT INTO PCORDEMSERVICO (
 NUMOS, CODEMITENTE, CODRCA, TIPOOS, CODPRODPRINC, NUMOSPRIMARIA,
 REMESSACOMODATO, NUMCONTRATOCOMODATO, CODPLPAG, CODCLI, CODFILIAL, OBS,
 CODCOB, NUMSERIE, DTPREVTERM, SITUACAO, DTCADASTRO, DTFECHA, CODOSVEICULO,
 KM, NUMTRANSVENDAPROD, NUMTRANSVENDASERV, NUMNOTAPREF)
VALUES (:NUMOS, ... , SYSDATE/NULL p/ DTCADASTRO/DTFECHA , ...)
```
Binds (21): NUMOS, CODEMITENTE, CODRCA, TIPOOS, CODPRODPRINC, NUMOSPRIMARIA,
REMESSACOMODATO, NUMCONTRATOCOMODATO, CODPLPAG, CODCLI, CODFILIAL, OBS, CODCOB,
NUMSERIE, DTPREVTERM, SITUACAO, CODOSVEICULO, KM, NUMTRANSVENDAPROD,
NUMTRANSVENDASERV, NUMNOTAPREF. (DTCADASTRO/DTFECHA não são bind → literais.)
NUMPED não é gravado nesta inclusão (O.S. sem pedido).

**PCORDEMSERVICOI** (`sql_id=6jf0cnkb8k9yv`):
```
INSERT INTO PCORDEMSERVICOI (
 NUMOSSERVICO, NUMOS, CODPROD, CODFUNC, PRECO, PUNIT, QTDE, DTINICIO, DTFINAL,
 RETERISS, PERCCOMISSAO, COMISSAO, TITULOLEVANTAMENTO, DETALHELEVANTAMENTO,
 PERCALIQISSRETIDA)
VALUES (:NUMOSSERVICO, :NUMOS, :CODPROD, :CODFUNC, :PRECO, :PUNIT, :QTDE,
 :DTINICIO, :DTFINAL, :RETERISS, :PERCCOMISSAO, :COMISSAO, :TITULOLEVANTAMENTO,
 :DETALHELEVANTAMENTO, :PERCALIQISSRETIDA)
```

**PCOSVEICULO** (`sql_id=642kxfar711v4`):
```
INSERT INTO PCOSVEICULO (CODOSVEICULO, PLACA, CODOSMODELO, ANO,
 CODOSCOMBUSTIVEL, MOTOR, OBS, DTCADASTRO)
VALUES (:CODOSVEICULO, :PLACA, :CODOSMODELO, :ANO, :CODOSCOMBUSTIVEL, :MOTOR,
 :OBS, :DTCADASTRO)
```
(Veículo nativo é normalizado por CODOSMODELO/CODOSCOMBUSTIVEL e NÃO grava CODCLI.)

## Confronto com OrdemServicoRepoWinthor (nosso)

| Item | Rotina 3509 nativa | Nosso repo | Status |
|------|--------------------|------------|--------|
| NUMOS | `DFSEQ_PCORDEMSERVICO.NEXTVAL` | idem | ✅ igual |
| NUMOSSERVICO | `DFSEQ_PCORDEMSERVICOI.NEXTVAL` | idem | ✅ igual |
| Colunas cabeçalho | conjunto acima | subconjunto compatível (+NUMPED) | ✅ compatível |
| Colunas serviço | conjunto acima | mesmo conjunto | ✅ igual |
| DTCADASTRO | literal SYSDATE | SYSDATE | ✅ |
| DTINICIO | bind | NVL(:dtinicio, SYSDATE) | ✅ |

## Divergências p/ próximas fases

- **Veículo (fase 2):** nativo usa cascata MARCA→MODELO→PCOSVEICULO (3 sequences)
  e modelo/combustível normalizados; nosso `PCM_OS_VEICULO` é texto livre e tem
  CODCLI. Para o modo Winthor, o cadastro de veículo precisa replicar a cascata.
- **Participantes (fase 2):** `PCORDEMSERVICOPARTICIP` no padrão temp(NUMOS=0)→
  UPDATE. Nosso repo ainda não grava participantes (técnico vai só em CODFUNC do
  item de serviço).
- **DELETE de itens:** a rotina remove só linhas vazias (`NVL(CODPROD,0)=0`);
  nosso repo faz delete-all + reinsert (mais simples; ok para o nosso fluxo).
- **Peças:** não exercitadas no trace original (sem produto). **Confirmado no
  2º trace abaixo.**

## 2º trace — O.S. nº 3 COM peça (capturado 2026-06-07 14:30)

O.S. nº 3 (PCSIS3509 v.37.0.0.16): cliente 5207, RCA 1, veículo HPE2A24
(VOLKS/FH/2023), KM 100040, cobrança 237, A VISTA, 1 serviço `CODPROD=201198`
(R$ 120,00) **+ 1 peça `CODPROD=20085` (R$ 4,99)**. Total R$ 124,99. Sem faturar.

**PCITEMSERVICO** (`sql_id=9xsmt422hrvk8`):
```
INSERT INTO PCITEMSERVICO (
 NUMOSSERVICO, CODPROD, QTDE, PVENDA, PTABELA, PERCDESC, DEMONSTRACAO,
 CODFILIALRETIRA, CODEQUIPAMENTO, NUMSERIEEQUIP, NUMLOTE, EQUIPAMENTO)
VALUES (:NUMOSSERVICO, :CODPROD, :QTDE, :PVENDA, :PTABELA, :PERCDESC,
 :DEMONSTRACAO, :CODFILIALRETIRA, :CODEQUIPAMENTO, :NUMSERIEEQUIP, :NUMLOTE,
 :EQUIPAMENTO)
```
Linha realmente gravada (lida da tabela):
`NUMOSSERVICO=4, CODPROD=20085, QTDE=1, PVENDA=4.99, PTABELA=4.99, PERCDESC=0,
DEMONSTRACAO='N', CODFILIALRETIRA='1', CODEQUIPAMENTO=0, NUMSERIEEQUIP='0',
NUMLOTE='0', EQUIPAMENTO='N'`.

**Confirmações importantes:**
- ✅ **Peça é filha da LINHA DE SERVIÇO via `NUMOSSERVICO`** (=4, a linha do serviço
  201198), **não via NUMOS** — valida a decisão de vincular a peça à linha de
  serviço (exige ≥1 serviço). Bate com `salvar_produtos` (usa MIN(NUMOSSERVICO)).
- ✅ Schema confirmado: NOT NULL = `NUMOSSERVICO, CODPROD, CODEQUIPAMENTO,
  NUMLOTE, NUMSERIEEQUIP`. `NUMSERIEEQUIP` tem **DEFAULT `'0'`**. Demais nullable.

**Divergências do nosso `salvar_produtos` (PCITEMSERVICO) a corrigir:**
1. **Defaults da PK:** nativo grava `NUMLOTE='0'` e `NUMSERIEEQUIP='0'` (string
   zero, = default da coluna). Nosso repo usa `' '` (espaço) → trocar para `'0'`.
2. **CODDEPOSITO:** nosso INSERT grava `CODDEPOSITO=NULL`; o nativo **não** grava
   essa coluna. Remover do INSERT (é nullable).
3. **Colunas que o nativo preenche e nós omitimos:** `PTABELA` (= PVENDA),
   `DEMONSTRACAO='N'`, `CODFILIALRETIRA` (= CODFILIAL da O.S.), `EQUIPAMENTO='N'`.
   Adicionar para fidelidade (todas nullable, mas o nativo popula).
4. **`PERCDESC` EXISTE** (nativo grava 0). A doc antiga dizia "sem desconto por
   item no nativo" — **incorreto**; dá para persistir `vl_desconto`/`perc_desc`.
```
