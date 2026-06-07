# Plano Tecnico - Modulo de Servico Winthor (Oficina / Borracharia)

Rotina desktop Python para o ERP TOTVS Winthor: gestao de **Ordens de Servico**
para oficina de auto pecas / borracharia, com cadastro de servicos, execucao,
acompanhamento, faturamento e emissao de **NFS-e** propria.

- Stack: **PyQt6**, **python-oracledb** (dual-mode thin/thick), **SQLAlchemy** (Core),
  **PyInstaller** (.exe 64-bit), chamada pelo menu Winthor via argv.
- Persistencia em **tabelas proprias `PCM_*`** (nunca grava nas nativas).
- Chamada: `app.exe USUARIOWT SENHABD ALIASBD USUARIOBD CODROTINA`.

---

## 1. Visao geral e fluxo

```
Cadastro de Servico ──► Abertura de O.S. ──► Execucao / Acompanhamento ──► Faturamento ──► NFS-e ──► Relatorios
   (PCM_SERVICO)          (PCM_OS +              (atualiza SITUACAO,         (gera trans.    (PCM_NFSE)   (consultas)
    -> PCPRODUT)           PCM_OS_VEICULO)        DTINICIO/DTFINAL)           de venda)
                           itens:
                           PCM_OS_SERVICO
                           PCM_OS_PRODUTO
```

Ciclo de vida da O.S. (campo `SITUACAO`):

| Codigo | Situacao    | Descricao                                              |
|--------|-------------|--------------------------------------------------------|
| 1      | Aberta      | O.S. criada, itens em edicao                           |
| 2      | EmExecucao  | Servicos iniciados (tecnico alocado, DTINICIO)         |
| 3      | Concluida   | Todos os itens finalizados (DTFINAL, DTFECHA)          |
| 4      | Faturada    | Gerou transacao de venda (servico e/ou produto)        |
| 5      | Cancelada   | Cancelada (DTCANCEL + MOTIVOCANCEL)                     |

Fluxo detalhado:

1. **Cadastro de Servico** - registra o servico em `PCM_SERVICO`. Na Opcao A
   (recomendada), aponta para um produto-servico ja cadastrado em `PCPRODUT`
   (criado pela rotina 3501), herdando tributacao de ISS e cadastro fiscal.
2. **Abertura de O.S.** - cria `PCM_OS` (cabecalho) vinculando cliente
   (`PCCLIENT`), vendedor/RCA, veiculo (`PCM_OS_VEICULO`) e filial.
3. **Lancamento de itens** - servicos em `PCM_OS_SERVICO` (com tecnico = `PCEMPR`)
   e pecas em `PCM_OS_PRODUTO` (produtos de `PCPRODUT`).
4. **Execucao / Acompanhamento** - atualiza `SITUACAO`, `DTINICIO`/`DTFINAL`
   por item, comissoes; tela de acompanhamento lista O.S. por situacao.
5. **Faturamento** - calcula totais (servico/produto/desconto/ISS) e gera as
   transacoes de venda (`NUMTRANSVENDASERV` / `NUMTRANSVENDAPROD`).
6. **NFS-e** - emite a nota de servico (certificado A1 .pfx) via `IntegradorNFSe`,
   gravando o controle em `PCM_NFSE`.
7. **Relatorios** - producao por tecnico, faturamento, O.S. por situacao/periodo.

---

## 2. Arvore de diretorios

