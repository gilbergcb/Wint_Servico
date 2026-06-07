-- =====================================================================
-- DDL das tabelas proprias do modulo de SERVICO (oficina/borracharia)
-- Prefixo PCM_ : NUNCA gravar nas tabelas nativas do Winthor.
-- Banco de teste: Oracle 10g (10.2.0.3.0). Producao: Oracle 12.1+.
-- Compatibilidade 10g: evitar IDENTITY/DEFAULT-sequence; usar SEQUENCE + TRIGGER.
--
-- Decisao de design PCM_SERVICO:
--   Opcao A (RECOMENDADA / adotada aqui): PCM_SERVICO referencia
--     PCPRODUT.CODPROD. Reaproveita catalogo, tributacao de ISS, estoque
--     e cadastro fiscal ja existentes no Winthor. A rotina 3501 cadastra
--     o "servico" como PRODUTO flagueado, e o item da O.S. (PCORDEMSERVICOI)
--     aponta CODPROD -> PCPRODUT. Mantemos esse vinculo.
--   Opcao B (NAO adotada): catalogo standalone, sem vinculo a PCPRODUT.
--     Simples, mas duplica tributacao e perde integracao fiscal/estoque.
--   >>> CONFIRMAR COM O USUARIO antes de promover ao banco. <<<
--   FK para CODPROD e LOGICA (validada na aplicacao), pois nao criamos
--   constraint fisica contra tabela nativa do Winthor.
-- =====================================================================

-- ---------------------------------------------------------------------
-- SEQUENCES
-- ---------------------------------------------------------------------
CREATE SEQUENCE PCM_SERVICO_SEQ      START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE PCM_OS_SEQ           START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE PCM_OS_SERVICO_SEQ   START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE PCM_OS_PRODUTO_SEQ   START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE PCM_OS_VEICULO_SEQ   START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE PCM_NFSE_SEQ         START WITH 1 INCREMENT BY 1 NOCACHE;


-- ---------------------------------------------------------------------
-- PCM_SERVICO  -- catalogo de servicos (Opcao A: vinculado a PCPRODUT)
-- ---------------------------------------------------------------------
CREATE TABLE PCM_SERVICO (
  CODSERVICO        NUMBER(10)      NOT NULL,                  -- PK propria
  CODPROD           NUMBER(8),                                 -- FK LOGICA -> PCPRODUT.CODPROD (servico flagueado na 3501)
  DESCRICAO         VARCHAR2(100)   NOT NULL,
  CODFILIAL         VARCHAR2(2),                               -- filial padrao
  PRECOPADRAO       NUMBER(15,4)    DEFAULT 0,
  TEMPOESTIMADOMIN  NUMBER(6),                                 -- tempo estimado em minutos
  RETERISS          VARCHAR2(1)     DEFAULT 'N',               -- S/N retencao de ISS
  PERCALIQISS       NUMBER(7,4)     DEFAULT 0,                 -- aliquota ISS (%)
  CODSITTRIBPISCOFINS VARCHAR2(2),                             -- situacao tributaria opcional
  ATIVO             VARCHAR2(1)     DEFAULT 'S',               -- S/N
  OBS               VARCHAR2(400),
  DTCADASTRO        DATE            DEFAULT SYSDATE,
  DTALTERACAO       DATE,
  USUARIOCAD        VARCHAR2(30),
  CONSTRAINT PK_PCM_SERVICO PRIMARY KEY (CODSERVICO),
  CONSTRAINT CK_PCM_SERVICO_ATIVO CHECK (ATIVO IN ('S','N')),
  CONSTRAINT CK_PCM_SERVICO_RETERISS CHECK (RETERISS IN ('S','N'))
);
CREATE INDEX IDX_PCM_SERVICO_CODPROD ON PCM_SERVICO (CODPROD);

CREATE OR REPLACE TRIGGER PCM_SERVICO_BI
BEFORE INSERT ON PCM_SERVICO FOR EACH ROW
BEGIN
  IF :NEW.CODSERVICO IS NULL THEN
    SELECT PCM_SERVICO_SEQ.NEXTVAL INTO :NEW.CODSERVICO FROM DUAL;
  END IF;
END;
/


