# Matriz de Riscos Técnicos, Legais e Éticos

**Fase 6 — Validação e Documentação (Cronograma PGT, F6: 17 Out–10 Nov/2026)**

## Metodologia

Os riscos técnicos listados nesta matriz não são hipotéticos: foram **efetivamente
encontrados e resolvidos** durante o desenvolvimento do framework, com evidência
registrada em Architecture Decision Records (ADRs) no repositório. Essa abordagem
— documentar riscos reais em vez de apenas antecipados teoricamente — fortalece
a validade empírica desta matriz frente a uma matriz puramente especulativa.

Escala de Probabilidade e Impacto: **Baixo / Médio / Alto**.

---

## 1. Riscos Técnicos

| ID | Risco | Probabilidade | Impacto | Mitigação Adotada | Status |
|---|---|---|---|---|---|
| RT01 | Incompatibilidade entre Docker Desktop (containerd) e Hyperledger Fabric, impedindo instalação de chaincode | Alta (ocorreu) | Alto (bloqueava todo o Módulo de Blockchain) | Desabilitação do containerd (ADR 001) | Mitigado |
| RT02 | Mudança de modelo de licenciamento de dependência externa (LocalStack passou a exigir conta/token) durante o desenvolvimento | Média (ocorreu) | Médio (RNF de "gratuidade" comprometido) | Migração para plano Hobby gratuito; documentação da mudança (ADR 002) | Mitigado |
| RT03 | Descontinuação de API de teste (`shimtest`) do Hyperledger Fabric entre o planejamento e a implementação | Média (ocorreu) | Médio (exigiu reescrita da estratégia de testes do chaincode) | Migração para mocks via `counterfeiter`, alinhado ao padrão oficial atual (ADR 003) | Mitigado |
| RT04 | Incompatibilidade de build de pacotes legados (`pkg_resources`/`setuptools`) com versões recentes do Python | Média (ocorreu) | Médio (bloqueava integração do MiVOLO) | Fixação de `setuptools<81` no ambiente (ADR 006) | Mitigado |
| RT05 | Incompatibilidade binária entre `torch` (build CPU-only) e `torchvision` (build padrão PyPI) | Média (ocorreu) | Médio (erro de operador ausente em runtime) | Instalação de ambas as bibliotecas do mesmo índice (ADR 007) | Mitigado |
| RT06 | Instabilidade amostral do LIME (explicações diferentes em execuções distintas da mesma instância) | Alta (documentada na literatura, Seção 2.3.2 do PGT) | Alto (pode ser arguida como inconsistência metodológica pela defesa em juízo) | Fixação de `random_state`/`random_seed` em todas as chamadas do LIME (identificado e corrigido durante testes automatizados) | Mitigado |
| RT07 | Viés de aprendizado espúrio ("Clever Hans") em modelo de NLP fine-tuned, associando estilo textual de origem do dataset ao rótulo, em vez do conteúdo semântico | Média | Alto (compromete confiabilidade prática além do split de teste interno) | Documentado como limitação (ADR 008); reforça necessidade de revisão humana obrigatória, não decisão automática isolada | Identificado e documentado (não eliminado) |
| RT08 | Nomenclatura imprecisa de fontes de dados na especificação original (OpenNSFW2 referenciado como "dataset", quando é modelo pré-treinado; dataset de treino original nunca foi público) | Média (ocorreu) | Médio (pode ser questionado por banca com conhecimento técnico) | Correção metodológica: uso do modelo pré-treinado diretamente via transfer learning, com nota de esclarecimento | Mitigado |
| RT09 | Lacuna de captura de metadados de sistema de arquivos do host (datas, permissões) em comparação com ferramentas forenses completas (ExifTool) | Alta (identificada em comparação formal) | Baixo-Médio (não compromete integridade, mas reduz completude do laudo) | Documentado como limitação de escopo; candidato a trabalho futuro | Identificado (não mitigado nesta fase) |
| RT10 | Interferência de software de segurança (antivírus/VPN corporativo) em operações de build do Docker | Baixa-Média (ocorreu) | Médio (builds falhando de forma intermitente) | Diagnóstico isolado por testes de build controlados; ajuste de configuração de rede | Mitigado |
| RT11 | Falta de infraestrutura de GPU local para treinamento de modelos profundos | Alta (esperada, antecipada no PGT) | Alto | Uso de Google Colab (gratuito) para treinamento; modelos pré-treinados (MiVOLO, OpenNSFW2) para reduzir necessidade de treino do zero | Mitigado |

## 2. Riscos Legais

