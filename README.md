# CCF — Framework de Perícia Digital Multi-Modal para Combate ao CSAM

Framework de perícia digital multi-modal e distribuído que integra Inteligência
Artificial (visão computacional, PLN e detecção de anomalias), Inteligência
Artificial Explicável (XAI/LIME/SHAP) e Blockchain (Hyperledger Fabric) para
detecção, coleta e preservação de evidências de CSAM em ambientes de nuvem.

Trabalho de Conclusão de Curso.
Autora: Lorena Guedes.

## Status do Projeto

Em desenvolvimento — Fase 2 (Implementação), modelo Waterfall.

**Módulos concluídos:**
- ✅ Módulo de Blockchain (Hyperledger Fabric 2.5) — test-network validada
- ✅ Módulo de Coleta Multi-Nuvem — conectores AWS/Azure/GCP, 100% cobertura de testes

**Em desenvolvimento:**
- ⏳ Chaincode de cadeia de custódia (Fabric)
- ⏳ Módulo de IA Multi-Modal
- ⏳ Módulo de XAI (LIME/SHAP)

## Pré-requisitos

- SO: Ubuntu 22.04 LTS (nativo ou via WSL2 no Windows)
- Docker + Docker Compose
- Python 3.11
- Poetry 2.x
- Go 1.22+ (necessário apenas para compilar chaincodes em Go)
- Git

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/lorenaguedess/ccf-framework.git
cd ccf-framework
```

### 2. Instalar dependências Python

```bash
poetry env use python3.11
poetry install
```

### 3. Subir os emuladores multi-cloud (AWS/Azure/GCP)

```bash
docker compose up -d
docker compose ps
```

Deve mostrar 3 serviços com status `Up`:
- `localstack` (porta 4566) — emulador AWS
- `azurite` (portas 10000-10002) — emulador Azure
- `fake-gcs-server` (porta 4443) — emulador GCP

**Nota sobre o LocalStack:** desde março/2026, o LocalStack exige uma conta
gratuita e um token de autenticação, mesmo para recursos community (ex: S3).
Crie uma conta gratuita em https://app.localstack.cloud, gere um token em
Auth Tokens, e configure em um arquivo `.env` na raiz do projeto: LOCALSTACK_AUTH_TOKEN=ls-seu-token-aqui

### 4. Rodar os testes

```bash
poetry run pytest modulo_coleta/tests/ -v
```

Resultado esperado: 21 testes passando.

Para relatório de cobertura:

```bash
poetry run pytest --cov=modulo_coleta --cov-report=term-missing modulo_coleta/tests/
```

Cobertura esperada: 100% no código de produção do módulo de coleta.

### 5. Subir a rede Hyperledger Fabric (test-network)

```bash
cd ~/fabric-dev/fabric-samples/test-network
./network.sh up createChannel -c ccfchannel -ca
```

**Nota de compatibilidade:** se a instalação de chaincode falhar com erro
`broken pipe` durante o build da imagem Docker, desabilite a opção "Use
containerd for pulling and storing images" em Docker Desktop → Settings →
General (ver ADR 001 em `docs/ADR/`).

## Estrutura do Repositório

ccf-framework/
├── docs/ADR/              # Architecture Decision Records
├── modulo_coleta/         # Conectores multi-nuvem + hashing forense
│   ├── aws_collector.py
│   ├── azure_collector.py
│   ├── gcp_collector.py
│   ├── hashing.py
│   └── tests/
├── modulo_blockchain/     # Chaincode de cadeia de custódia (em desenvolvimento)
├── modulo_ia/             # Pipeline de IA multi-modal + XAI (não iniciado)
├── modulo_integracao/     # Cenários de simulação forense (não iniciado)
├── docker-compose.yml     # Emuladores multi-cloud
└── pyproject.toml

## Testes e Qualidade

| Módulo | Testes | Cobertura |
|---|---|---|
| Coleta Multi-Nuvem | 21/21 | 100% (código de produção) |

## Decisões Técnicas Documentadas

Ver `docs/ADR/` para o histórico de decisões arquiteturais e problemas de
compatibilidade resolvidos durante o desenvolvimento (ex: incompatibilidade
Docker containerd/Fabric, mudança de licenciamento do LocalStack).

## Conformidade Ética e Legal

Este projeto opera exclusivamente com datasets proxy éticos e emuladores
locais, sem acesso a material ilícito real ou infraestrutura de produção de
terceiros, em conformidade com as Resoluções CNS nº 466/2012 e nº 510/2016,
o ECA (art. 241-B §2º) e a LGPD.

## Licença

MIT
