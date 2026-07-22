
# CCF — Framework de Perícia Digital Multi-Modal para Combate ao CSAM

Framework de perícia digital multi-modal e distribuído que integra Inteligência
Artificial (visão computacional, PLN e detecção de anomalias), Inteligência
Artificial Explicável (XAI/LIME/SHAP) e Blockchain (Hyperledger Fabric) para
detecção, coleta e preservação de evidências de CSAM em ambientes de nuvem.

Trabalho de Conclusão de Curso.
Autora: Lorena Guedes.

## Status do Projeto

**Todas as fases técnicas do cronograma (F1–F6) concluídas e validadas.**

- ✅ Módulo de Coleta Multi-Nuvem (AWS, Azure, GCP, Docker)
- ✅ Módulo de Blockchain (Hyperledger Fabric — chaincode de custódia)
- ✅ Módulo de IA Multi-Modal (6 estágios: E1–E6)
- ✅ Módulo de Integração (3 cenários RF14, laudo pericial RF12)
- ✅ Fase 6 — Validação (comparação com ferramentas tradicionais, matriz de riscos)

## Arquitetura

ccf-framework/
├── docs/
│   ├── ADR/                  # 8 Architecture Decision Records
│   └── validacao/            # Comparação com ferramentas tradicionais, matriz de riscos, testes qualitativos
├── modulo_coleta/            # Conectores AWS, Azure, GCP, Docker + hashing forense
├── modulo_blockchain/
│   └── chaincode/custody/    # Chaincode Go: registro, transferência, verificação de custódia
├── modulo_ia/
│   ├── perceptual_hash.py       # E1 — Hash Perceptual (PDQ Hash)
│   ├── triagem.py               # E1 — Triagem contra base de hashes conhecidos
│   ├── visao_computacional.py   # E2 — Classificação de conteúdo (OpenNSFW2)
│   ├── estimativa_idade.py      # E3 — Estimativa de idade (MiVOLO)
│   ├── deteccao_grooming.py     # E4 — Detecção de grooming (BERT, PAN12)
│   ├── deteccao_anomalias.py    # E5 — Detecção de anomalias (Isolation Forest)
│   ├── xai.py                   # E6 — Explicabilidade (LIME + score de concordância)
│   └── models/                  # Pesos de modelos fine-tuned (fora do Git, ver .gitignore)
├── modulo_integracao/
│   ├── cenarios_simulacao/      # Orquestradores C1, C2, C3 (RF14) + scripts de execução real
│   ├── laudo_pericial.py        # Gerador de laudo PDF (RF12)
│   └── logs/                    # Logs de execução e laudos gerados
├── docker-compose.yml         # Emuladores multi-cloud (LocalStack, Azurite, fake-gcs-server)
└── pyproject.toml

## Pré-requisitos

- SO: Ubuntu 22.04 LTS (nativo ou via WSL2 no Windows)
- Docker + Docker Compose
- Python 3.11
- Poetry 2.x
- Go 1.22+ (para compilar o chaincode)
- Git

## Instalação

### 1. Clonar o repositório

```
git clone https://github.com/lorenaguedess/ccf-framework.git
cd ccf-framework
```

### 2. Instalar dependências Python

```
poetry env use python3.11
poetry install
```

**Dependências instaladas fora do Poetry** (limitação conhecida, ver ADR 006/007):

```
poetry run pip install "setuptools<81"
poetry run pip install --no-build-isolation "git+https://github.com/WildChlamydia/MiVOLO.git"
poetry run pip install --force-reinstall "torchvision==0.28.0" --index-url https://download.pytorch.org/whl/cpu
```

### 3. Subir os emuladores multi-cloud (AWS/Azure/GCP)

```
docker compose up -d
docker compose ps
```

**Nota sobre o LocalStack:** exige conta gratuita e token de autenticação
(mudança de licenciamento em mar/2026 — ver ADR 002). Configure em `.env`:
```
LOCALSTACK_AUTH_TOKEN=ls-seu-token-aqui
```

### 4. Rodar os testes

```
poetry run pytest --cov --cov-report=term-missing
```

Resultado esperado: 70+ testes passando, ~98% de cobertura de código de produção.

### 5. Subir a rede Hyperledger Fabric e instalar o chaincode

```
cd ~/fabric-dev/fabric-samples/test-network
./network.sh up createChannel -c ccfchannel -ca
./network.sh deployCC -ccn custody -ccp ~/projetos/ccf-framework/modulo_blockchain/chaincode/custody -ccl go -c ccfchannel
```

**Nota de compatibilidade:** se falhar com `broken pipe`, desabilite "Use
containerd for pulling and storing images" em Docker Desktop → Settings →
General (ver ADR 001).

### 6. Executar os cenários de simulação forense (RF14)

```
poetry run python -m modulo_integracao.cenarios_simulacao.executar_c1_real
poetry run python -m modulo_integracao.cenarios_simulacao.executar_c2_real
poetry run python -m modulo_integracao.cenarios_simulacao.executar_c3_real
```

## Testes e Qualidade

| Módulo | Testes | Cobertura |
|---|---|---|
| Coleta Multi-Nuvem (AWS/Azure/GCP/Docker) | 27+ | ~100% |
| Blockchain (chaincode custody) | 9 | — (Go) |
| IA Multi-Modal (E1–E6) | 37 | 98% |
| Integração (C1/C2/C3 + Laudo Pericial) | 16 | — |

## Estágios do Pipeline de IA (Tabela 12, PGT)

| Estágio | Técnica | Status | Resultado-Chave |
|---|---|---|---|
| E1 — Hash Perceptual | PDQ Hash | ✅ | 12 testes, MATCH/NOMATCH funcional |
| E2 — Visão Computacional | OpenNSFW2 (pré-treinado) | ✅ | Validado com conteúdo neutro e borderline |
| E3 — Estimativa de Idade | MiVOLO | ✅ | Recall MENOR: 86,51% (zero-shot, supera fine-tuning próprio) |
| E4 — Detecção de Grooming | BERT (PAN12) | ✅ | F1: 0,8153; limitação de generalização documentada (ADR 008) |
| E5 — Detecção de Anomalias | Isolation Forest | ✅ | 7 testes, detecção de outliers sintéticos validada |
| E6 — XAI Transversal | LIME + score de concordância | ✅ | Divergência LIME/SHAP documentada como achado |

## Decisões Técnicas Documentadas (ADRs)

Ver `docs/ADR/` para o histórico completo:
1. Incompatibilidade Docker containerd/Fabric
2. Mudança de licenciamento do LocalStack
3. Migração shimtest → counterfeiter (testes de chaincode)
4–5. (reservado)
6. Compatibilidade setuptools/MiVOLO
7. Compatibilidade torch/torchvision
8. Limitação de generalização do modelo BERT de grooming

## Validação (Fase 6)

Ver `docs/validacao/` para:
- Comparação formal com ferramentas forenses tradicionais (SHA-256, ExifTool, ImageHash)
- Matriz de riscos técnicos, legais e éticos (21 riscos identificados, 15 mitigados)
- Testes qualitativos do pipeline E2/E3 com imagens reais consentidas

## Conformidade Ética e Legal

Este projeto opera exclusivamente com datasets proxy éticos e emuladores
locais, sem acesso a material ilícito real ou infraestrutura de produção de
terceiros, em conformidade com as Resoluções CNS nº 466/2012 e nº 510/2016,
o ECA (art. 241-B §2º) e a LGPD.

## Licença

MIT

```

Me avisa quando terminar.