```
Wint_servico/
├─ app.py                         # entrypoint PyQt6 (logging, excepthook, conexao, licenca, MainWindow)
├─ parametros_winthor.py          # le argv do menu Winthor (fallback env)
├─ requirements.txt
├─ .env.example
├─ .gitignore
├─ build.bat                      # build PyInstaller 64-bit
├─ abrir_app.bat                  # roda em dev (.venv)
├─ PCWNT_9520.spec                # spec PyInstaller (COD_ROTINA generico 9520)
├─ README.md
├─ core/
│  ├─ __init__.py
│  ├─ conexao_oracle.py           # singleton dual-mode thin/thick (SVC_DB_MODE)
│  ├─ db_engine.py                # engine SQLAlchemy sobre a conexao oracledb
│  ├─ licenca_config.py           # whitelist CODCLIPC (gerada)
│  ├─ licenca_repo.py             # validacao de empresa liberada
│  ├─ servico_repo.py             # CRUD PCM_SERVICO (+ lookup PCPRODUT)
│  ├─ ordem_servico_repo.py       # CRUD PCM_OS / PCM_OS_SERVICO / PCM_OS_PRODUTO
│  ├─ veiculo_repo.py             # CRUD PCM_OS_VEICULO
│  ├─ tecnico_repo.py             # consulta PCEMPR (tecnicos)
│  └─ cliente_repo.py             # consulta PCCLIENT
├─ servicos/                      # regras de negocio (sem UI)
│  ├─ __init__.py
│  ├─ numerador_os.py             # geracao de NUMOS via sequence
│  ├─ calculadora_os.py           # totais, ISS, comissoes
│  ├─ validador_os.py             # validacoes de regra
│  ├─ faturador_os.py             # geracao de transacoes de venda
│  └─ integrador_nfse.py          # interface abstrata NFS-e + stub
├─ ui_widgets/
│  ├─ __init__.py
│  ├─ theme.py                    # tema claro/escuro PyQt6
│  ├─ main_window.py              # shell com menu lateral (4 modulos)
│  ├─ tela_cadastro_servico.py
│  ├─ tela_os_lista.py
│  ├─ tela_os_edicao.py
│  ├─ tela_acompanhamento.py
│  └─ tela_relatorios.py
├─ modelos/                       # dataclasses de dominio
│  ├─ __init__.py
│  ├─ servico.py
│  ├─ veiculo.py
│  ├─ ordem_servico.py
│  └─ item_servico.py
├─ scripts/
│  ├─ ddl_pcm.sql                 # DDL das tabelas PCM_*
│  └─ gerar_licenca_config.py     # gera core/licenca_config.py
├─ docs/
│  └─ PLANO_TECNICO.md
├─ logs/        (.gitkeep)
├─ assets/      (.gitkeep)
└─ outputs/     (.gitkeep)
```

---

## 3. Modelo de dados (tabelas PCM_*)

Os DDLs executaveis estao em [`scripts/ddl_pcm.sql`](../scripts/ddl_pcm.sql).
Resumo das tabelas e sequences:

| Tabela          | Papel                                          | PK            | Sequence            |
|-----------------|------------------------------------------------|---------------|---------------------|
| PCM_SERVICO     | catalogo de servicos (-> PCPRODUT)             | CODSERVICO    | PCM_SERVICO_SEQ     |
| PCM_OS_VEICULO  | veiculo da O.S. (espelha PCOSVEICULO)          | CODVEICULO    | PCM_OS_VEICULO_SEQ  |
| PCM_OS          | cabecalho da O.S. (espelha PCORDEMSERVICO)     | NUMOS         | PCM_OS_SEQ          |
| PCM_OS_SERVICO  | itens de servico (espelha PCORDEMSERVICOI)     | NUMOSSERVICO  | PCM_OS_SERVICO_SEQ  |
| PCM_OS_PRODUTO  | pecas/produtos consumidos                      | NUMOSPRODUTO  | PCM_OS_PRODUTO_SEQ  |
| PCM_NFSE        | controle de emissao de NFS-e                   | CODNFSE       | PCM_NFSE_SEQ        |

Notas de compatibilidade Oracle 10g:
- Numeracao por **SEQUENCE + TRIGGER BEFORE INSERT** (sem `IDENTITY` ou
  `DEFAULT seq.NEXTVAL`, recursos de 11g/12c).
- FKs contra tabelas nativas (PCPRODUT, PCCLIENT, PCEMPR) sao **logicas**
  (validadas na aplicacao), nao constraints fisicas - preserva a base nativa.

### 3.1 Decisao de design - PCM_SERVICO (CONFIRMAR COM O USUARIO)

> **Opcao A (RECOMENDADA - adotada nos DDLs).** `PCM_SERVICO.CODPROD` referencia
> `PCPRODUT.CODPROD`. No Winthor, "servico" e um PRODUTO flagueado (cadastrado
> pela rotina 3501 com Departamento/Secao/Fornecedor); o item da O.S. nativa
> (`PCORDEMSERVICOI`) usa `CODPROD -> PCPRODUT`. Reaproveitar esse vinculo
> herda tributacao de ISS, cadastro fiscal e integracao de estoque/faturamento
> ja existentes. **Custo:** depende do servico estar cadastrado como produto.
>
> **Opcao B.** Catalogo `PCM_SERVICO` standalone, sem `CODPROD`. Mais simples
> de cadastrar, mas duplica regras de tributacao e perde a ponte para o
> faturamento/estoque nativo. Nao adotada.

`PCSERVICO` no Winthor e tabela de **licenciamento**, NAO catalogo - nao usar.

### 3.2 Auditoria LGPD

A rotina 3509 grava auditoria de acesso a dados pessoais em
`PCLOGDADOSPESSOAS`. Ao consultar/exibir dados de cliente (`PCCLIENT`) ou
pessoa fisica, preveja insercao de log nessa tabela (campos a confirmar com a
estrutura do banco de cada cliente; tratado em fase posterior).

---

## 4. Mapa de telas e contratos dos repositorios

