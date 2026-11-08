# Rastreabilidade normativa: requisito → módulo → evidência

Documento de apoio à Hipótese H3 (argumento normativo) e à Tabela 16 do PGT.
Cada linha liga um requisito normativo a um módulo do framework e a uma evidência
verificável (log, laudo ou teste). A coluna **Situação** é deliberadamente
conservadora: *Atendido* só quando há evidência executada; *Parcial* quando há
limitação declarada; *Não atendido* quando é lacuna.

> Os números de artigos e seções abaixo devem ser **conferidos no texto oficial**
> antes da citação final (marcados [CONFERIR] onde há dúvida). Este documento não
> constitui parecer jurídico.

| # | Fonte normativa | Requisito (síntese) | Módulo | Evidência | Situação |
|---|---|---|---|---|---|
| N1 | ISO/IEC 27037:2012 (identificação, coleta, aquisição, preservação) | Aquisição com cópia fiel e verificação de integridade por *hash* | `modulo_coleta` (AWS/Azure/GCP) | `cenario_c3_execucao.json` (SHA-256 e MD5 por evidência); testes de coleta | Atendido |
| N2 | ISO/IEC 27037:2012 — princípios de confiabilidade e repetibilidade | Procedimento documentado e repetível | CLI `./ccf`, README, ambientes LocalStack/Azurite/fake-gcs | `./ccf cenario todos`; logs v2 com *ledger* recriado | Atendido (ambiente simulado, não produção) |
| N3 | ISO/IEC 27037:2012 — documentação da cadeia de custódia | Registro de quem custodiou, quando e por quê | `modulo_blockchain` (chaincode `custody` v2.0) | `cenario_custodia_completa.json` (6/6: registro, transferência, rejeições, devolução, cadeia reconstituída) | Atendido (PoC; 2 orgs em uma máquina) |
| N4 | NIST SP 800-86 — fases coleta, exame, análise, relatório | Fluxo coleta → exame → análise → relatório | `modulo_integracao` (cenários C1–C4, laudo) | Laudos `laudo_c1…c4.pdf` | Atendido |
| N5 | NIST SP 800-86 — preservação da integridade | Detectar alteração posterior da evidência | `VerificarIntegridade` + `teste_adulteracao` | `teste_adulteracao_execucao.json` (byte 706 alterado; hashes divergentes; integridade inválida) | Atendido |
| N6 | CPP arts. 158-A a 158-F (cadeia de custódia) [CONFERIR numeração] | Rastreabilidade de coleta, transporte, recebimento, armazenamento | Coleta + chaincode (registro e transferência) | Mesmas de N1/N3 | Parcial: cobre coleta, transferência e armazenamento lógico; não cobre lacre físico, descarte nem etapas presenciais |
| N7 | LGPD art. 20 (revisão de decisões automatizadas) [CONFERIR redação atual] | Explicação sobre critérios da decisão automatizada e possibilidade de revisão humana | `modulo_ia/xai.py`, `laudo_pericial.py` | Laudo C1 (LIME: escore, estabilidade Jaccard, mapa com SHA-256); laudo C2/C4 (oclusão por mensagem) com ressalva de revisão pericial | Parcial: explicação é do comportamento do modelo, não causal; estabilidade medida em n reduzido |
| N8 | LGPD art. 6º (finalidade, necessidade, segurança) e art. 4º, III (exceção p/ investigação e repressão penal) [CONFERIR] | Minimização e segurança de dados pessoais | Uso de dados sintéticos/proxy; *ledger* guarda apenas *hash* e metadados, não o conteúdo | Chaincode `Evidencia` (campos: id, hash, timestamps, CSP, região, tipo, MSP) | Atendido no desenho; tratamento real exigiria base legal própria |
| N9 | ECA (Lei 8.069/1990) arts. 240 a 241-E, em especial 241-B [CONFERIR] | Não reproduzir, armazenar ou disseminar material ilícito fora de hipóteses legais | Todos os cenários | Imagem sintética e neutra; ramo NSFW **forçado e declarado** (`classificador_forcado: true`); conversas sintéticas; nenhum conteúdo real | Atendido (por construção ética) |
| N10 | Admissibilidade (CPP art. 157; teoria da prova ilícita) [CONFERIR] | Prova obtida e preservada de forma lícita e verificável | Cadeia de custódia + laudo com ressalvas | N3, N5 e laudos | Parcial: validação por perito/juízo está fora do escopo |
| N11 | Explicabilidade como requisito de transparência (LGPD art. 6º, VI) [CONFERIR] | Registro dos critérios usados pelo sistema | Laudos, regras R1–R4 do caso multimodal | `cenario_c4_execucao.json` (regras e indícios) | Atendido |

## Lacunas conhecidas (a declarar no texto)

1. **Tempo**: o *timestamp* do contrato é carimbado na transação, sem autoridade
   de tempo independente (RFC 3161 não implementado).
2. **Identidade**: o agente é a organização (MSP), não a pessoa física do perito.
3. **Escala do ledger**: duas organizações na mesma máquina (PoC).
4. **XAI**: LIME é amostral; a estabilidade (Jaccard) é medida com poucas sementes
   e não valida causalidade. O ramo NSFW do C1 explica o escore real do modelo
   (neutro, ≈ 0,01), não o rótulo forçado.
5. **LGPD**: o tratamento de dados reais de CSAM em investigação possui regime
   próprio; a análise aqui é do desenho do framework.
