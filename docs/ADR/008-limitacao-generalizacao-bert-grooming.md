# ADR 008 — Limitacao de generalizacao do modelo BERT de grooming (E4)

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