| ID | Risco | Probabilidade | Impacto | Mitigação Adotada | Status |
|---|---|---|---|---|---|
| RL01 | Uso do framework como prova pericial sem fundamentação técnica compreensível pelo tribunal ("caixa-preta") | Alta (sem XAI) | Alto (inadmissibilidade da prova) | Integração obrigatória de LIME/SHAP em toda classificação de IA (RF08); rastreabilidade STJ Tema 1.168 | Mitigado por design |
| RL02 | Obtenção de dados de CSPs estrangeiros sem cooperação jurídica adequada (MLAT/CLOUD Act) | Alta (fora do escopo de laboratório, mas relevante para uso real) | Alto (ilegalidade da coleta) | Escopo do projeto restrito a ambiente de laboratório com emuladores (LocalStack/Azurite/GCP), sem acesso a infraestrutura real de produção | Fora do escopo experimental (documentado) |
| RL03 | Perecibilidade de evidências em nuvem durante o prazo médio de resposta do MLAT (6–24 meses) | Alta (risco estrutural do domínio, não do framework em si) | Alto | Arquitetura do framework prioriza hash de integridade no momento da coleta (RF02), preservando prova antes de decisões de retenção do CSP | Mitigado por design (real, fora do escopo de laboratório) |
| RL04 | Violação da LGPD no tratamento de metadados/dados pessoais durante simulações | Baixa (dataset proxy, sem dados reais de terceiros) | Alto se ocorresse | Uso exclusivo de dados sintéticos/proxy; sem coleta de dados pessoais reais | Mitigado |
| RL05 | Armazenamento inadvertido de conteúdo real ilícito durante desenvolvimento | Muito Baixa | Crítico | Uso exclusivo de datasets proxy éticos (OpenNSFW2, UTKFace, PAN12); nenhum componente do framework processa CSAM real em qualquer etapa | Mitigado |

## 3. Riscos Éticos

| ID | Risco | Probabilidade | Impacto | Mitigação Adotada | Status |
|---|---|---|---|---|---|
| RE01 | Trauma vicário/estresse traumático secundário em pesquisadores expostos a temática sensível | Média (risco ocupacional documentado na literatura, Seção 2.6.3 do PGT) | Alto | Mediação tecnológica obrigatória; uso exclusivo de datasets proxy; protocolo de suporte psicológico preventivo (Europol/NCMEC) | Mitigado por design |
| RE02 | Uso de conversas reais de aliciamento (dataset PAN12, origem Perverted Justice) levantando questões de proveniência e consentimento dos dados históricos | Média (identificado durante o desenvolvimento) | Médio | Dataset já é publicamente disponível há mais de uma década, amplamente citado em pesquisa acadêmica revisada por pares; uso restrito a fins de pesquisa, sem republicação de conteúdo | Reconhecido, mitigado por natureza pública/acadêmica consolidada do dataset |
| RE03 | Revitimização de crianças identificadas em evidências (mesmo proxy) por descrição ou reprodução de conteúdo | Baixa (dataset proxy não sensível) | Alto se ocorresse | Anonimização irrestrita; imagens tratadas exclusivamente como objetos de análise técnica; resultados reportados em agregação estatística | Mitigado |
| RE04 | Uso do framework fora do escopo de laboratório sem validação operacional supervisionada | Baixa (fora do controle do desenvolvedor após publicação) | Alto | Escopo explicitamente delimitado como protótipo de laboratório (Seção 1.6, PGT); recomendação explícita de validação operacional adicional antes de uso real | Documentado como limitação/aviso |
| RE05 | Ausência de registro formal em CEP/CONEP antes do início efetivo da pesquisa | A confirmar junto à instituição | Alto (adequação ética formal) | Submissão do protocolo de pesquisa ao sistema CEP/CONEP conforme Resolução CNS 466/2012 | Ação pendente/institucional |

---

## Síntese Quantitativa

| Categoria | Total de Riscos | Mitigados | Identificados/Documentados (não eliminados) | Ação Pendente |
|---|---|---|---|---|
| Técnicos | 11 | 9 | 2 (RT07, RT09) | 0 |
| Legais | 5 | 3 | 2 (RL02, RL03 — estruturais do domínio) | 0 |
| Éticos | 5 | 3 | 1 (RE04) | 1 (RE05) |
| **Total** | **21** | **15** | **5** | **1** |

## Observação Metodológica Final

Um diferencial relevante desta matriz é que **9 dos 11 riscos técnicos foram
efetivamente enfrentados durante o desenvolvimento**, não apenas antecipados
teoricamente — cada um está documentado em Architecture Decision Record (ADR)
no repositório do projeto, com data, diagnóstico e solução aplicada,
proporcionando rastreabilidade completa exigida pela Seção 3.4.4 do PGT.
Os dois riscos técnicos não eliminados (RT07, RT09) são apresentados com
transparência integral, coerente com a exigência de honestidade científica
sobre limitações do estudo.
