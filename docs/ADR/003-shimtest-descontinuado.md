# ADR 003 — Migração de shimtest para mocks via counterfeiter

## Contexto
O pacote shimtest (fabric-chaincode-go), usado tradicionalmente para
testes unitários de chaincode com MockStub, foi oficialmente
descontinuado ("Deprecated: ShimTest will be removed in a future
release"). A documentação recomenda gerar mocks da interface
ChaincodeStubInterface diretamente.

## Decisão
Adotar o padrão usado pelo próprio fabric-samples (asset-transfer-basic):
gerar mocks de ChaincodeStubInterface e TransactionContextInterface via
counterfeiter, testando os métodos do contrato diretamente (não via
dispatch de string como no MockInvoke antigo).

## Consequências
- Positivo: alinhado ao padrão oficial atual; testes mais expressivos
  (chamada direta de método, não string parsing).
- Negativo: exige ferramenta adicional (counterfeiter) e passo de
  geração de código (go generate) antes de rodar os testes.