### Telas (uma por modulo, navegacao por menu lateral na MainWindow)

| Tela                      | Modulo            | Funcao                                                        |
|---------------------------|-------------------|---------------------------------------------------------------|
| `tela_cadastro_servico`   | Cadastro Servico  | CRUD de PCM_SERVICO, lookup de produto-servico em PCPRODUT     |
| `tela_os_lista`           | Ordem de Servico  | listagem/filtro de O.S., abre edicao                          |
| `tela_os_edicao`          | Ordem de Servico  | cabecalho + itens de servico/produto + veiculo                |
| `tela_acompanhamento`     | Acompanhamento    | O.S. por situacao, evolucao da execucao, alocacao de tecnico  |
| `tela_relatorios`         | Relatorios        | producao/tecnico, faturamento, O.S. por periodo               |

### Contratos dos repositorios (assinaturas principais)

```python
# core/servico_repo.py
class ServicoRepo:
    def listar(self, ativo: bool | None = None) -> list[Servico]: ...
    def obter(self, cod_servico: int) -> Servico | None: ...
    def inserir(self, servico: Servico) -> int: ...           # retorna CODSERVICO
    def atualizar(self, servico: Servico) -> None: ...
    def inativar(self, cod_servico: int) -> None: ...
    def buscar_produto_servico(self, termo: str) -> list[dict]: ...  # lookup PCPRODUT

# core/ordem_servico_repo.py
class OrdemServicoRepo:
    def listar(self, *, situacao: int | None = None,
               cod_cli: int | None = None,
               dt_ini: date | None = None, dt_fim: date | None = None) -> list[OrdemServico]: ...
    def obter(self, num_os: int) -> OrdemServico | None: ...
    def inserir(self, os_: OrdemServico) -> int: ...          # retorna NUMOS
    def atualizar(self, os_: OrdemServico) -> None: ...
    def alterar_situacao(self, num_os: int, situacao: int) -> None: ...
    def cancelar(self, num_os: int, motivo: str) -> None: ...
    # itens
    def listar_servicos(self, num_os: int) -> list[ItemServico]: ...
    def salvar_servicos(self, num_os: int, itens: list[ItemServico]) -> None: ...
    def listar_produtos(self, num_os: int) -> list[dict]: ...
    def salvar_produtos(self, num_os: int, itens: list[dict]) -> None: ...

# core/veiculo_repo.py
class VeiculoRepo:
    def listar(self, cod_cli: int | None = None) -> list[Veiculo]: ...
    def obter(self, cod_veiculo: int) -> Veiculo | None: ...
    def buscar_por_placa(self, placa: str) -> Veiculo | None: ...
    def inserir(self, veiculo: Veiculo) -> int: ...
    def atualizar(self, veiculo: Veiculo) -> None: ...

# core/tecnico_repo.py  (consulta PCEMPR; MATRICULA = CODFUNC)
class TecnicoRepo:
    def listar_ativos(self) -> list[dict]: ...
    def obter(self, matricula: int) -> dict | None: ...

# core/cliente_repo.py  (consulta PCCLIENT)
class ClienteRepo:
    def buscar(self, termo: str) -> list[dict]: ...
    def obter(self, cod_cli: int) -> dict | None: ...
```

### Servicos (regras de negocio)

```python
numerador_os.proximo_num_os(engine) -> int            # PCM_OS_SEQ.NEXTVAL
calculadora_os.calcular_totais(os_) -> Totais          # servico/produto/desconto/ISS/total
calculadora_os.calcular_comissao(item, perc) -> Decimal
validador_os.validar(os_) -> list[str]                 # lista de erros (vazia = ok)
faturador_os.faturar(num_os) -> ResultadoFaturamento   # gera NUMTRANSVENDA*
integrador_nfse.IntegradorNFSe.emitir(dados) -> ResultadoNFSe   # interface
```

---

## 5. Estrategia de conexao dual-mode

`core/conexao_oracle.py` (singleton) seleciona o modo via env var
**`SVC_DB_MODE`**:

- **`thin`** (default) - sem Instant Client. Exige servidor **Oracle 12.1+**.
  Indicado para producao moderna.
- **`thick`** - inicializa o Instant Client a partir de
  **`SVC_ORACLE_CLIENT_LIB_DIR`** (`oracledb.init_oracle_client(lib_dir=...)`).
  Obrigatorio para falar com bancos antigos.

Credenciais resolvidas na ordem:
1. menu Winthor (`USUARIOBD`/`SENHABD`/`ALIASBD` via argv);
2. `.env` em dev (`SVC_DB_USER`/`SVC_DB_PWD`/`SVC_DB_DSN`).

### Nota de compatibilidade Instant Client x Oracle 10g (CRITICA)

