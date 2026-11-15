# 5 RESULTADOS E DISCUSSÃO

Numeração de tabelas e figuras em continuação ao Capítulo 4 (Tabela 40 era a última; Figura 18 a última). Esta versão incorpora as medições de 15/11/2026 (E1, benchmark, XAI do C1, custódia completa). Figuras 19 (E1), 20 (E5) e 21 (C4) acompanham este arquivo (PNG, 200 dpi). Os itens [CONFERIR] dependem de verificação sua.

---

Este capítulo apresenta e discute os resultados obtidos com o framework implementado no Capítulo 4. A avaliação segue o protocolo de validação da Seção 3.4.3, que organiza a verificação em torno dos objetivos específicos da Seção 1.5.2 e das hipóteses H1, H2 e H3 da Seção 1.3. Como a pesquisa adota a abordagem da Design Science Research (HEVNER et al., 2004), o artefato é avaliado por critérios definidos *a priori*, e os resultados são confrontados com esses critérios mesmo quando não os atendem. Essa postura orienta todo o capítulo: o objetivo não é demonstrar que o framework funciona, e sim delimitar com precisão o que a evidência produzida permite afirmar, o que ela não permite afirmar e o que permanece como lacuna.

O capítulo está organizado em dez seções. A Seção 5.1 descreve as condições de execução e explica os três níveis de evidência usados na leitura dos resultados. As Seções 5.2 a 5.7 apresentam os resultados por componente: coleta e integridade, estágios de inteligência artificial, cenários integrados C1 a C3, caso multimodal C4, cadeia de custódia e teste de adulteração, e laudo pericial. A Seção 5.8 discute os resultados à luz dos objetivos e das hipóteses, a Seção 5.9 trata das ameaças à validade, a Seção 5.10 das limitações e dos trabalhos futuros.

## 5.1 Condições de execução e níveis de evidência

Os resultados dos cenários integrados da rodada final foram obtidos em 15/11/2026, em ambiente local, sobre um ledger Hyperledger Fabric criado em 08/11/2026, com o chaincode `custody` na versão 2.0 e sequência 1, estado verificado pelo comando de status do framework antes de cada rodada. Como o ledger foi preservado entre as duas datas, as evidências registradas em 08/11/2026 constam como `ja_registrada` nos logs de 15/11/2026: o cliente de custódia é idempotente e, se a evidência já existe, apenas compara o hash gravado ao hash coletado. As gravações novas (ação `registrada`) dos cenários de 08/11/2026 estão preservadas no histórico do repositório (commit `0af9771`), e as gravações novas da rodada final são as do cenário de custódia completa e do *benchmark* (Seções 5.2 e 5.6). Os provedores de nuvem foram emulados (LocalStack para a AWS, Azurite para a Azure e fake-gcs-server para o GCP) e a coleta em contêiner foi feita em um contêiner Docker local, em um computador com Windows e subsistema Linux (WSL2), com Python 3.11. Todas as evidências são sintéticas: imagens abstratas geradas por script, conversas inventadas e registros de acesso produzidos por simulação. Nenhum material ilícito real foi utilizado, em conformidade com o escopo negativo da Seção 3.2.2. Os logs completos encontram-se no diretório `modulo_integracao/logs` do repositório do projeto [CONFERIR: citar o commit final ou o apêndice correspondente]. A verificação de corretude do código é feita por testes automatizados em Python e 19 testes do chaincode em Go [CONFERIR: preencher o total de testes Python com a saída de `./ccf testes --go`, que na última rodada completa registrou 170 aprovados antes da inclusão dos testes do experimento E1, do *benchmark* e da explicabilidade da imagem].

A leitura dos resultados exige distinguir três níveis de evidência, porque eles sustentam conclusões de força diferente. O primeiro nível é a *demonstração funcional de integração*: uma execução de ponta a ponta mostra que os componentes se encadeiam e produzem os artefatos esperados (registros, verificações, laudos), mas, por tratar-se de um único caso, nada diz sobre desempenho. O segundo nível é a *métrica de desempenho dos modelos*, obtida em protocolos de validação próprios sobre dados rotulados (corpus PAN12 para o E4, simulações com 30 sementes para o E5), que permite afirmar taxas de erro dentro do domínio dos dados usados. O terceiro nível é o *argumento normativo*, que relaciona o desenho do framework aos requisitos de normas e da legislação, e que não é verificável por execução. A Tabela 41 relaciona cada hipótese ao nível de evidência que a sustenta neste trabalho.

**Tabela 41 – Hipóteses, nível de evidência disponível e seções em que são avaliadas**

| Hipótese | Enunciado resumido | Nível de evidência disponível | Seções |
|----------|--------------------|-------------------------------|--------|
| H1 | Pipeline multimodal com triagem por hash perceptual supera a linha de base de referência em precisão, revocação e F1 | Métricas de modelo sobre dados proxy e sintéticos; execução integrada (C4) | 5.3, 5.5, 5.8 |
| H2 | O chaincode preserva a rastreabilidade e a imutabilidade da sequência de custódia | Demonstração funcional (PoC) em rede Fabric de duas organizações, com transferência de custódia, rejeições e latência medida; testes do contrato | 5.6, 5.8 |
| H3 | O desenho atende aos requisitos normativos e produz justificativas auditáveis para admissibilidade | Argumento normativo (tabela de rastreabilidade); artefatos de explicabilidade e laudo | 5.7, 5.8 |

Fonte: elaborado pela autora (2026), a partir da Seção 1.3.

## 5.2 Coleta forense e integridade (objetivo específico 1)

O módulo de coleta obteve as evidências dos três provedores emulados e do contêiner Docker, calculou o hash SHA-256 no momento da coleta e o manteve associado ao objeto coletado em todas as execuções dos cenários. Em todas as execuções que incluíram verificação, o hash recalculado a partir de uma nova coleta do mesmo objeto foi idêntico ao hash original (Seção 5.6). A corretude da camada de hashing foi verificada por comparação direta com uma implementação independente: para o mesmo arquivo, o módulo do framework e o utilitário `sha256sum` do sistema operacional produziram o mesmo valor (`933410f2…b2ed54`), o que valida a base sobre a qual se apoia a cadeia de custódia. A mesma comparação com o ExifTool mostrou equivalência nos campos de identificação do dispositivo de origem (fabricante, modelo e software) e revelou uma lacuna: o módulo não captura metadados do sistema de arquivos do hospedeiro nem informações técnicas de codificação da imagem, o que está registrado como risco RT09 e como trabalho futuro.

Para medir a integridade em volume, prevista na Tabela 7 como log de 1.000 coletas com taxa de integridade igual ou superior a 99,9%, foi implementado um *benchmark* (comando `./ccf benchmark`). Cada coleta lê um objeto sintético de 1 a 256 KiB, distribuído em rodízio entre os três provedores emulados, cujo SHA-256 é conhecido de antemão por ter sido calculado ao gerar o conteúdo, de forma independente do coletor; a coleta é considerada íntegra se o hash e o tamanho devolvidos pelo coletor forem iguais aos esperados. Falhas e exceções são contadas, e não descartadas. A Tabela 42 apresenta o resultado.

**Tabela 42 – Integridade e latência de 1.000 coletas em provedores emulados**

| Provedor | Coletas | Íntegras | IC de 95% da taxa | Latência mediana | Latência p95 |
|----------|---------|----------|-------------------|------------------|--------------|
| AWS (LocalStack) | 334 | 334 | 98,86% a 100% | 7,6 ms | 11 ms |
| Azure (Azurite) | 333 | 333 | 98,86% a 100% | 3,7 ms | 6,6 ms |
| GCP (fake-gcs-server) | 333 | 333 | 98,86% a 100% | 3,4 ms | 4,4 ms |
| **Total** | **1.000** | **1.000** | **99,62% a 100%** | **3,9 ms** | **8,9 ms** |

