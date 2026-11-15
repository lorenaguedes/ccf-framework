# Texto para o PGT: seções 4.7, 4.8 e Capítulo 5

Numeração de tabelas e figuras segue a continuação do 4.6 (última: Tabela 39, Figura 18). Itens marcados [CONFERIR] dependem de verificação sua no documento ou na literatura.

---

## 4.7 Desvios em relação ao planejado

A implementação divergiu do planejamento em cinco pontos, todos identificados durante a execução dos cenários e tratados antes da coleta dos resultados finais. A Tabela 40 os resume, e os parágrafos seguintes detalham o motivo e a correção de cada um.

**Tabela 40 – Desvios identificados na implementação e seu tratamento**

| Nº | Desvio | Impacto potencial | Tratamento |
|----|--------|-------------------|------------|
| D1 | Cenário C4 (caso multimodal) não consta na Tabela 16 | Escopo acima do previsto | Incluído como demonstração de integração, não como validação |
| D2 | Cliente de custódia não reconhecia erro do peer com caracteres escapados em octal e consultava o ledger antes da confirmação do bloco | Falsos negativos de registro | Decodificação dos escapes e consulta com tentativas até a confirmação |
| D3 | Chaincode v1 aceitava hash e timestamp sem validação (incidente com o texto marcador de posição no lugar do hash) | Registro de valor inválido no ledger | Chaincode v2 com validação no contrato |
| D4 | Registros de C1 e C3 reaproveitados de execuções anteriores à v2 | Log não demonstrava as garantias da v2 | Ledger recriado em 08/11/2026 e todos os cenários reexecutados |
| D5 | C3 abortava na falha de um provedor e não gerava laudo único | Critério de laudo único não atendido | Sucesso parcial por provedor e laudo consolidado |

O primeiro desvio (D1) decorre de uma limitação do desenho original: os cenários C1 a C3 exercitam uma modalidade de evidência por vez, o que não demonstra a integração multimodal que dá nome ao framework. Optou-se por acrescentar o cenário C4, que reúne imagem, conversa e registros de acesso em um único caso sintético e os avalia por regras explícitas. Como o C4 não consta na Tabela 16, seus resultados não são comparados aos critérios de sucesso ali definidos e são apresentados no Capítulo 5 apenas como demonstração do funcionamento conjunto dos componentes.

O segundo desvio (D2) reuniu dois defeitos do cliente Python de custódia. O primeiro é que o peer exibe a mensagem de erro do chaincode com os bytes não ASCII escapados em octal, de modo que a expressão "não encontrada" não era reconhecida e uma evidência ainda não registrada era tratada como falha. O segundo é que a invocação retorna quando o serviço de ordenação aceita a transação, antes de o bloco ser confirmado pelo peer, e a consulta imediata não encontrava o registro recém-gravado. Corrigiu-se o primeiro com a decodificação dos escapes antes da comparação e o segundo com consultas repetidas, em intervalos fixos, até a confirmação ou o esgotamento do prazo. Ambas as correções têm testes unitários com executor injetado.

O terceiro desvio (D3) foi revelado por uma execução manual em que um texto marcador de posição foi gravado no lugar do hash, pois a versão inicial do chaincode não validava o argumento. A versão 2 passou a exigir hash SHA-256 com 64 caracteres hexadecimais minúsculos e timestamp em RFC 3339, a usar o identificador do MSP do certificado do chamador como agente coletor e a registrar o instante da transação como `registrado_em`. Essas verificações são cobertas pelos testes do contrato em Go. Permanece uma limitação: o timestamp informado pelo cliente é assinado pelo próprio cliente e não constitui autoridade independente de tempo, e a identidade registrada é a da organização, não a do operador individual.

O quarto desvio (D4) é de procedimento. Após a atualização para a v2, os registros dos cenários C1 e C3 já existiam no ledger, gravados pela versão anterior, e foram reportados como `ja_registrada`, o que demonstrava apenas a idempotência do cliente e não as garantias do novo contrato. Para que todos os logs refletissem uma única configuração, a rede foi recriada em 08/11/2026 (o ledger anterior havia sido recriado em 05/11/2026), o chaincode v2 foi implantado com sequência 1 e todos os cenários foram reexecutados. Durante essa recriação identificou-se ainda um defeito na interface de linha de comando do framework, que fixava a sequência do chaincode em 2 e, portanto, falhava em rede nova; a sequência passou a ser calculada a partir do estado da rede.

O quinto desvio (D5) refere-se ao C3. Na versão inicial, a falha de custódia em um dos provedores interrompia o cenário, e o critério de produzir um único laudo para os três provedores não era atendido. O cenário passou a registrar o erro por provedor, a concluir com status de sucesso parcial quando apenas parte dos provedores falha e a gerar, além dos laudos por provedor, um laudo consolidado.

---