> O ambiente de **TESTE e Oracle 10g (10.2.0.3.0, 32-bit)**.
> - O modo **thin NAO funciona** com 10g (thin exige servidor 12.1+).
>   Portanto, **no teste o `SVC_DB_MODE` precisa ser `thick`**.
> - Para o thick conversar com 10g, o **Instant Client deve ser 11.2 ou 12.x**.
>   **NAO use 19c** (o 19c removeu suporte a servidores 10g).
> - Como o alvo de empacotamento e **.exe 64-bit**, o Instant Client tambem
>   deve ser **64-bit (Windows x64)**, e `oci.dll` deve estar em
>   `SVC_ORACLE_CLIENT_LIB_DIR`. (Um client 64-bit conversa normalmente com o
>   servidor 10g 32-bit; o que importa e a versao 11.2/12.x, nao 19c.)

`core/db_engine.py` cria um engine **SQLAlchemy** com `creator=` apontando para
o `ConexaoOracle.conn` (reuso da conexao/sessao ja configurada com NLS), usando
o dialect `oracle+oracledb`. Os repos usam SQLAlchemy Core (`text()`).

---

## 6. Subsistema NFS-e

Emissao **propria** com certificado A1 (.pfx). Isolada atras da interface
`servicos/integrador_nfse.py`:

```python
class IntegradorNFSe(abc.ABC):
    @abc.abstractmethod
    def emitir(self, dados: DadosNFSe) -> ResultadoNFSe: ...
    @abc.abstractmethod
    def cancelar(self, codigo: str, motivo: str) -> ResultadoNFSe: ...
    @abc.abstractmethod
    def consultar(self, protocolo: str) -> ResultadoNFSe: ...
```

- **Pontos de extensao:** implementacao concreta por provedor/padrao (PyNFe,
  ABRASF, ou gateway de terceiros). O scaffolding entrega apenas a interface +
  `IntegradorNFSeStub` (levanta `NotImplementedError` / retorna pendente).
- **Persistencia:** `PCM_NFSE` (RPS, numero NFS-e, codigo de verificacao,
  XML de envio/retorno, situacao).
- **O que falta decidir (PENDENTE DO USUARIO):**
  - municipio(s) emissor(es) e padrao da prefeitura (ABRASF 1.0/2.x, ou layout
    proprio - Ginfes, ISSNet, WebISS, etc.);
  - provedor: biblioteca PyNFe vs. gateway pago (Focus NF-e, eNotas, PlugNotas);
  - dados do certificado A1 (caminho do .pfx e senha - via env/secret);
  - regime tributario / aliquota ISS por servico e regras de retencao.

---

## 7. Roadmap por fases

- **Fase 0 - Fundacao (este scaffolding).** App abre offline, estrutura,
  dual-mode, engine SQLAlchemy, telas stub, DDLs. CONFIRMAR Opcao A.
- **Fase 1 - Dados base.** Promover DDL `PCM_*`; implementar `ServicoRepo`,
  `VeiculoRepo`, `ClienteRepo`, `TecnicoRepo`; tela de Cadastro de Servico
  com lookup PCPRODUT.
- **Fase 2 - O.S.** `OrdemServicoRepo`, tela de lista/edicao, itens de servico
  e produto, `numerador_os`, `calculadora_os`, `validador_os`.
- **Fase 3 - Execucao/Acompanhamento.** Situacoes, alocacao de tecnico,
  DTINICIO/DTFINAL, comissoes, tela de acompanhamento.
- **Fase 4 - Faturamento.** `faturador_os` gerando transacoes de venda
  (servico/produto), totais e ISS.
- **Fase 5 - NFS-e.** Implementar `IntegradorNFSe` concreto (apos decisao de
  municipio/provedor), persistencia em `PCM_NFSE`, certificado A1.
- **Fase 6 - Relatorios + LGPD.** Relatorios, exportacoes, log
  `PCLOGDADOSPESSOAS`.
- **Fase 7 - Empacotamento/distribuicao.** Build 64-bit, integracao ao menu
  Winthor, licenciamento por CODCLIPC.

---

### Pendencias que exigem confirmacao do usuario

1. **Opcao A vs. B** para `PCM_SERVICO` (DDLs assumem A).
2. **COD_ROTINA** = `9520` (generico/provisorio em `parametros_winthor.py`, `build.bat` e `.spec`); trocar se houver codigo oficial.
3. **NFS-e:** municipio, padrao/provedor, certificado A1.
4. **Mapeamento de comissao/ISS** por servico (regras tributarias).
5. **Versao/arquitetura do Instant Client** disponivel no ambiente de teste
   (precisa ser 11.2 ou 12.x, 64-bit).
