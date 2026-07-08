# ADR 001 — Desabilitação do containerd no Docker Desktop

## Contexto
O Hyperledger Fabric 2.5 utiliza uma biblioteca interna de comunicação com a
API do Docker incompatível com o modo containerd (ativado por padrão em
versões recentes do Docker Desktop, ex: 29.1.5). Isso causa falha
"broken pipe" ao construir a imagem do chaincode durante peer lifecycle
chaincode install.

## Decisão
Desabilitar "Use containerd for pulling and storing images" em
Docker Desktop > Settings > General.

## Consequências
- Positivo: resolve a falha de instalação de chaincode de forma definitiva.
- Negativo: perde-se otimizações de storage do containerd; sem impacto
  relevante no escopo deste projeto (ambiente de laboratório, não produção).

