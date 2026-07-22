
## Teste de Gradação — Conteúdo "Borderline" Legal

**Metodologia:** seguindo a mesma lógica da categoria "biquíni" utilizada
por Moreira (2021, Tabela 6.1, dataset AIIA-PID4), testou-se o classificador
OpenNSFW2 com imagens legais de bancos de estoque gratuitos (Unsplash/Pexels)
contendo conteúdo levemente sugestivo (roupas de banho/academia), para
verificar a sensibilidade gradual do modelo, sem uso de conteúdo explícito.

| Categoria | Probabilidade NSFW | Flag |
|---|---|---|
| Conteúdo neutro (fotos de rosto, seção anterior) | ~0,010 | SFW |
| Conteúdo borderline (imagem 1) | 0,305 | SFW |
| Conteúdo borderline (imagem 2) | 0,058 | SFW |

**Observação:** a imagem 1 apresentou probabilidade NSFW aproximadamente
30 vezes maior que o conteúdo neutro, evidenciando que o modelo responde
de forma gradual e proporcional ao grau de exposição visual do conteúdo,
não apenas de forma binária. Nenhuma das imagens ultrapassou o limiar de
decisão (0,5), classificando corretamente ambas como SFW, o que é esperado
dado que se trata de conteúdo legal não-explícito.
