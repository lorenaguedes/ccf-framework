package main

import (
	"testing"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
	"github.com/stretchr/testify/require"

	"ccf-custody-chaincode/mocks"
)

// TestRegistrarEvidencia_Sucesso valida o caminho feliz: uma evidência
// nova é registrada com todos os metadados exigidos pelo RF10.
func TestRegistrarEvidencia_Sucesso(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	// Simula que a evidência ainda não existe no ledger
	chaincodeStub.GetStateReturns(nil, nil)

	contract := CustodyContract{}
	err := contract.RegistrarEvidencia(
		transactionContext,
		"evid-001",
		"a892d7a517939e5d07e61ab3b2e5c5db8be675d75801e0c60221a68412bbd2a4",
		"2026-07-09T10:00:00Z",
		"aws",
		"us-east-1",
		"imagem",
		"Org1MSP",
	)

	require.NoError(t, err)
	require.Equal(t, 1, chaincodeStub.PutStateCallCount(), "esperava exatamente 1 chamada a PutState")
}

// TestRegistrarEvidencia_IDDuplicado garante que não é possível
// registrar duas vezes a mesma evidência.
func TestRegistrarEvidencia_IDDuplicado(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	// Simula que a evidência JÁ existe no ledger
	chaincodeStub.GetStateReturns([]byte(`{"id":"evid-001"}`), nil)

	contract := CustodyContract{}
	err := contract.RegistrarEvidencia(
		transactionContext,
		"evid-001",
		"hash123",
		"2026-07-09T10:00:00Z",
		"aws",
		"us-east-1",
		"imagem",
		"Org1MSP",
	)

	require.Error(t, err)
	require.Contains(t, err.Error(), "já está registrada")
}

// TestRegistrarEvidencia_HashVazio garante rejeição de hash vazio.
func TestRegistrarEvidencia_HashVazio(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	contract := CustodyContract{}
	err := contract.RegistrarEvidencia(
		transactionContext,
		"evid-002",
		"", // hash vazio
		"2026-07-09T10:00:00Z",
		"aws",
		"us-east-1",
		"imagem",
		"Org1MSP",
	)

	require.Error(t, err)
	require.Contains(t, err.Error(), "hash SHA-256 não pode ser vazio")
}

// TestTransferirCustodia_Sucesso valida transferência de custódia de
// uma evidência existente.
func TestTransferirCustodia_Sucesso(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	evidenciaExistente := `{"id":"evid-001","custodiante_atual":"Org1MSP","historico_transferencias":[]}`
	chaincodeStub.GetStateReturns([]byte(evidenciaExistente), nil)

	contract := CustodyContract{}
	err := contract.TransferirCustodia(
		transactionContext,
		"evid-001",
		"Org2MSP",
		"2026-07-09T11:00:00Z",
		"encaminhamento ao laboratório pericial",
	)

	require.NoError(t, err)
	require.Equal(t, 1, chaincodeStub.PutStateCallCount())
}

// TestTransferirCustodia_EvidenciaInexistente garante rejeição de
// transferência para evidência não registrada.
func TestTransferirCustodia_EvidenciaInexistente(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	chaincodeStub.GetStateReturns(nil, nil)

	contract := CustodyContract{}
	err := contract.TransferirCustodia(
		transactionContext,
		"evid-inexistente",
		"Org2MSP",
		"2026-07-09T11:00:00Z",
		"motivo qualquer",
	)

	require.Error(t, err)
	require.Contains(t, err.Error(), "não encontrada")
}

// TestVerificarIntegridade_HashValido valida que hashes idênticos
// retornam integridade confirmada.
func TestVerificarIntegridade_HashValido(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	hashOriginal := "a892d7a517939e5d07e61ab3b2e5c5db8be675d75801e0c60221a68412bbd2a4"
	evidenciaExistente := `{"id":"evid-001","hash_sha256":"` + hashOriginal + `","historico_transferencias":[]}`
	chaincodeStub.GetStateReturns([]byte(evidenciaExistente), nil)

	contract := CustodyContract{}
	resultado, err := contract.VerificarIntegridade(transactionContext, "evid-001", hashOriginal)

	require.NoError(t, err)
	require.True(t, resultado.IntegridadeValida)
}

// TestVerificarIntegridade_HashDivergente valida que hashes diferentes
// sinalizam violação de integridade
func TestVerificarIntegridade_HashDivergente(t *testing.T) {
	chaincodeStub := &mocks.ChaincodeStub{}
	transactionContext := &mocks.TransactionContext{}
	transactionContext.GetStubReturns(chaincodeStub)

	evidenciaExistente := `{"id":"evid-001","hash_sha256":"hash_original_abc","historico_transferencias":[]}`
	chaincodeStub.GetStateReturns([]byte(evidenciaExistente), nil)

	contract := CustodyContract{}
	resultado, err := contract.VerificarIntegridade(transactionContext, "evid-001", "hash_diferente_xyz")

	require.NoError(t, err)
	require.False(t, resultado.IntegridadeValida, "deveria sinalizar violação de integridade")
}

var _ contractapi.TransactionContextInterface = (*mocks.TransactionContext)(nil)