-- ---------------------------------------------------------------------
-- PCM_OS_VEICULO  -- veiculo associado a O.S. (espelha PCOSVEICULO)
-- ---------------------------------------------------------------------
CREATE TABLE PCM_OS_VEICULO (
  CODVEICULO        NUMBER(10)      NOT NULL,                  -- PK propria
  CODCLI            NUMBER(8),                                 -- FK LOGICA -> PCCLIENT.CODCLI (proprietario)
  PLACA             VARCHAR2(10),
  MODELO            VARCHAR2(60),
  MARCA             VARCHAR2(60),
  ANO               NUMBER(4),
  COMBUSTIVEL       VARCHAR2(20),
  MOTOR             VARCHAR2(30),
  COR               VARCHAR2(30),
  CHASSI            VARCHAR2(30),
  KMATUAL           NUMBER(10),
  OBS               VARCHAR2(400),
  DTCADASTRO        DATE            DEFAULT SYSDATE,
  CONSTRAINT PK_PCM_OS_VEICULO PRIMARY KEY (CODVEICULO)
);
CREATE INDEX IDX_PCM_VEICULO_PLACA ON PCM_OS_VEICULO (PLACA);
CREATE INDEX IDX_PCM_VEICULO_CODCLI ON PCM_OS_VEICULO (CODCLI);

CREATE OR REPLACE TRIGGER PCM_OS_VEICULO_BI
BEFORE INSERT ON PCM_OS_VEICULO FOR EACH ROW
BEGIN
  IF :NEW.CODVEICULO IS NULL THEN
    SELECT PCM_OS_VEICULO_SEQ.NEXTVAL INTO :NEW.CODVEICULO FROM DUAL;
  END IF;
END;
/


-- ---------------------------------------------------------------------
-- PCM_OS  -- cabecalho da Ordem de Servico (espelha PCORDEMSERVICO)
-- SITUACAO: 1=Aberta 2=EmExecucao 3=Concluida 4=Faturada 5=Cancelada
-- ---------------------------------------------------------------------
CREATE TABLE PCM_OS (
  NUMOS             NUMBER(10)      NOT NULL,                  -- PK propria
  CODFILIAL         VARCHAR2(2)     NOT NULL,
  CODCLI            NUMBER(8),                                 -- FK LOGICA -> PCCLIENT.CODCLI
  CODRCA            NUMBER(6),                                 -- FK LOGICA -> PCUSUARI/PCRCA (vendedor)
  CODFUNCABERTURA   NUMBER(6),                                 -- FK LOGICA -> PCEMPR.MATRICULA
  CODVEICULO        NUMBER(10),                                -- FK -> PCM_OS_VEICULO
  TIPOOS            VARCHAR2(2),                               -- tipo (ex.: 'B' borracharia, 'M' mecanica)
  SITUACAO          NUMBER(1)       DEFAULT 1 NOT NULL,
  KM                NUMBER(10),
  CODCOB            VARCHAR2(4),                               -- cobranca
  CODPLPAG          NUMBER(6),                                 -- plano de pagamento
  VLTOTALSERVICO    NUMBER(15,2)    DEFAULT 0,
  VLTOTALPRODUTO    NUMBER(15,2)    DEFAULT 0,
  VLDESCONTO        NUMBER(15,2)    DEFAULT 0,
  VLTOTAL           NUMBER(15,2)    DEFAULT 0,
  DTCADASTRO        DATE            DEFAULT SYSDATE,
  DTPREVTERM        DATE,
  DTFECHA           DATE,
  DTCANCEL          DATE,
  MOTIVOCANCEL      VARCHAR2(200),
  NUMTRANSVENDASERV NUMBER(10),                                -- transacao de venda de servico (faturamento)
  NUMTRANSVENDAPROD NUMBER(10),                                -- transacao de venda de produto
  NUMPED            NUMBER(10),
  OBS               VARCHAR2(400),
  USUARIOCAD        VARCHAR2(30),
  CONSTRAINT PK_PCM_OS PRIMARY KEY (NUMOS),
  CONSTRAINT FK_PCM_OS_VEICULO FOREIGN KEY (CODVEICULO) REFERENCES PCM_OS_VEICULO (CODVEICULO),
  CONSTRAINT CK_PCM_OS_SITUACAO CHECK (SITUACAO IN (1,2,3,4,5))
);
CREATE INDEX IDX_PCM_OS_CODCLI ON PCM_OS (CODCLI);
CREATE INDEX IDX_PCM_OS_SITUACAO ON PCM_OS (SITUACAO);
CREATE INDEX IDX_PCM_OS_DTCADASTRO ON PCM_OS (DTCADASTRO);

CREATE OR REPLACE TRIGGER PCM_OS_BI
BEFORE INSERT ON PCM_OS FOR EACH ROW
BEGIN
  IF :NEW.NUMOS IS NULL THEN
    SELECT PCM_OS_SEQ.NEXTVAL INTO :NEW.NUMOS FROM DUAL;
  END IF;
