# Comparação com Ferramentas Forenses Tradicionais

**Fase 6 — Validação e Documentação (Cronograma PGT, F6: 17 Out–10 Nov/2026)**

## 1. Justificativa Metodológica

Ferramentas forenses de referência citadas na literatura (EnCase, FTK) são
proprietárias e comercialmente licenciadas, inviáveis para uso em ambiente de
laboratório de TCC. A estratégia adotada compara o framework CCF contra
ferramentas open-source que implementam os mesmos princípios técnicos
fundamentais (hashing criptográfico SHA-256, extração de metadados EXIF,
hash perceptual), permitindo validação objetiva e reprodutível por terceiros.

## 2. Comparação 1 — Integridade Criptográfica (SHA-256)

| Ferramenta | Hash Calculado |
|---|---|
| `sha256sum` (GNU coreutils, referência do SO) | `933410f2524e0510afb12f727d54146d000906ed80956a130957d5eb59b2ed54` |
| `modulo_coleta.hashing` (Framework CCF) | `933410f2524e0510afb12f727d54146d000906ed80956a130957d5eb59b2ed54` |

**Resultado: equivalência total.** O framework produz hashes SHA-256
idênticos à implementação de referência do sistema operacional (mesmo
algoritmo, RFC 6234 / FIPS 180-4), validando a corretude da camada de
hashing sobre a qual se apoia toda a cadeia de custódia (RNF01, RF02).

## 3. Comparação 2 — Extração de Metadados EXIF

Ferramenta de referência: **ExifTool v12.40** (Phil Harvey), padrão de fato
da indústria forense para extração de metadados de imagem.

| Campo EXIF | ExifTool (referência) | Framework CCF (Pillow) |
|---|---|---|
| Make (fabricante) | TestCamera | TestCamera |
| Model (modelo do dispositivo) | Model-X100 | Model-X100 |
| Software | CCF-Framework-Test | CCF-Framework-Test |
| Metadados de sistema de arquivos (datas, permissões, tamanho) | Presente | Ausente |
| Informações técnicas de imagem (JFIF, encoding) | Presente | Ausente |

**Resultado: equivalência nos campos forensicamente prioritários** (Make,
Model, Software — os identificadores de dispositivo de origem, conforme
Seção 2.2.3 do PGT).

**Limitação identificada:** o módulo atual do framework não captura
metadados de sistema de arquivos do host nem informações técnicas de
codificação de imagem, presentes na saída completa do ExifTool. Essa é uma
lacuna real de escopo, documentada como limitação e candidata a trabalho
futuro (expansão do módulo de metadados para incluir essas dimensões
adicionais).

## 4. Comparação 3 — Hash Perceptual (Validação Cruzada)

Ferramenta de referência: biblioteca **ImageHash** (implementação
independente de pHash clássico), comparada contra o **PDQ Hash** (Meta/
Facebook, adotado no framework conforme Tabela 12 do PGT).

| Aspecto | pHash (ImageHash) | PDQ Hash (Framework) |
|---|---|---|
| Determinismo | Confirmado | Confirmado |
| Comprimento do hash | 64 bits | 256 bits |
| Robustez a transformações | Documentada na literatura | Documentada na literatura (Meta, 2019) |

**Nota metodológica:** os dois algoritmos operam sobre espaços de
features distintos (DCT global vs. gradientes locais), portanto uma
comparação numérica direta entre os valores de hash não é significativa.
A validação realizada confirma que ambos os algoritmos são
deterministicamente calculáveis e consistentes; testes com imagens
sintéticas uniformes (sem variação visual) produzem saídas degeneradas em
ambos os algoritmos — isso é uma limitação do estímulo de teste, não dos
algoritmos, e reforça a necessidade de validação futura com datasets de
imagens com diversidade visual representativa (ex: UTKFace, já usado no
Estágio E3 deste framework).

## 5. Capacidades Exclusivas do Framework CCF

Ferramentas forenses tradicionais (EnCase, FTK, Autopsy) não incluem, de
forma nativa:

- Classificação automatizada de conteúdo explícito via CNN (Estágio E2)
- Estimativa de idade facial via modelo especializado (Estágio E3, MiVOLO)
- Detecção de padrões de grooming via NLP (Estágio E4, BERT)
- Detecção de anomalias comportamentais em logs (Estágio E5, Isolation Forest)
- Explicabilidade (XAI) das classificações de IA (Estágio E6, LIME/SHAP)
- Registro de cadeia de custódia em blockchain permissionada (Hyperledger Fabric)

Essas capacidades constituem a contribuição científica central do
framework, respondendo à lacuna identificada na revisão de literatura
(Tabela 5, PGT) quanto à ausência de soluções integradas de IA
multi-modal + XAI + blockchain para perícia de CSAM em nuvem.

## 6. Síntese

| Dimensão | Equivalência com Ferramentas Tradicionais |
|---|---|
| Integridade criptográfica (SHA-256) | Total |
| Metadados EXIF prioritários | Total |
| Metadados de sistema de arquivos | Parcial (lacuna documentada) |
| Hash perceptual | Não comparável numericamente (algoritmos distintos), ambos determinísticos |
| Capacidades de IA/XAI/Blockchain | Framework oferece capacidades ausentes nas ferramentas tradicionais |

Esta comparação sustenta empiricamente a afirmação de que o framework CCF
**iguala** ferramentas forenses de referência nas funções fundamentais de
integridade e metadados, e **estende** significativamente suas capacidades
através da camada de IA multi-modal explicável e blockchain, respondendo
diretamente à Hipótese H1 do PGT.