Fonte: elaborado pela autora (2026), com dados de `benchmark_framework.json` (execução de 15/11/2026; intervalos de Wilson).

Todas as 1.000 coletas foram íntegras, e a taxa observada de 100% atende o critério de 99,9%. A formulação precisa, porém, ser cuidadosa: com mil observações e nenhuma falha, o limite inferior do intervalo de confiança de 95% é 99,62%, inferior a 99,9%, de modo que o critério é atendido pela taxa observada, mas não é comprovado estatisticamente com esse número de coletas; seriam necessárias cerca de 3.000 coletas sem falha para limitar a taxa de falha a 0,1% com 95% de confiança (regra dos três). As latências, da ordem de milissegundos, refletem o custo de processamento do coletor sobre emuladores executados na mesma máquina, e não a latência de rede de provedores reais, razão pela qual não devem ser extrapoladas. Os testes automatizados do módulo de coleta cobrem praticamente todo o código, mas o que sustenta a afirmação sobre taxa de integridade é o *benchmark*, e não a cobertura. A diferença entre a coleta emulada e a coleta em provedores reais também limita a generalização, pois permissões, limites de requisição, versionamento de objetos e formatos de log dos provedores reais não foram exercitados.

## 5.3 Desempenho dos estágios de inteligência artificial (objetivos específicos 2 e 5; H1)

A Tabela 43 confronta, estágio a estágio, os alvos definidos na Tabela 15 com o que foi efetivamente medido. A coluna de situação distingue três casos: o alvo foi atendido, o alvo não foi atendido e o alvo não foi medido, de modo que a ausência de medida não seja confundida com êxito.

**Tabela 43 – Alvos da Tabela 15 e resultados obtidos por estágio de IA**