END;
/


-- ---------------------------------------------------------------------
-- PCM_OS_SERVICO  -- itens de SERVICO da O.S. (espelha PCORDEMSERVICOI)
-- Inclui campos QTDE/PERCCOMISSAO/COMISSAO que so existem em versoes
-- novas do Winthor (ausentes no 10g de teste): aqui modelamos completo.
-- ---------------------------------------------------------------------
CREATE TABLE PCM_OS_SERVICO (
  NUMOSSERVICO      NUMBER(10)      NOT NULL,                  -- PK propria
  NUMOS             NUMBER(10)      NOT NULL,
  CODSERVICO        NUMBER(10),                                -- FK -> PCM_SERVICO
  CODPROD           NUMBER(8),                                 -- FK LOGICA -> PCPRODUT.CODPROD (redundancia p/ faturamento)
  CODFUNC           NUMBER(6),                                 -- FK LOGICA -> PCEMPR.MATRICULA (tecnico)
  DESCRICAO         VARCHAR2(100),
  QTDE              NUMBER(15,4)    DEFAULT 1,
  PUNIT             NUMBER(15,4)    DEFAULT 0,
  PRECO             NUMBER(15,2)    DEFAULT 0,                 -- total do item (QTDE * PUNIT - desc)
  VLDESCONTO        NUMBER(15,2)    DEFAULT 0,
  PERCCOMISSAO      NUMBER(7,4)     DEFAULT 0,
  COMISSAO          NUMBER(15,2)    DEFAULT 0,
  RETERISS          VARCHAR2(1)     DEFAULT 'N',
  PERCALIQISSRETIDA NUMBER(7,4)     DEFAULT 0,
  DTINICIO          DATE,
  DTFINAL           DATE,
  TITULOLEVANTAMENTO    VARCHAR2(100),
  DETALHELEVANTAMENTO   VARCHAR2(4000),
  CONSTRAINT PK_PCM_OS_SERVICO PRIMARY KEY (NUMOSSERVICO),
  CONSTRAINT FK_PCM_OSSRV_OS FOREIGN KEY (NUMOS) REFERENCES PCM_OS (NUMOS),
  CONSTRAINT CK_PCM_OSSRV_RETERISS CHECK (RETERISS IN ('S','N'))
);
CREATE INDEX IDX_PCM_OSSRV_NUMOS ON PCM_OS_SERVICO (NUMOS);

CREATE OR REPLACE TRIGGER PCM_OS_SERVICO_BI
BEFORE INSERT ON PCM_OS_SERVICO FOR EACH ROW
BEGIN
  IF :NEW.NUMOSSERVICO IS NULL THEN
    SELECT PCM_OS_SERVICO_SEQ.NEXTVAL INTO :NEW.NUMOSSERVICO FROM DUAL;
  END IF;
END;
/


-- ---------------------------------------------------------------------
-- PCM_OS_PRODUTO  -- pecas/produtos consumidos na O.S.
-- ---------------------------------------------------------------------
CREATE TABLE PCM_OS_PRODUTO (
  NUMOSPRODUTO      NUMBER(10)      NOT NULL,                  -- PK propria
  NUMOS             NUMBER(10)      NOT NULL,
  CODPROD           NUMBER(8)       NOT NULL,                  -- FK LOGICA -> PCPRODUT.CODPROD
  DESCRICAO         VARCHAR2(100),
  QTDE              NUMBER(15,4)    DEFAULT 1,
  PUNIT             NUMBER(15,4)    DEFAULT 0,
  VLDESCONTO        NUMBER(15,2)    DEFAULT 0,
  PRECO             NUMBER(15,2)    DEFAULT 0,                 -- total do item
  BAIXAESTOQUE      VARCHAR2(1)     DEFAULT 'S',               -- S/N controla baixa
  CONSTRAINT PK_PCM_OS_PRODUTO PRIMARY KEY (NUMOSPRODUTO),
  CONSTRAINT FK_PCM_OSPRD_OS FOREIGN KEY (NUMOS) REFERENCES PCM_OS (NUMOS),
  CONSTRAINT CK_PCM_OSPRD_BAIXA CHECK (BAIXAESTOQUE IN ('S','N'))
);
CREATE INDEX IDX_PCM_OSPRD_NUMOS ON PCM_OS_PRODUTO (NUMOS);

