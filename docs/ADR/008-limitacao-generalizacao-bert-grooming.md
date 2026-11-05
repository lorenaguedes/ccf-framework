# ADR 008 — Limitacao de generalizacao do classificador de grooming (E4)

Status: **atualizado** (ver secao "Atualizacao" ao final). O texto abaixo
registra o diagnostico original sobre o primeiro modelo (BERT com rotulos
por autor); a decisao de projeto vigente esta na atualizacao.

## Contexto
Apos fine-tuning do BERT sobre o PAN12 (F1=0.8153 no conjunto de teste
interno, ver resultados da secao experimental), testes exploratorios
com frases novas (fora do split de teste original) revelaram uma taxa
alta de falsos positivos: frases claramente benignas em estilo de chat
casual ("i love pizza, whats your favorite food") foram classificadas
como SUSPEITO com score >0.99.

Validacao cruzada Colab/local confirmou que os pesos foram carregados
corretamente (mesmos scores exatos em ambos os ambientes), descartando
erro de integracao - a limitacao e do modelo/dataset.

## Hipotese
O modelo provavelmente aprendeu um atalho espurio (fenomeno "Clever
Hans", ja documentado no Estagio E6/XAI deste projeto): as mensagens
"normais" do PAN12 tem origem em fontes diferentes (IRC, Omegle) das
mensagens de grooming (Perverted Justice), com estilo textual
sistematicamente distinto. O modelo pode ter aprendido a associar
esse estilo de origem, nao o conteudo semantico de aliciamento.

## Decisao
Documentar esta limitacao explicitamente no TCC (Discussao/Limitacoes),
nao ocultar o problema. O F1 de 0.8153 no split de teste interno
permanece valido como metrica sobre a mesma distribuicao de dados do
treino, mas a generalizacao para conversas de dominio diferente
(ex: usuarios reais em portugues, estilos de chat distintos) precisa
de validacao adicional antes de qualquer uso alem do laboratorio.

## Consequencias
- Positivo: achado cientificamente honesto, reforca a necessidade de
  revisao humana e XAI (nunca decisao automatica isolada) - coerente
  com o proprio design do framework.
- Negativo: a confiabilidade pratica do Estagio E4 fica mais limitada
  do que a metrica de teste isolada sugere - deve ser mencionado como
  limitacao relevante do estudo.


## Atualizacao — redesenho do estagio E4 (secao 4.4.4 do PGT)

**Causa confirmada.** O corpus de treinamento do PAN12 rotula apenas o
autor (predador ou nao). Janelas triviais de predadores (jogos, escola)
contavam como aliciamento, e o modelo aprendeu o estilo ("fazer
perguntas ao interlocutor"). Teste de pares mínimos: afirmacoes
inocentes p = 0,06 contra perguntas inocentes p = 0,99, apesar de AUC
de 0,94 no proprio corpus.

**Decisao.**
1. Usar o corpus de teste do PAN12, que traz o *ground truth* do
   Problema 2 (linhas predatorias), para rotular **por janela** de 5
   mensagens, e criar **negativos duros** (mesmo predador, mesma
   conversa, janela sem linha anotada).
2. Dividir treino/validacao/teste **por grupo** (predador e conversa),
   com tres sementes.
3. Substituir o BERT ajustado por **embeddings multilingues congelados**
   (paraphrase-multilingual-mpnet-base-v2) + regressao logistica: AUC
   indistinguivel do BERT nos negativos duros (0,870 contra 0,886),
   treino em segundos e aplicacao a textos em portugues.
4. Descartar a fusao com TF-IDF (reduziu o recall em portugues).
5. Gravar os parametros do modelo em JSON
   (`modulo_ia/models/modelo_e4_embeddings.json`), com limiares da
   validacao; o limiar padrao do codigo e 0,40.

**Resultados (media de 3 sementes).** AUC em negativos duros 0,870;
recall 0,844 e FPR 0,287 no limiar de F1 maximo; no conjunto bilingue
(90 janelas), acuracia 0,859, recall de aliciamento 0,726 e 26% dos
negativos dificeis sinalizados. Precisao estimada de 2,9% com
prevalencia de 1%.

**Consequencias.** O estagio e uma *triagem sujeita a revisao humana*,
nunca evidencia isolada. Persistem: corpus em ingles com voluntarios
adultos; conjunto bilingue pequeno e escrito pela autora (e usado na
escolha do modelo); anotacao do PAN12 parcial; limiar especifico da
particao. O F1 de 0,8153 do primeiro modelo **nao** deve ser citado
como desempenho do estagio.
