# ADR 002 — Mudança de licenciamento do LocalStack

## Contexto
A partir de 23/03/2026, a imagem localstack/localstack:latest unificou as
versões Community e Pro, passando a exigir LOCALSTACK_AUTH_TOKEN mesmo para
recursos community (ex: S3). Isso diverge da premissa de "disponibilidade
sem custo" da Tabela 14 do PGT, redigida antes dessa mudança.

## Decisão
Adotar o plano Hobby gratuito (não-comercial) do LocalStack, mediante
criação de conta e token pessoal, mantendo a ferramenta originalmente
especificada. Token armazenado em .env, fora do controle de versão.

## Consequências
- Positivo: mantém fidelidade à arquitetura original do PGT.
- Negativo: introduz dependência de conta externa (ainda que gratuita),
  levemente reduzindo a autonomia total do ambiente reprodutível — risco
  documentado e mitigado, sem impacto na validade científica do experimento.