## 4.8 Síntese do capítulo

Este capítulo descreveu a implementação do framework em quatro módulos integrados: coleta forense nos três provedores de nuvem emulados, estágios de inteligência artificial (E1 a E5), cadeia de custódia em Hyperledger Fabric e integração com emissão de laudo pericial. A verificação de corretude do código é feita por 170 testes automatizados em Python e 19 testes do chaincode em Go, todos aprovados na última execução. Os desvios registrados na Seção 4.7 foram corrigidos antes da coleta dos resultados. O capítulo seguinte apresenta os resultados das execuções dos cenários C1 a C4, do caso de controle e do teste de adulteração, e discute o que eles permitem e o que não permitem concluir.

---

# Capítulo 5 – Resultados e Discussão

## 5.1 Condições de execução

Todas as execuções analisadas neste capítulo foram realizadas em 08/11/2026, em ambiente local, sobre um ledger Hyperledger Fabric recém-criado e com o chaincode `custody` na versão 2.0 (sequência 1), conforme o estado verificado pelo comando de status do framework antes de cada rodada. Os provedores de nuvem foram emulados (LocalStack, Azurite e fake-gcs-server) e todas as evidências são sintéticas: imagens abstratas geradas por script, conversas inventadas e registros de acesso produzidos por simulação. Nenhum material real foi utilizado. Os logs completos de cada execução encontram-se no repositório do projeto, no diretório `modulo_integracao/logs` [CONFERIR: citar o apêndice ou o commit `0af9771`].

## 5.2 Resultados por cenário

A Tabela 41 reúne o resultado de cada cenário e o estado da custódia. Em todos os cenários com registro, a ação foi `registrada` (gravação nova pela v2) e a conferência do hash gravado contra o hash recalculado a partir da evidência recoletada resultou em integridade válida.

**Tabela 41 – Resultado das execuções e registros de custódia por cenário**

| Cenário | Evidência | Resultado do estágio | Registro de custódia | Integridade na recoleta |
|---------|-----------|----------------------|----------------------|--------------------------|
| C1 (classificação real) | Imagem, AWS | E2: SFW (prob. NSFW 0,0102) | Não (sem sinalização) | Não aplicável |
| C1 (ramo NSFW forçado) | Imagem, AWS | E2 original SFW, forçado para NSFW e declarado no log | `evid-c1-aws-ee7911c243c8` | Válida |
| C2 (suspeito) | Conversa, Docker | E4: SUSPEITO (escore 0,8687) | `evid-c2-docker-c09be7d97838` | Não executada no cenário |
| C2 (controle) | Conversa, Docker | E4: NORMAL (escore 0,0504) | Não | Não aplicável |
| C3 | Três objetos, AWS, GCP e Azure | Coleta nos três provedores | Três registros (`evid-c3-aws-…`, `evid-c3-gcp-…`, `evid-c3-azure-…`) | Válida nos três |

O C1 em modo real classificou a imagem sintética como SFW com probabilidade NSFW de 0,0102 e, por isso, não acionou a custódia, o que é o comportamento esperado para uma imagem abstrata. Para exercitar o ramo que leva à custódia, o classificador foi forçado a sinalizar NSFW, e essa substituição consta no próprio log (`classificador_forcado` e `flag_original`) e no laudo, de modo que o resultado demonstra o encadeamento coleta, classificação, registro e verificação, e não a capacidade de detecção do classificador.

No C2, a conversa sintética de aliciamento foi classificada como SUSPEITO com escore de 0,8687, com os trechos mais relevantes identificados pelo estágio, e registrada na custódia; a conversa de controle recebeu escore de 0,0504 e foi classificada como NORMAL, sem registro. No C3, os três provedores foram coletados, os três hashes foram registrados e os três foram verificados com sucesso, e o cenário produziu os laudos individuais e o laudo consolidado.

### 5.2.1 Caso multimodal (C4) e caso de controle

A Tabela 42 compara o caso multimodal com o caso de controle benigno, ambos avaliados pelas regras R1 a R4 da Seção 4.6.

**Tabela 42 – Resultado do C4: caso multimodal e caso de controle**

| Componente | Caso (suspeito) | Controle (benigno) |
|------------|-----------------|--------------------|
| E1, hash perceptual (base simulada) | MATCH, similaridade 0,9922 (indício forte) | NOMATCH, similaridade 0,5078 |
| E2, conteúdo explícito | SFW, prob. 0,00013 | SFW, prob. 0,00011 |
| E3, estimativa de idade | Não executado (E2 não sinalizou) | Não executado |
| E4, aliciamento | SUSPEITO, escore 0,8687 (indício moderado) | NORMAL, escore 0,0504 |
| E5, anomalias de acesso | ANOMALO, 2 de 8 registros (indício contextual) | NORMAL, 0 de 8 registros |
| Regra aplicada | R1 (há indício forte) | R4 (nenhum indício moderado ou forte) |
| Prioridade de revisão | ALTA | BAIXA |
| Registros de custódia | 3, todos verificados | Nenhum |