| Estágio | Alvo (Tabela 15) | Resultado obtido | Situação |
|---------|------------------|------------------|----------|
| E1 – hash perceptual (PDQ) | Precisão ≥ 0,95; revocação ≥ 0,99; FP < 1% | Corpus sintético (200 referências, 2.000 negativos, 11 transformações leves), limiar de 31 bits: precisão 1,00; FP 0/2.000 (IC de 95% até 0,19%); revocação global 0,76 (1,00 para recompressão, redução, desfoque e brilho; 0,07 e 0,31 para recorte de 5% e marca-d'água) | Precisão e FP atendem; revocação global não atende |
| E2 – conteúdo explícito (OpenNSFW2) | Precisão ≥ 0,90; revocação ≥ 0,85; F1 ≥ 0,87; FP < 5% | Teste qualitativo de gradação: ≈ 0,010 em conteúdo neutro, 0,305 e 0,058 em conteúdo borderline legal, todos abaixo do limiar 0,5 | Não medido |
| E3 – idade facial (MiVOLO) | Precisão ≥ 0,85; revocação ≥ 0,80; F1 ≥ 0,82; FP < 8% | Revocação de 86,51% para a classe menor, em modo zero-shot [CONFERIR: conjunto de dados e número de amostras] | Revocação atende; demais não reportadas |
| E4 – aliciamento (embeddings multilíngues e regressão logística) | Precisão ≥ 0,88; revocação ≥ 0,83; F1 ≥ 0,85; FP < 5% | Média de 3 sementes, negativos difíceis: AUC 0,870; revocação 0,844; FP 28,7% no limiar de F1 máximo; precisão estimada de 2,9% com prevalência de 1% | Revocação atende; precisão, F1 e FP não atendem |
| E5 – anomalias (Isolation Forest) | Precisão ≥ 0,80; revocação ≥ 0,78; F1 ≥ 0,79; FP < 10% | Dados sintéticos, 30 sementes, contaminação 0,1: severidade 1,0 com precisão 0,903, revocação 0,998, F1 0,947, FP 1,1%; severidade 0,10 com precisão 0,630 e F1 0,668 | Atende para anomalias de perfil marcado; não atende para anomalias sutis |

Fonte: elaborado pela autora (2026), com dados de `docs/validacao`, `docs/ADR/008` e `modulo_ia/experimentos/resultados_e5.json`.

Os resultados mostram um quadro heterogêneo, e a heterogeneidade é em si um achado. O E1 foi medido em um experimento próprio (`experimento_e1.py`) sobre um corpus sintético, sem qualquer conteúdo real: 200 imagens de referência, geradas de forma determinística em três famílias (degradê com formas, blocos de baixa frequência e textura), cada uma submetida a onze transformações leves (recompressão JPEG em três níveis, redução em dois níveis, recorte de 5% e 10%, variação de brilho, desfoque leve e marca-d'água), e 2.000 imagens independentes como negativos. Um positivo é acerto se a menor distância de Hamming à base for igual ou inferior ao limiar e apontar para a referência correta; um negativo é falso positivo se algum hash da base estiver dentro do limiar. A Tabela 44 e a Figura 19 apresentam os resultados.

**Tabela 44 – E1 (PDQ): revocação por transformação (200 referências cada) e indicadores globais**

| Transformação | Revocação, 10 bits | Revocação, 16 bits | Revocação, 31 bits |
|---------------|--------------------|--------------------|--------------------|
| JPEG q90 / q70 / q50 | 1,00 / 0,99 / 0,985 | 1,00 / 1,00 / 1,00 | 1,00 / 1,00 / 1,00 |
| Redução a 75% / 50% | 0,995 / 0,915 | 1,00 / 0,99 | 1,00 / 1,00 |
| Desfoque leve | 0,995 | 1,00 | 1,00 |
| Brilho +15% / −15% | 0,725 / 1,00 | 0,89 / 1,00 | 0,995 / 1,00 |
| Recorte de 5% / 10% | 0,00 / 0,00 | 0,00 / 0,00 | 0,07 / 0,00 |
| Marca-d'água no canto | 0,00 | 0,02 | 0,31 |
| **Global (11 transformações, 2.200 positivos)** | **0,69** | **0,72** | **0,76** (IC de 95%: 0,74 a 0,78) |
| Falsos positivos (2.000 negativos) | 0 | 0 | 0 (IC de 95%: 0 a 0,19%) |
| Precisão (corpus 1:1) | 1,00 | 1,00 | 1,00 |

Fonte: elaborado pela autora (2026), com dados de `resultados_e1.json`. O limiar de 31 bits é o sugerido pela documentação do PDQ [CONFERIR: documento da Meta]; o de 10 bits é o padrão do módulo.

![Figura 19](fig19_e1_pdq_transformacoes.png)

*Figura 19 – Revocação do E1 por transformação, nos limiares de 10 e de 31 bits. Fonte: elaborado pela autora (2026), com dados de `resultados_e1.json`.*

Os resultados atendem a dois dos três alvos da Tabela 15 e não atendem o terceiro, e a causa é identificável. A precisão (1,00) e a taxa de falsos positivos (nenhuma ocorrência em 2.000 negativos, com limite superior de 0,19%) atendem os alvos. A revocação global de 0,76 não atende o alvo de 0,99, porque é dominada por duas transformações que o PDQ não tolera quando se compara apenas o hash original: o recorte, mesmo de 5% (revocação 0,07), e a marca-d'água sobreposta (0,31). Para recompressão, redução, desfoque e brilho, a revocação é igual ou superior a 0,995 no limiar de 31 bits. Em um grupo à parte, de transformações no limite declarado, o espelhamento horizontal, a rotação de 90 graus e o recorte de 30% têm revocação nula, e a redução a 25% só é tolerada no limiar de 31 bits (0,985). O achado corrige uma afirmação que constava na documentação do módulo, segundo a qual o hash perceptual seria robusto a recorte, e tem consequência prática: um distribuidor que apenas recorte ou aplique marca-d'água escapa da triagem por hash, o que reforça o papel do E1 como filtro de material conhecido e a necessidade de combiná-lo com os demais estágios. A comparação de variantes diedricas do hash, descrita na literatura do PDQ, mitigaria o espelhamento e a rotação, mas não foi implementada [CONFERIR]. Três ressalvas limitam a leitura. O corpus é sintético e não reproduz a distribuição de imagens reais, de modo que os valores indicam viabilidade e comportamento por transformação, e não desempenho em produção. A qualidade do hash, medida pelo próprio PDQ, ficou abaixo de 50 em 43 das 200 referências e em 459 dos 2.000 negativos, e a recomendação do fornecedor é descartar esses hashes; restringindo a análise às imagens com qualidade igual ou superior a 50, a revocação no limiar de 31 bits é 0,77 e a taxa de falsos positivos permanece nula (0 em 1.541), de modo que a conclusão não muda. Por fim, a similaridade de 0,9922 do caso C4, equivalente a uma distância de 2 bits em 256, é consequência de a base de referência simulada conter o hash do mesmo padrão usado como evidência, e portanto demonstra o mecanismo de correspondência, não a sua robustez.

No E2, por restrição ética, não foi possível avaliar o classificador sobre conteúdo explícito; o teste de gradação com imagens legais mostra que a probabilidade responde de forma proporcional ao grau de exposição, mas nenhuma métrica de erro pode ser derivada dele.

O resultado mais relevante do ponto de vista científico é o do E4, e merece uma análise própria. O primeiro modelo, um BERT ajustado sobre o corpus PAN12, alcançou F1 de 0,8153 no conjunto de teste interno, valor próximo ao do estado da arte da competição (Tabela 15), mas apresentou taxas elevadas de falsos positivos em frases benignas de conversa casual. A investigação (ADR 008) mostrou que o corpus rotula apenas o autor da conversa e não o trecho de aliciamento, de modo que janelas triviais de predadores, como conversas sobre jogos ou escola, contavam como positivas e o modelo aprendeu o estilo textual associado a esses autores, e não o conteúdo de aliciamento. O teste de pares mínimos tornou o problema visível: afirmações inocentes receberam probabilidade 0,06 e perguntas inocentes 0,99, apesar de AUC de 0,94 no próprio corpus. Esse comportamento é um caso do fenômeno de aprendizado por atalhos (*shortcut learning*), descrito de forma geral por Geirhos et al. (2020) [CONFERIR], e mostra que a métrica de teste interno, isoladamente, pode superestimar a utilidade forense de um modelo. O estágio foi então redesenhado, com rotulagem por janela de cinco mensagens usando o *ground truth* do corpus de teste, negativos difíceis (mesmo predador, mesma conversa, janela sem linha anotada), divisão por grupo em três sementes e substituição do ajuste fino por embeddings multilíngues congelados com regressão logística, cuja AUC nos negativos difíceis (0,870) é indistinguível da do BERT (0,886).

O modelo redesenhado é mais honesto, mas não atinge os alvos de precisão e de falsos positivos da Tabela 15. No limiar que maximiza o F1, a revocação de 0,844 satisfaz o alvo de 0,83, porém a taxa de falsos positivos de 28,7% é muito superior ao limite de 5%. A consequência prática é dada pela relação entre prevalência e precisão: com revocação de 0,844, taxa de falsos positivos de 0,287 e prevalência de 1%, a precisão esperada é de 0,844 × 0,01 / (0,844 × 0,01 + 0,287 × 0,99) ≈ 0,029, ou seja, cerca de 97 de cada 100 alertas seriam falsos. Esse cálculo ilustra por que, em problemas de prevalência baixa, a precisão e a curva de precisão-revocação são mais informativas do que a AUC (SAITO; REHMSMEIER, 2015) [CONFERIR]. Por isso o E4 é tratado em todo o framework como triagem sujeita a revisão humana, nunca como evidência isolada, e o F1 de 0,8153 do primeiro modelo não deve ser citado como desempenho do estágio. No conjunto bilíngue de 90 janelas, escrito pela autora, a acurácia foi de 0,859 e a revocação de aliciamento de 0,726, com 26% dos negativos difíceis sinalizados; como esse conjunto foi usado na escolha do modelo, ele não constitui avaliação independente.

O E5 foi avaliado por simulação com 30 sementes, em que treino e teste usam sementes distintas e os rótulos sintéticos só servem para medir o desempenho. A Figura 20 mostra a sensibilidade do estágio à severidade da anomalia e à configuração do parâmetro de contaminação, e permite duas leituras. Primeiro, com a contaminação 0,1, valor adotado nos cenários, o F1 e a taxa de falsos positivos atendem aos alvos da Tabela 15 para anomalias com severidade igual ou superior a 0,25 (F1 de 0,927 a 0,947 e FP de 1,1% a 1,3%) e deixam de atendê-los para a severidade 0,10, em que a anomalia está muito próxima do comportamento normal (F1 de 0,668). Segundo, com a contaminação automática, a precisão cai para a faixa de 0,44 a 0,60 e o F1 permanece abaixo do alvo em todas as severidades, o que mostra que o desempenho depende de uma escolha de configuração que, em um caso real, exigiria conhecer a proporção de anomalias. Como as anomalias e os registros normais foram gerados pelo mesmo processo para treino e teste, os valores são otimistas e valem para o gerador sintético, não para logs reais de provedores.

![Figura 20](fig20_e5_severidade.png)

*Figura 20 – F1-score e taxa de falsos positivos do E5 em função da severidade da anomalia, por configuração de contaminação (média e desvio-padrão de 30 sementes). Fonte: elaborado pela autora (2026), com dados de `resultados_e5.json`.*

A leitura conjunta da Tabela 43 tem uma consequência direta para a hipótese H1, tratada na Seção 5.8: o trabalho não produziu medidas que permitam afirmar desempenho superior a uma linha de base, porque o E2 não foi medido, o E1 não atinge o alvo de revocação, o E4 não atinge os alvos de precisão e falsos positivos e o único estágio que atende a todos os alvos (E5) o faz apenas em dados sintéticos e para anomalias de perfil marcado.

## 5.4 Cenários integrados C1 a C3

Os cenários C1 a C3 da Tabela 16 foram executados ponta a ponta sobre o ledger com o chaincode v2. A Tabela 45 reúne o resultado de cada execução da rodada final (15/11/2026) e o estado da custódia. Em todos os cenários com registro, a ação consta como `ja_registrada`, porque as mesmas evidências haviam sido gravadas na rodada de 08/11/2026 sobre o mesmo ledger (Seção 5.1), e a conferência do hash gravado contra o hash coletado resultou em integridade válida; o comportamento é a idempotência do cliente de custódia, e a gravação nova é demonstrada na Seção 5.6.

**Tabela 45 – Resultado das execuções de C1, C2 e C3 e estado da custódia**

| Cenário | Evidência | Resultado do estágio | Registro de custódia | Integridade na recoleta |
|---------|-----------|----------------------|----------------------|--------------------------|
| C1 (classificação real) | Imagem, AWS | E2: SFW (prob. NSFW 0,0102) | Não (sem sinalização) | Não se aplica |
| C1 (ramo NSFW forçado) | Imagem, AWS | E2 original SFW, forçado para NSFW e declarado no log e no laudo; explicação LIME gerada sobre o escore real (Seção 5.7) | `evid-c1-aws-ee7911c243c8` | Válida |
| C2 (conversa suspeita) | Conversa, Docker | E4: SUSPEITO (escore 0,8687; limiar 0,3997) | `evid-c2-docker-c09be7d97838` | Verificação não incluída no cenário |
| C2 (controle benigno) | Conversa, Docker | E4: NORMAL (escore 0,0504) | Não | Não se aplica |
| C3 | Três objetos: AWS, GCP e Azure | Coleta nos três provedores; estágios de IA não aplicados | Três registros (`evid-c3-aws-…`, `evid-c3-gcp-…`, `evid-c3-azure-…`) | Válida nos três |

Fonte: elaborado pela autora (2026), com dados de `cenario_c1_execucao.json`, `cenario_c1_ramo_nsfw_forcado.json`, `cenario_c2_execucao.json`, `cenario_c2_controle.json` e `cenario_c3_execucao.json`.

O C1 em modo real classificou a imagem sintética como SFW, com probabilidade NSFW de 0,0102, e por isso não acionou a custódia, comportamento esperado para uma imagem abstrata. Para exercitar o ramo que leva ao registro e à explicabilidade, o classificador foi forçado a sinalizar NSFW, e essa substituição consta no log (`classificador_forcado` e `flag_original`) e no laudo. O resultado desse ramo demonstra o encadeamento coleta, classificação, explicação, registro e verificação, e não a capacidade de detecção do classificador. No C2, a conversa sintética de aliciamento obteve escore de 0,8687, acima do limiar de 0,3997 fixado na validação, e foi registrada; a conversa de controle obteve 0,0504 e não foi registrada. O C3 coletou e registrou os três objetos, um por provedor, e produziu laudos por provedor e um laudo consolidado.

A Tabela 46 confronta esses resultados com os critérios de sucesso da Tabela 16, usando as mesmas categorias da Tabela 43. A comparação revela diferenças entre o que a Tabela 16 previa e o que os cenários, como implementados, exercitam.

**Tabela 46 – Critérios de sucesso da Tabela 16 e resultados dos cenários C1, C2 e C3**

| Cenário | Critério de sucesso | Resultado | Situação |
|---------|---------------------|-----------|----------|
| C1 | Precisão ≥ 0,90 na classificação | Execução com uma única imagem; não há mix de objetos nem rotulagem que permita calcular precisão | Não avaliado |
| C1 | Todos os eventos no ledger | Registro da coleta e verificação de integridade no C1; transferência de custódia entre organizações, rejeições e reconstituição da cadeia no cenário de custódia completa (Seção 5.6) | Atendido, com o histórico de transferências exercitado em cenário próprio |
| C1 | Laudo com artefatos XAI | O laudo do C1 traz a explicação LIME da imagem sinalizada (SLIC, logit, 1.000 perturbações, 3 sementes), com estabilidade de Jaccard de 0,73 e mapa de importância com SHA-256; refere-se ao escore real do modelo, não ao rótulo forçado (Seção 5.7) | Atendido parcialmente |
| C2 | F1 ≥ 0,85 na detecção de grooming | Um caso suspeito e um de controle classificados corretamente; F1 do estágio abaixo do alvo (Tabela 43) | Não atendido |
| C2 | Tokens de grooming identificados pelo SHAP | Trechos relevantes identificados por oclusão por mensagem, no lugar do SHAP | Atendido com método diferente |
| C2 | Laudo com hash e blockchain | Hash coletado e registro de custódia no laudo | Atendido |
| C3 | Pipeline de ponta a ponta sem erros | Status de sucesso; três coletas, três registros, três verificações | Atendido |
| C3 | Correlação de evidências de 3 CSPs no mesmo laudo | Laudo consolidado reúne os três provedores; correlação por provedor, sem correlação de conteúdo | Atendido parcialmente |
| C3 | Cadeia de custódia verificável por auditoria | Três verificações de integridade válidas | Atendido |

Fonte: elaborado pela autora (2026), a partir da Tabela 16 e dos logs de execução.

Três diferenças entre a Tabela 16 e a implementação precisam ser declaradas. A primeira é que os critérios de desempenho dos cenários C1 e C2 (precisão e F1) pressupõem uma coleção de objetos ou conversas rotuladas, enquanto os cenários executados processam um único caso; nessas condições, o resultado correto de um caso não é uma estimativa de precisão ou de F1, e o desempenho dos estágios é tratado na Seção 5.3, com os resultados que nela se tem. A segunda é que o estágio de linguagem natural deixou de ser um BERT com SHAP e passou a ser embeddings com regressão logística e explicação por oclusão, em decorrência do redesenho descrito na Seção 5.3, e que a conversa sintética do C2 está em inglês, e não em português como previa a Tabela 16, porque os recursos de validação do modelo, exceto o conjunto bilíngue, estão em inglês. A terceira é que o C3, tal como foi implementado, exercita a coleta multinuvem e a custódia, mas não aplica os estágios de IA, que a Tabela 16 previa; a integração entre coleta, estágios de IA multimodais e custódia é exercitada no cenário C4, descrito a seguir e acrescentado ao protocolo original (Seção 4.7).

## 5.5 Caso multimodal integrado (C4)

O C4 reúne em um único caso sintético uma imagem (AWS), uma conversa (Azure) e registros de acesso (GCP), aplica os estágios E1 a E5 conforme a modalidade e avalia o caso pelas regras R1 a R4 da Seção 4.6. Foram executados um caso suspeito e um caso de controle benigno, este último construído com os mesmos componentes para verificar que as regras não sinalizam todo caso submetido. A Tabela 47 apresenta os resultados e a Figura 21 compara os valores dos estágios que dependem de escore ou de contagem.

![Figura 21](fig21_c4_caso_controle.png)

*Figura 21 – Valores dos estágios E1, E4 e E5 no caso suspeito e no controle benigno do C4; a linha tracejada indica o limiar de decisão do E4. Fonte: elaborado pela autora (2026), com dados dos logs do C4.*

**Tabela 47 – Resultado do C4: caso suspeito e caso de controle**

| Componente | Caso suspeito | Controle benigno |
|------------|---------------|------------------|
| E1, similaridade PDQ (base simulada) | MATCH, 0,9922 (indício forte) | NOMATCH, 0,5078 |
| E2, probabilidade NSFW | SFW, 0,00013 | SFW, 0,00011 |
| E3, idade | Não executado (E2 não sinalizou) | Não executado |
| E4, escore de aliciamento | SUSPEITO, 0,8687 (indício moderado) | NORMAL, 0,0504 |
| E5, registros anômalos | ANOMALO, 2 de 8 (indício contextual) | NORMAL, 0 de 8 |
| Regra aplicada | R1: há ao menos um indício forte | R4: nenhum indício moderado ou forte |
| Prioridade de revisão | ALTA | BAIXA |
| Registros de custódia | 3, todos verificados na recoleta | Nenhum |

Fonte: elaborado pela autora (2026), com dados de `cenario_c4_execucao.json` e `cenario_c4_controle.json`.

No caso suspeito, os três estágios aplicáveis geraram indícios de forças diferentes, a regra R1 atribuiu prioridade ALTA e as três evidências foram registradas e conferidas na recoleta. No controle, nenhum estágio gerou indício, a regra R4 atribuiu prioridade BAIXA, nenhuma evidência foi registrada e o laudo foi emitido declarando a ausência de indícios. A comparação dos dois casos mostra que o encadeamento é sensível ao conteúdo: as mesmas regras produziram saídas opostas para entradas diferentes, e os registros de custódia só foram criados quando houve indício moderado ou forte em pelo menos uma evidência do caso.

A interpretação desses resultados exige cautela por três razões. Primeiro, a regra R1 foi acionada exclusivamente pelo indício forte do E1, que depende de uma base de referência simulada contendo o hash do próprio padrão usado como evidência. Sem esse indício, a prioridade seria igualmente ALTA, mas pela regra R2, que exige indícios em duas modalidades distintas com ao menos um moderado: o E4 (moderado, texto) e o E5 (contextual, logs). Esse desfecho evidencia uma característica da regra R2, que conta um indício contextual, isto é, uma anomalia de acesso que não indica conteúdo ilícito por si só, como modalidade de reforço; trata-se de uma escolha de projeto que deve ser discutida e que não foi validada empiricamente. Segundo, o E2 não sinalizou nenhuma das imagens, como esperado para padrões abstratos, e por isso o E3, que depende da sinalização do E2 e de uma face recortada, não foi executado em nenhum dos casos; esse estágio só foi verificado por testes unitários e pelo teste qualitativo de imagens consentidas. Terceiro, o E5 foi treinado com registros do mesmo processo gerador dos avaliados e testado com oito registros, de modo que a detecção de 2 em 8 não tem valor estatístico.

As regras R1 a R4 foram adotadas em vez de uma combinação numérica de escores porque os escores dos estágios provêm de modelos e conjuntos de dados distintos e não são calibrados entre si, e não há dados multimodais rotulados que permitam ajustar ou avaliar uma fusão aprendida. A consequência assumida é que a prioridade produzida é uma ordenação para revisão pericial, não uma probabilidade, e que a própria regra de decisão não foi validada empiricamente. O laudo emitido reproduz essa ressalva em todos os casos.

## 5.6 Cadeia de custódia e teste de adulteração (objetivo específico 4; H2)

Na rodada de 08/11/2026, sobre o ledger novo, foram gravados nove registros de custódia (um no C1 forçado, um no C2, três no C3, três no C4 e um no teste de adulteração), todos pelo contrato na versão 2.0 e com ação `registrada`. Na rodada final de 15/11/2026, as evidências dos cenários foram novamente coletadas, e o cliente, ao encontrá-las no ledger, conferiu o hash gravado contra o hash coletado sem regravar (ação `ja_registrada`), o que mostra a idempotência do registro. A Tabela 48 resume os registros e as verificações de integridade.

**Tabela 48 – Registros de custódia e verificações de integridade dos cenários**

| Origem | Gravações novas (08/11/2026) | Conferências do hash gravado (15/11/2026) | Verificação na recoleta (15/11/2026) |
|--------|------------------------------|--------------------------------------------|---------------------------------------|
| C1 (ramo forçado) | 1 | 1, hash igual | 1 válida |
| C2 (suspeito) | 1 | 1, hash igual | Não incluída no cenário |
| C3 | 3 | 3, hash igual | 3 válidas |
| C4 (caso suspeito) | 3 | 3, hash igual | 3 válidas |
| Teste de adulteração | 1 | [CONFERIR: log de 15/11/2026] | Ver Tabela 49 |
| **Total** | **9** | **8 (sem o teste de adulteração)** | **7 válidas** |

Fonte: elaborado pela autora (2026), com dados dos logs de execução de 15/11/2026 e do commit `0af9771` (execução de 08/11/2026).

O teste de adulteração consistiu em registrar o hash de uma imagem (`evid-adulteracao-aws-ee7911c243c8`), criar uma cópia com a alteração de um único bit (byte 706, valor 69 para 68) e verificar as duas versões contra o registro. A Tabela 49 apresenta o resultado: a cópia íntegra foi aceita e a cópia adulterada foi rejeitada, com hash recalculado diferente do gravado (`aad0ca97…2532d`, contra `ee7911c2…3a02a20`).

**Tabela 49 – Resultado do teste de adulteração de um bit**

| Versão verificada | Hash recalculado | Integridade |
|-------------------|------------------|-------------|
| Original (controle) | `ee7911c2…3a02a20`, igual ao registrado | Válida |
| Cópia adulterada (byte 706) | `aad0ca97…2532d`, diferente do registrado | Inválida |

Fonte: elaborado pela autora (2026), com dados de `teste_adulteracao_execucao.json`.

A transferência de custódia entre organizações, que na versão anterior deste trabalho só era exercitada por testes unitários, foi executada em rede real pelo cenário de custódia completa (comando `./ccf cenario custodia`). O cenário registra uma evidência nova (`evid-custodia-aws-ee7911c243c8-20261115230106`, com sufixo de instante para garantir um registro novo a cada execução), faz a Org1 transferi-la à Org2, tenta duas operações que o contrato deve rejeitar, devolve a custódia à Org1 e reconstitui a cadeia a partir do ledger. A Tabela 50 apresenta as seis verificações, todas satisfeitas.

**Tabela 50 – Cenário de custódia completa: verificações e resultado (15/11/2026)**

| Verificação | Descrição | Resultado |
|-------------|-----------|-----------|
| V1 | Registro novo: custodiante inicial Org1MSP, histórico vazio | Atendida (ação `registrada`) |
| V2 | Org1 transfere a custódia à Org2 | Atendida (custodiante Org2MSP, 1 transferência) |
| V3 | Org1, já sem a custódia, tenta transferir de novo | Atendida: o contrato rejeita (transferência não autorizada) |
| V4 | Org2 tenta transferir a custódia para si mesma | Atendida: o contrato rejeita (cessionário já é o custodiante) |
| V5 | Org2 devolve a custódia à Org1 | Atendida (custodiante Org1MSP, 2 transferências) |
| V6 | Cadeia reconstituída do ledger | Atendida: 2 eventos encadeados, instantes não decrescentes, hash íntegro |

Fonte: elaborado pela autora (2026), com dados de `cenario_custodia_completa.json`.

Para medir a latência das transações, o *benchmark* registrou 100 evidências sintéticas em sequência no chaincode, consultando o ledger a cada 0,1 s até a confirmação do bloco, de modo que a medida corresponde à latência de ponta a ponta do cliente (consulta prévia, envio da transação e espera pela confirmação). A Tabela 51 apresenta o resultado.

**Tabela 51 – Latência de confirmação de transações no Hyperledger Fabric (100 registros sequenciais)**

| Indicador | Valor |
|-----------|-------|
| Transações confirmadas | 100 de 100 (IC de 95%: 96,3% a 100%) |
| Latência média | 2,17 s |
| Latência mediana (p50) | 2,16 s |
| Latência p95 | 2,26 s |
| Latência máxima | 2,31 s |
| Vazão sequencial | 0,46 transação por segundo |
| Duração total | 217 s |

Fonte: elaborado pela autora (2026), com dados de `benchmark_framework.json` (execução de 15/11/2026).

A latência se concentra em torno de 2,15 s, com dispersão pequena (a diferença entre o p95 e a mediana é de 0,11 s), e as três latências do cenário de custódia completa (2,21 s, 2,15 s e 2,14 s) estão na mesma faixa. Esse comportamento é compatível com uma latência dominada pelo intervalo de formação de bloco do serviço de ordenação (2 s na configuração padrão da rede de teste [CONFERIR: parâmetro `BatchTimeout` do `configtx.yaml`]) e não pelo processamento da transação; a vazão de 0,46 transação por segundo é consequência de o cliente enviar uma transação por vez e esperar a confirmação, e não uma medida da capacidade da rede, que não foi avaliada sob carga concorrente. A taxa de sucesso de 100% em 100 transações tem limite inferior de 96,3%, de modo que a medida descreve o comportamento nominal, não a confiabilidade sob falha.

Além das execuções, o contrato v2 é verificado por 19 testes em Go, que cobrem a rejeição de hash fora do formato (64 caracteres hexadecimais minúsculos), a rejeição de timestamp fora do padrão RFC 3339, o uso do MSP do certificado do chamador como agente coletor, a impossibilidade de sobrescrever um registro existente e a restrição de que somente o custodiante atual transfira a evidência. Essas verificações respondem diretamente ao incidente em que um texto marcador de posição foi gravado no lugar do hash em uma versão anterior (Seção 4.7).

Os resultados sustentam a hipótese H2 em uma extensão específica e delimitada. Estão demonstrados, por execução em rede real de duas organizações, que um registro gravado não pode ser silenciosamente alterado por uma nova gravação com o mesmo identificador, que o hash gravado é comparável ao hash de uma recoleta, que uma alteração de um bit na evidência é detectada, que a custódia só é transferida pelo custodiante atual (as tentativas indevidas foram rejeitadas pelo contrato), e que a cadeia de eventos pode ser reconstituída a partir do ledger, com os eventos encadeados e em ordem temporal não decrescente. A latência de confirmação foi medida (Tabela 51). Permanecem fora do que foi demonstrado quatro propriedades importantes para uso real: o timestamp registrado é o informado pelo cliente da transação e não o de uma autoridade de tempo independente, de modo que a ordem temporal comprovada é a dos eventos no ledger e não a do relógio de um terceiro; a identidade registrada é a da organização (MSP), não a do operador individual; a rede tem duas organizações em máquina única, uma topologia de prova de conceito, sem as propriedades de tolerância a falhas de uma implantação institucional; e o desempenho sob carga concorrente não foi avaliado. O teste de adulteração, por fim, verifica a divergência entre o hash recalculado e o registrado; ele não avalia a adulteração do próprio ledger, que depende das garantias de consenso da rede Fabric e não do código desenvolvido neste trabalho.

## 5.7 Laudo pericial e explicabilidade (objetivo específico 3; H3)

O framework gera laudos em PDF com cinco seções, e a lógica de redação distingue três estados para evitar afirmações sem lastro: evidência classificada como benigna, evidência cuja classificação não foi executada e evidência sinalizada sem artefato de explicação disponível. O laudo nunca afirma o que não ocorreu: no C4, por exemplo, o laudo declara que o E3 não foi executado, que a base de referência do E1 é simulada e que a prioridade resulta de regras heurísticas sem validação empírica. Os laudos têm valor de subsídio à perícia e não possuem assinatura digital, de modo que não substituem o laudo do perito oficial, nos termos do Código de Processo Penal (arts. 158-A a 158-F) [CONFERIR].

Quanto à explicabilidade, o resultado é parcial e se apoia em duas técnicas. Para o E4, o laudo do C2 apresenta os trechos mais relevantes da conversa, identificados por oclusão por mensagem, que mede a queda do escore quando cada mensagem é removida; essa técnica é simples e auditável, mas não equivale aos valores de SHAP previstos na Tabela 16. Para o E2, o laudo do C1 passou a incluir uma explicação por LIME da imagem sinalizada. Como o LIME é amostral, a explicação foi gerada com três sementes, e a estabilidade foi medida pelo índice de Jaccard entre as regiões de alta importância obtidas com sementes diferentes. A configuração do LIME foi escolhida em um experimento de calibração com três imagens sintéticas legais (uma de cor sólida, uma com formas geométricas e um degradê com ruído), três pares de sementes por configuração, comparando a segmentação padrão (*quickshift*) com a segmentação por SLIC de aproximadamente 16 segmentos e a explicação da probabilidade com a explicação do logit da probabilidade, em 500 e 1.000 perturbações. A Tabela 52 apresenta os resultados com 1.000 perturbações.

**Tabela 52 – Estabilidade da explicação LIME (Jaccard médio e desvio-padrão entre 3 pares de sementes; 1.000 perturbações)**

| Configuração | Imagem sólida | Imagem com formas | Degradê com ruído |
|--------------|---------------|-------------------|-------------------|
| *Quickshift*, probabilidade | 0,53 (0,22) | 1,00 (0,00) | 0,55 (0,06) |
| *Quickshift*, logit | 1,00 (0,00) | 0,50 (0,35) | 0,87 (0,18) |
| SLIC, probabilidade | 1,00 (0,00) | 0,68 (0,00) | 0,40 (0,13) |
| **SLIC, logit (adotada)** | **0,86 (0,00)** | **0,74 (0,18)** | **0,55 (0,07)** |

Fonte: elaborado pela autora (2026), com dados de `experimento_xai_estabilidade.json`. Os escores do modelo nas três imagens são inferiores a 0,011.

Nenhuma configuração foi estável em todas as imagens: o menor valor médio por imagem ficou entre 0,50 e 0,55 em todas as configurações com logit, abaixo do patamar de 0,6 que se havia fixado como desejável. O logit melhorou a média em relação à probabilidade, e o aumento de 500 para 1.000 perturbações não melhorou os resultados de forma consistente. Adotou-se a segmentação por SLIC com o logit porque foi a configuração de menor dispersão entre pares de sementes (desvio-padrão de 0,00 a 0,18, contra até 0,35 do *quickshift* com logit); como essa escolha foi feita após observar os resultados, ela deve ser lida como calibração, e não como validação. Com a configuração adotada, a explicação do C1 em ramo forçado obteve índice de Jaccard de 0,73 entre as sementes, com 31,6% da imagem em regiões de alta importância e o mapa de importância gravado em arquivo com o seu SHA-256 (`097420f1…c84b`) registrado no laudo, de modo que o artefato de explicabilidade tem integridade verificável como a própria evidência. Quatro ressalvas limitam o valor probatório desse artefato. Primeiro, a explicação refere-se ao escore real do modelo (0,0102), não ao rótulo NSFW forçado, e o laudo declara essa distinção. Segundo, a imagem do C1 é de cor sólida, caso degenerado para o LIME, pois não há estrutura visual que distinga os segmentos; as regiões destacadas, portanto, não devem ser interpretadas como conteúdo que o modelo considerou, e o resultado demonstra a geração do artefato e a medida de estabilidade, não o raciocínio do modelo sobre conteúdo explícito. Terceiro, todas as imagens de calibração têm escore muito baixo, de modo que a estabilidade para conteúdo efetivamente sinalizado não foi testada, por restrição ética. Quarto, três pares de sementes dão uma estimativa de variância pouco precisa. A investigação do E6 também produziu um achado que limita a confiança nas explicações: a divergência entre LIME e SHAP, documentada no repositório, é coerente com a instabilidade amostral do LIME, descrita na literatura e registrada como risco RT06. Do ponto de vista da admissibilidade, o critério de taxa de erro conhecida, extraído do padrão Daubert e funcionalmente análogo às exigências do laudo pericial, só pode ser atendido com as taxas das Tabelas 43 e 44, e estas valem para dados sintéticos e proxy (CASEY, 2011).

A hipótese H3 é, por natureza, um argumento normativo, e a Tabela 53 o organiza em requisitos, módulos e evidências verificáveis (o detalhamento encontra-se em `docs/validacao/rastreabilidade_normativa.md`). A coluna de situação é deliberadamente conservadora: considera-se atendido apenas o requisito com evidência executada, e parcial o que tem limitação declarada.

**Tabela 53 – Rastreabilidade normativa: requisito, módulo e evidência**

| Fonte normativa | Requisito (síntese) | Módulo e evidência | Situação |
|-----------------|---------------------|--------------------|----------|
| ISO/IEC 27037:2012 | Aquisição com cópia fiel e verificação de integridade por hash | Módulo de coleta; hashes SHA-256 e MD5 em cada coleta; 1.000 coletas íntegras (Tabela 42) | Atendido (emulado) |
| ISO/IEC 27037:2012 | Procedimento documentado e repetível | Comandos `./ccf`, README, ambientes emulados; logs reexecutáveis | Atendido (laboratório) |
| ISO/IEC 27037:2012 | Documentação da cadeia de custódia | Chaincode `custody` v2.0; custódia completa, 6 de 6 verificações (Tabela 50) | Atendido (prova de conceito) |
| NIST SP 800-86 | Fluxo de coleta, exame, análise e relatório | Cenários C1 a C4 e laudos em PDF | Atendido |
| NIST SP 800-86 | Preservação e detecção de alteração da integridade | Teste de adulteração de um bit (Tabela 49) | Atendido |
| CPP, arts. 158-A a 158-F [CONFERIR] | Rastreabilidade de coleta, transporte, recebimento e armazenamento | Coleta e chaincode (registro e transferência) | Parcial: sem lacre físico, descarte nem etapas presenciais |
| LGPD, art. 20 [CONFERIR] | Explicação dos critérios de decisões automatizadas e revisão humana | LIME no laudo do C1 e oclusão no C2, com ressalva de revisão pericial (Tabela 52) | Parcial: explicação não causal, estabilidade moderada |
| LGPD, arts. 4º, III e 6º [CONFERIR] | Minimização e segurança dos dados pessoais | Dados sintéticos; o ledger guarda apenas hash e metadados, não o conteúdo | Atendido no desenho |
| ECA, arts. 240 a 241-E [CONFERIR] | Não reproduzir nem armazenar material ilícito fora das hipóteses legais | Imagens e conversas sintéticas; ramo NSFW forçado e declarado | Atendido por construção |
| CPP, art. 157 [CONFERIR] | Prova obtida e preservada de forma lícita e verificável | Cadeia de custódia e laudo com ressalvas | Parcial: a validação pericial e judicial está fora do escopo |

Fonte: elaborado pela autora (2026), com dados de `docs/validacao/rastreabilidade_normativa.md`. Os dispositivos legais e normativos devem ser conferidos nos textos oficiais antes da citação final.

O desenho do framework incorpora, assim, elementos associados aos princípios de identificação, coleta, aquisição e preservação da ISO/IEC 27037:2012, com hash no momento da coleta, registro imutável da custódia e documentação do procedimento no laudo. Contudo, a avaliação da conformidade normativa não foi realizada por um terceiro, a validação jurídica do procedimento não foi feita, o registro formal junto ao CEP/CONEP permanece como ponto a confirmar (risco RE05) e a explicabilidade é parcial, com estabilidade moderada, como descrito acima. A hipótese permanece, portanto, no estado de argumento fundamentado, e não de demonstração, agora sustentado por evidências executadas para cada requisito técnico da tabela.

## 5.8 Discussão

### 5.8.1 Síntese por objetivo específico

A Tabela 54 sintetiza a situação de cada objetivo específico da Seção 1.5.2 com base nos resultados deste capítulo.

**Tabela 54 – Situação dos objetivos específicos**

| Objetivo | Resultado | Situação |
|----------|-----------|----------|
| 1. Coleta multinuvem com hash no momento da coleta | Coleta em AWS, Azure, GCP (emulados) e Docker; hashing equivalente ao `sha256sum`; 1.000 de 1.000 coletas íntegras (IC de 95%: 99,62% a 100%); integridade válida nas recoletas | Atendido em ambiente emulado; latências não representam nuvens reais |
| 2. Análise multimodal por IA | Estágios E1 a E5 implementados e integrados no C4; E1 medido em corpus sintético | Implementado; desempenho abaixo dos alvos em parte dos estágios (Tabela 43) |
| 3. XAI (LIME e SHAP) transversal | LIME no laudo do C1 com estabilidade medida (Jaccard 0,73) e mapa com hash; oclusão por mensagem no E4; SHAP não utilizado; laudos do C2 e do C4 com trechos relevantes; C3 sem estágios de IA | Parcial |
| 4. Cadeia de custódia em Hyperledger Fabric | Chaincode v2 com validação; registros, verificação, teste de adulteração, transferência entre duas organizações com rejeições e cadeia reconstituída; latência medida (mediana de 2,16 s) | Atendido como prova de conceito |
| 5. Hash perceptual como triagem | PDQ integrado como primeiro estágio no C4; precisão 1,00 e FP nulo em corpus sintético; revocação 0,76, limitada por recorte e marca-d'água | Atendido parcialmente; revocação abaixo do alvo |
| 6. Validação por simulações controladas com comparação a ferramentas de referência | C1 a C4, controle e adulteração; comparação com `sha256sum`, ExifTool e ImageHash | Parcial; a comparação cobre integridade e metadados, não detecção |

Fonte: elaborado pela autora (2026).

### 5.8.2 Avaliação das hipóteses

A Tabela 55 apresenta o veredito sobre cada hipótese. A formulação de H1 pede *superioridade* de precisão, revocação e F1 em relação a uma linha de base de ferramentas forenses de referência, e é esse o ponto em que os resultados não oferecem sustentação.

**Tabela 55 – Veredito sobre as hipóteses**

| Hipótese | Veredito | Justificativa |
|----------|----------|---------------|
| H1 | Não sustentada como formulada | Não houve comparação de desempenho de detecção com ferramentas de referência; o E2 não foi medido, o E1 não atinge o alvo de revocação e o E4 não atinge os alvos de precisão e falsos positivos (Tabela 43) |
| H2 | Sustentada como prova de conceito | Registro, unicidade, verificação, detecção de adulteração, transferência de custódia entre organizações com rejeições indevidas, reconstituição da cadeia e latência demonstrados em rede real; ressalvas: timestamp do cliente, identidade por organização, topologia de uma máquina, sem carga concorrente |
| H3 | Argumentada, não demonstrada | Rastreabilidade normativa com evidências executadas por requisito técnico; explicabilidade parcial, com estabilidade moderada; sem avaliação normativa ou jurídica independente |

Fonte: elaborado pela autora (2026).

A conclusão sobre H1 pode parecer desfavorável, mas é uma conclusão honesta e não invalida a contribuição do trabalho, que está em outro lugar. A comparação formal com ferramentas tradicionais (Seção 5.2) estabelece equivalência nas funções de integridade e de metadados, e mostra que o framework acrescenta capacidades que essas ferramentas não oferecem de forma nativa (classificação automatizada, detecção de anomalias, registro em ledger permissionado); ela não mede qualidade de detecção, e sua leitura como confirmação de H1 não seria defensável diante da banca. Recomenda-se que H1 seja reformulada no Capítulo 1 para o que o trabalho de fato sustenta: a integração de um pipeline multimodal com triagem por hash perceptual e registro imutável de custódia é tecnicamente viável em laboratório e produz triagens com taxas de erro conhecidas e declaradas, e não superioridade sobre uma linha de base. Essa reformulação é coerente com a natureza de Design Science Research do trabalho, em que o artefato é avaliado por sua utilidade e por critérios definidos *a priori*, e preserva a validade científica ao evitar uma alegação que os dados não suportam (HEVNER et al., 2004; WOHLIN et al., 2012).

### 5.8.3 Achados principais

Seis achados sintetizam o que o trabalho acrescenta, além da implementação em si. O primeiro é o caso do E4: um modelo com métrica de teste interno aparentemente adequada (F1 de 0,8153; AUC de 0,94) aprendeu um atalho textual e falhou em pares mínimos, e a correção exigiu mudar a rotulagem e a divisão dos dados, não apenas o modelo. O achado tem valor metodológico para a perícia digital, porque mostra que a taxa de erro exigida por padrões de admissibilidade como o Daubert só é informativa se medida em dados que separam o conteúdo do estilo, e justifica o tratamento do estágio como triagem sujeita a revisão humana. O segundo é a relação entre prevalência e precisão: um estágio com revocação de 0,844 e taxa de falsos positivos de 28,7% produz cerca de 97% de alertas falsos quando a prevalência é de 1%, o que desloca a discussão do desempenho do classificador para o custo da revisão humana e para o limiar escolhido, e indica que, em uso real, o limiar de revocação de 90% (disponível no modelo) e o de F1 máximo representam compromissos diferentes entre omissão e carga de revisão. O terceiro é o resultado do controle do C4: o framework distingue um caso suspeito de um benigno com as mesmas regras e só cria registros de custódia quando há indício, o que é relevante porque um sistema que sinalizasse tudo seria inútil como filtro. O quarto é de natureza forense: o histórico de falhas do cliente de custódia (Seção 4.7) mostra que o ponto mais frágil de uma cadeia de custódia em ledger não é o ledger, e sim a interface entre a coleta e o registro, onde um valor incorreto ou uma confirmação não aguardada pode comprometer a prova. A validação no contrato, a conferência após o registro e a idempotência do cliente respondem a esse risco. O quinto é a limitação do hash perceptual: o PDQ, apresentado como robusto a recorte, tem revocação de 0,07 para um recorte de apenas 5% e de 0,31 para uma marca-d'água no canto, de modo que a triagem por hash perceptual identifica cópias recomprimidas, reduzidas e desfocadas de material conhecido, mas pode ser contornada por transformações simples, e a sua taxa de falsos positivos nula em 2.000 negativos depende de se aceitar essa perda de revocação. O sexto é a sensibilidade da explicabilidade ao objeto explicado: a estabilidade da explicação LIME variou entre 0,40 e 1,00 conforme a imagem e a configuração, e o resultado mais estável ocorreu justamente na imagem sem estrutura, o que mostra que uma métrica de estabilidade isolada pode indicar concordância trivial e deve ser lida junto com o que está sendo explicado.

### 5.8.4 Implicações forenses

Do ponto de vista pericial, o resultado mais útil do framework, nas condições avaliadas, é a preservação verificável da integridade e a organização da triagem para revisão humana, e não a decisão automática. O laudo gerado declara o que foi feito, o que não foi feito e com que limites, o que o aproxima do dever de transparência exigido de um subsídio pericial. Para uso em investigação real, seriam necessários, no mínimo, uma fonte de tempo independente para o timestamp, identidades individuais dos operadores no ledger, assinatura digital do laudo, validação dos estágios de IA em dados representativos do domínio, avaliação do E2 e do E3 em conjuntos adequados sob supervisão ética e jurídica, e o tratamento da cooperação jurídica internacional para a coleta em provedores reais, que está fora do escopo do laboratório (riscos RL02 e RL03).

## 5.9 Ameaças à validade

A principal ameaça à validade externa é o uso exclusivo de dados sintéticos e proxy e de provedores emulados. As latências, as permissões, os formatos de log e a diversidade de conteúdo de ambientes reais não foram representados, e as taxas de erro obtidas valem para os conjuntos usados, não para casos reais. As latências medidas no *benchmark* de coleta, da ordem de milissegundos, são de emuladores na mesma máquina. Em particular, as imagens sintéticas abstratas não exercitam os estágios E2 e E3, a conversa de grooming do C2 foi escrita pela autora e está em inglês, e os registros de acesso são gerados por um processo cujos parâmetros definem a anomalia.

Quanto à validade interna, cada cenário foi executado uma vez por rodada sobre um único caso (o *benchmark* e o experimento do E1 usam, respectivamente, 1.000 coletas e 2.200 positivos com 2.000 negativos), de modo que não há medida de variabilidade entre execuções, embora os valores dos estágios sejam determinísticos para as mesmas entradas e sementes. A base de referência do E1 contém o padrão usado como evidência, o E5 foi treinado e testado com dados do mesmo processo gerador, e o conjunto bilíngue usado na escolha do modelo E4 não é independente da avaliação desse modelo; esses três pontos aproximam os resultados dos casos favoráveis e foram declarados nos laudos e neste capítulo. O hash de um arquivo JPEG sintético depende da versão das bibliotecas de imagem, razão pela qual as comparações entre execuções consideram o comportamento e não o hash byte a byte.

Quanto à validade de construto, a prioridade produzida pelas regras R1 a R4 é uma heurística de ordenação, e a sua interpretação como probabilidade ou como indício de crime seria um erro de construto, razão pela qual o laudo traz a ressalva em todos os casos. Quanto à validade de conclusão, os critérios da Tabela 16 de precisão e F1 foram definidos para coleções de objetos e não para casos únicos, e a análise deste capítulo evitou calcular métricas sobre amostras de tamanho um. Por fim, o ledger foi criado em 08/11/2026 e preservado até a rodada de 15/11/2026, o que garante a coerência dos logs com a versão 2 do chaincode, mas faz com que os cenários da rodada final registrem a ação `ja_registrada`; a gravação nova está demonstrada nos logs de 08/11/2026 (commit `0af9771`), no cenário de custódia completa e no *benchmark*. A configuração do LIME foi escolhida após observar os resultados do experimento de calibração, o que pode inflar a estabilidade aparente em relação a uma escolha prévia.

## 5.10 Limitações e trabalhos futuros

As limitações do trabalho decorrem do escopo de laboratório, e as mais relevantes para quem pretenda reutilizar o framework são as seguintes. O E2 não teve precisão e revocação medidas, por restrição ética, e o E1 foi medido apenas em corpus sintético, com revocação abaixo do alvo para recorte e marca-d'água; o E3 não foi executado em nenhum cenário integrado; o E4 não atinge os alvos de precisão e de falsos positivos e foi avaliado em corpus em inglês, com voluntários adultos, anotação parcial e limiar específico da partição de calibração; o E5 foi avaliado apenas em dados sintéticos. A cadeia de custódia foi avaliada em rede de duas organizações em máquina única, com identidade no nível da organização e timestamp informado pelo cliente, com latência medida em transações sequenciais e sem avaliação de desempenho sob carga concorrente. A explicabilidade está implementada de forma parcial, com oclusão no E4 e LIME no E2, este último presente no laudo do C1 com estabilidade moderada e aplicado a uma imagem sem estrutura, e não é aplicada ao C3, que não executa estágios de IA. Por fim, o laudo não é assinado digitalmente, e a validação jurídica do procedimento e o registro formal em comitê de ética permanecem pendentes.

Esses pontos definem a agenda de trabalhos futuros, em ordem decrescente de impacto sobre a validade do framework: construir conjuntos rotulados e éticos para a medida de precisão e revocação do E3 e para a validação do E1 em imagens reais; validar o E4 em conversas em português e com anotação por trecho; comparar variantes diedricas do PDQ para mitigar o espelhamento e a rotação, e estudar a robustez ao recorte; avaliar a estabilidade do LIME em imagens com estrutura e escores intermediários, sob supervisão ética; medir o desempenho do ledger sob carga concorrente, com mais de duas organizações e em máquinas distintas; incorporar uma fonte de tempo independente e identidades individuais no ledger; e comparar o desempenho de detecção com ferramentas de referência em um protocolo de linha de base definido *a priori*, o que permitiria, enfim, testar a hipótese H1 em sua formulação original.

## 5.11 Síntese do capítulo

Os resultados mostram que os componentes do framework funcionam de forma integrada em ambiente de laboratório: as evidências são coletadas e protegidas por hash (1.000 de 1.000 coletas íntegras), os estágios de IA produzem indícios que as regras ordenam para revisão humana, a cadeia de custódia registra, transfere entre organizações e verifica as evidências no Hyperledger Fabric com latência mediana de 2,16 s, e uma adulteração de um bit é detectada. Eles mostram também, com a mesma clareza, os limites do trabalho: o desempenho de detecção não foi medido no E2, não atinge o alvo de revocação no E1 (que não tolera recorte nem marca-d'água) e não atinge os alvos de precisão e falsos positivos no estágio de aliciamento, a explicabilidade tem estabilidade moderada, os cenários integrados processam casos únicos sintéticos, e parte dos critérios da Tabela 16 não foi atendida ou foi atendida por método diferente do previsto. A hipótese H2 é sustentada como prova de conceito, a H3 como argumento fundamentado com evidências executadas, e a H1 não é sustentada em sua formulação original, de modo que o Capítulo 6 deve apresentar a contribuição do trabalho como a de um framework integrado e verificável de preservação de integridade e triagem assistida, com taxas de erro declaradas, e não como uma ferramenta de detecção comprovadamente superior.

---

## Referências citadas neste capítulo (para conferir e normalizar em ABNT)

- CASEY, E. *Digital Evidence and Computer Crime*. 3. ed. Academic Press, 2011. (já no PGT)
- GEIRHOS, R. et al. Shortcut learning in deep neural networks. *Nature Machine Intelligence*, v. 2, p. 665–673, 2020. [CONFERIR]
- HEVNER, A. R. et al. Design science in information systems research. *MIS Quarterly*, v. 28, n. 1, 2004. (já no PGT)
- SAITO, T.; REHMSMEIER, M. The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. *PLoS ONE*, v. 10, n. 3, 2015. [CONFERIR]
- WOHLIN, C. et al. *Experimentation in Software Engineering*. Springer, 2012. (já no PGT)
- ISO/IEC 27037:2012; NIST SP 800-86; Código de Processo Penal, arts. 158-A a 158-F [CONFERIR]