CREATE OR REPLACE TRIGGER PCM_OS_PRODUTO_BI
BEFORE INSERT ON PCM_OS_PRODUTO FOR EACH ROW
BEGIN
  IF :NEW.NUMOSPRODUTO IS NULL THEN
    SELECT PCM_OS_PRODUTO_SEQ.NEXTVAL INTO :NEW.NUMOSPRODUTO FROM DUAL;
  END IF;
END;
/


-- ---------------------------------------------------------------------
-- PCM_NFSE  -- controle de emissao de NFS-e por O.S.
-- SITUACAO: 0=Pendente 1=Autorizada 2=Rejeitada 3=Cancelada
-- ---------------------------------------------------------------------
CREATE TABLE PCM_NFSE (
  CODNFSE           NUMBER(10)      NOT NULL,                  -- PK propria
  NUMOS             NUMBER(10)      NOT NULL,
  CODFILIAL         VARCHAR2(2),
  CODMUNICIPIO      VARCHAR2(7),                               -- IBGE do municipio emissor
  NUMRPS            NUMBER(15),                                -- numero do RPS
  SERIERPS          VARCHAR2(5),
  NUMNFSE           VARCHAR2(20),                              -- numero retornado pela prefeitura
  CODVERIFICACAO    VARCHAR2(50),
  SITUACAO          NUMBER(1)       DEFAULT 0 NOT NULL,
  VLSERVICO         NUMBER(15,2)    DEFAULT 0,
  VLISS             NUMBER(15,2)    DEFAULT 0,
  VLDEDUCOES        NUMBER(15,2)    DEFAULT 0,
  DTEMISSAO         DATE,
  DTCANCEL          DATE,
  PROTOCOLO         VARCHAR2(50),
  MSGRETORNO        VARCHAR2(1000),
  XMLENVIO          CLOB,
  XMLRETORNO        CLOB,
  CONSTRAINT PK_PCM_NFSE PRIMARY KEY (CODNFSE),
  CONSTRAINT FK_PCM_NFSE_OS FOREIGN KEY (NUMOS) REFERENCES PCM_OS (NUMOS),
  CONSTRAINT CK_PCM_NFSE_SITUACAO CHECK (SITUACAO IN (0,1,2,3))
);
CREATE INDEX IDX_PCM_NFSE_NUMOS ON PCM_NFSE (NUMOS);

CREATE OR REPLACE TRIGGER PCM_NFSE_BI
BEFORE INSERT ON PCM_NFSE FOR EACH ROW
BEGIN
  IF :NEW.CODNFSE IS NULL THEN
    SELECT PCM_NFSE_SEQ.NEXTVAL INTO :NEW.CODNFSE FROM DUAL;
  END IF;
END;
/

-- ---------------------------------------------------------------------
-- PCM_OS_FATURA  -- faturamento proprio da O.S. (Fase 4; sem tocar nativas)
-- Registra o faturamento e marca a O.S. como Faturada. NAO gera movimento
-- de estoque/financeiro nativo (PCMOV/PCPREST).
-- ---------------------------------------------------------------------
CREATE SEQUENCE PCM_OS_FATURA_SEQ START WITH 1 INCREMENT BY 1 NOCACHE;

CREATE TABLE PCM_OS_FATURA (
  CODFATURA         NUMBER(10)      NOT NULL,                  -- PK propria
  NUMOS             NUMBER(10)      NOT NULL,
  DTFATURA          DATE            DEFAULT SYSDATE,
  VLSERVICO         NUMBER(15,2)    DEFAULT 0,
  VLPRODUTO         NUMBER(15,2)    DEFAULT 0,
  VLDESCONTO        NUMBER(15,2)    DEFAULT 0,
  VLTOTAL           NUMBER(15,2)    DEFAULT 0,
  USUARIO           VARCHAR2(30),
  CONSTRAINT PK_PCM_OS_FATURA PRIMARY KEY (CODFATURA),
  CONSTRAINT FK_PCM_FATURA_OS FOREIGN KEY (NUMOS) REFERENCES PCM_OS (NUMOS),
  CONSTRAINT UN_PCM_FATURA_OS UNIQUE (NUMOS)                   -- uma fatura por O.S. (ja indexa NUMOS)
);

CREATE OR REPLACE TRIGGER PCM_OS_FATURA_BI
BEFORE INSERT ON PCM_OS_FATURA FOR EACH ROW
BEGIN
  IF :NEW.CODFATURA IS NULL THEN
    SELECT PCM_OS_FATURA_SEQ.NEXTVAL INTO :NEW.CODFATURA FROM DUAL;
  END IF;
END;
/

-- =====================================================================
-- FIM DDL PCM_*
-- =====================================================================