No caso suspeito, os três estágios aplicáveis geraram indícios de forças distintas e a regra R1 atribuiu prioridade ALTA, com os três registros de custódia gravados e conferidos na recoleta. No caso de controle, nenhum estágio gerou indício, a regra R4 atribuiu prioridade BAIXA e nenhuma evidência foi registrada, o que mostra que as regras não sinalizam todo caso submetido. Em ambos, o laudo foi emitido e declara os limites do caso, entre eles o fato de o E3 não ter sido executado.

## 5.3 Teste de adulteração

O teste negativo registrou o hash de uma imagem no ledger (`evid-adulteracao-aws-ee7911c243c8`), criou uma cópia com a alteração de um único byte e verificou ambas as versões contra o registro. A Tabela 43 apresenta o resultado.

**Tabela 43 – Resultado do teste de adulteração de um byte**

| Versão verificada | Hash recalculado | Integridade |
|-------------------|------------------|-------------|
| Original (controle) | `ee7911c2…3a02a20`, igual ao registrado | Válida |
| Cópia adulterada (byte 706, valor 69 para 68) | `aad0ca97…2532d`, diferente do registrado | Inválida |

A cópia íntegra foi aceita e a cópia com a alteração de um bit foi rejeitada, de modo que o mecanismo distinguiu as duas situações no teste realizado. O resultado confirma o que se espera de uma função hash criptográfica combinada a um registro imutável, mas não avalia outras formas de adulteração, como a substituição do próprio registro, que depende das garantias de consenso da rede.

## 5.4 Discussão

Os resultados mostram que os componentes funcionam de forma integrada e que a cadeia de custódia detecta alteração de conteúdo após o registro, o que sustenta o objetivo de preservar a integridade da evidência. Eles não mostram, e este trabalho não afirma, que o framework detecte com qualidade material ilícito real: os estágios de IA operaram sobre dados sintéticos, e os desempenhos mensurados (métricas de precisão, revocação e taxa de falsos positivos) pertencem à validação dos modelos, apresentada separadamente [CONFERIR: indicar a seção de avaliação dos modelos].

Três características dos resultados exigem leitura cautelosa. A primeira é que a correspondência do E1 (similaridade 0,9922) decorre de a base de referência simulada conter o hash do mesmo padrão sintético usado como evidência, e a prioridade ALTA do caso suspeito resulta exclusivamente desse indício forte (regra R1). Trata-se, portanto, de uma demonstração do mecanismo, e não de uma medida de detecção. A segunda é que o E5 foi treinado com registros do mesmo processo gerador dos avaliados, o que torna o resultado otimista. A terceira é que o ramo NSFW do C1 só foi exercitado com o classificador forçado, pois as imagens sintéticas abstratas não o sinalizam; o E3, que depende dessa sinalização e de uma face recortada, não foi executado em nenhum cenário, e sua verificação permanece restrita aos testes unitários.

As regras R1 a R4 foram adotadas em vez de uma combinação numérica de escores porque os escores dos estágios não são calibrados entre si e não há dados multimodais rotulados que permitam calibrá-los. A consequência é que a prioridade produzida é uma ordenação para revisão pericial, sem validação empírica, e não uma probabilidade nem uma conclusão sobre a prática de crime. O laudo gerado é um subsídio à perícia e não possui assinatura digital, não substituindo o laudo do perito oficial (arts. 158-A a 158-F do Código de Processo Penal [CONFERIR]).

Do ponto de vista da admissibilidade da prova, o registro em ledger com validação do hash e do timestamp contribui para demonstrar a integridade e a ordem dos eventos, mas o instante registrado é o informado pelo cliente da transação e a identidade é a da organização. Para uso real, seriam necessários uma fonte de tempo independente e identidades individuais dos operadores, além da validação jurídica do procedimento [CONFERIR: referências sobre cadeia de custódia e provas digitais].

## 5.5 Ameaças à validade

A principal ameaça à validade externa é o uso exclusivo de dados sintéticos e de provedores emulados: as latências, as permissões, os formatos de log e a diversidade de conteúdo de ambientes reais não foram representados, e os resultados não devem ser extrapolados para eles. Quanto à validade interna, cada cenário foi executado uma vez sobre um único caso, de modo que não há medida de variabilidade, e o hash do arquivo JPEG sintético depende da versão das bibliotecas de imagem, razão pela qual a comparação entre execuções considera o comportamento e não o hash byte a byte. Por fim, o ledger foi recriado antes das execuções finais, o que garante a coerência dos logs com a versão 2 do chaincode, mas impede a comparação com os registros produzidos pela versão anterior.
