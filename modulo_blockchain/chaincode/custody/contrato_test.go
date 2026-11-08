package main

import (
	"crypto/x509"
	"encoding/json"
	"testing"
	"time"

	"github.com/hyperledger/fabric-chaincode-go/v2/pkg/cid"
	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
	"github.com/stretchr/testify/require"
	"google.golang.org/protobuf/types/known/timestamppb"

	"ccf-custody-chaincode/mocks"
)

const (
	hashA = "a892d7a517939e5d07e61ab3b2e5c5db8be675d75801e0c60221a68412bbd2a4"
	hashB = "b892d7a517939e5d07e61ab3b2e5c5db8be675d75801e0c60221a68412bbd2a4"

	instanteTx = "2026-11-08T04:30:00Z"
	coleta     = "2026-11-08T04:18:31.154232+00:00"
)

// identidadeFalsa implementa cid.ClientIdentity com um MSP fixo.
type identidadeFalsa struct{ msp string }

func (i identidadeFalsa) GetID() (string, error)    { return "id-" + i.msp, nil }
func (i identidadeFalsa) GetMSPID() (string, error) { return i.msp, nil }
func (i identidadeFalsa) GetAttributeValue(string) (string, bool, error) {
	return "", false, nil
}
func (i identidadeFalsa) AssertAttributeValue(string, string) error { return nil }
func (i identidadeFalsa) GetX509Certificate() (*x509.Certificate, error) {
	return nil, nil
}

var _ cid.ClientIdentity = identidadeFalsa{}

// novoContexto monta um contexto de transação cujo chamador pertence ao
// MSP informado e cujo carimbo é fixo (instanteTx).
func novoContexto(msp string) (*mocks.TransactionContext, *mocks.ChaincodeStub) {
	stub := &mocks.ChaincodeStub{}
	ctx := &mocks.TransactionContext{}
	ctx.GetStubReturns(stub)
	ctx.GetClientIdentityReturns(identidadeFalsa{msp: msp})
	instante, _ := time.Parse(time.RFC3339, instanteTx)
	stub.GetTxTimestampReturns(timestamppb.New(instante), nil)
	return ctx, stub
}

func registrar(ctx contractapi.TransactionContextInterface, id, hash, ts string) error {
	contract := CustodyContract{}
	return contract.RegistrarEvidencia(ctx, id, hash, ts, "aws", "us-east-1", "imagem")
}

// gravada devolve a evidência escrita na primeira chamada de PutState.
func gravada(t *testing.T, stub *mocks.ChaincodeStub, chamada int) (string, Evidencia) {
	t.Helper()
	chave, valor := stub.PutStateArgsForCall(chamada)
	var e Evidencia
	require.NoError(t, json.Unmarshal(valor, &e))
	return chave, e
}

func evidenciaJSON(t *testing.T, e Evidencia) []byte {
	t.Helper()
	b, err := json.Marshal(e)
	require.NoError(t, err)
	return b
}

// --- RegistrarEvidencia -------------------------------------------------

// TestRegistrarEvidencia_Sucesso valida o caminho feliz: uma evidência
// nova é registrada com os metadados exigidos pelo RF10, o agente
// coletor vem da identidade do chamador e o instante do registro é o
// carimbo da transação.
func TestRegistrarEvidencia_Sucesso(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(nil, nil)

	require.NoError(t, registrar(ctx, "evid-001", hashA, coleta))

	require.Equal(t, 1, stub.PutStateCallCount())
	chave, e := gravada(t, stub, 0)
	require.Equal(t, "evid-001", chave)
	require.Equal(t, hashA, e.HashSHA256)
	require.Equal(t, coleta, e.Timestamp)
	require.Equal(t, instanteTx, e.RegistradoEm)
	require.Equal(t, "Org1MSP", e.AgenteColetorMSP)
	require.Equal(t, "Org1MSP", e.CustodianteAtual)
	require.Empty(t, e.HistoricoTransferencias)
}

// TestRegistrarEvidencia_AgenteVemDaIdentidade garante que a autoria é a
// do certificado que assinou a transação, e não um dado informado.
func TestRegistrarEvidencia_AgenteVemDaIdentidade(t *testing.T) {
	ctx, stub := novoContexto("Org2MSP")
	stub.GetStateReturns(nil, nil)

	require.NoError(t, registrar(ctx, "evid-001", hashA, coleta))

	_, e := gravada(t, stub, 0)
	require.Equal(t, "Org2MSP", e.AgenteColetorMSP)
	require.Equal(t, "Org2MSP", e.CustodianteAtual)
}

// TestRegistrarEvidencia_IDDuplicado garante que a origem não é sobrescrita.
func TestRegistrarEvidencia_IDDuplicado(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns([]byte(`{"id":"evid-001"}`), nil)

	err := registrar(ctx, "evid-001", hashA, coleta)

	require.Error(t, err)
	require.Contains(t, err.Error(), "já está registrada")
	require.Equal(t, 0, stub.PutStateCallCount())
}

// TestRegistrarEvidencia_HashVazio garante rejeição de hash vazio.
func TestRegistrarEvidencia_HashVazio(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")

	err := registrar(ctx, "evid-002", "", coleta)

	require.Error(t, err)
	require.Contains(t, err.Error(), "hash SHA-256 não pode ser vazio")
	require.Equal(t, 0, stub.PutStateCallCount())
}

// TestRegistrarEvidencia_HashForaDoFormato reproduz o incidente da
// primeira execução do C2, em que um marcador de posição foi gravado no
// lugar do hash: o contrato agora o rejeita.
func TestRegistrarEvidencia_HashForaDoFormato(t *testing.T) {
	casos := map[string]string{
		"marcador de posição": "COLE_O_HASH_AQUI",
		"maiúsculas":          "A892D7A517939E5D07E61AB3B2E5C5DB8BE675D75801E0C60221A68412BBD2A4",
		"curto (63)":          hashA[:63],
		"longo (65)":          hashA + "a",
		"não hexadecimal":     "g" + hashA[1:],
	}
	for nome, hash := range casos {
		t.Run(nome, func(t *testing.T) {
			ctx, stub := novoContexto("Org1MSP")

			err := registrar(ctx, "evid-002", hash, coleta)

			require.Error(t, err)
			require.Contains(t, err.Error(), "hash SHA-256 inválido")
			require.Equal(t, 0, stub.PutStateCallCount())
		})
	}
}

// TestRegistrarEvidencia_TimestampInvalido rejeita o outro marcador do
// incidente (carimbo de coleta que não é RFC 3339).
func TestRegistrarEvidencia_TimestampInvalido(t *testing.T) {
	for _, ts := range []string{"TIMESTAMP_DA_COLETA", "", "08/11/2026"} {
		ctx, stub := novoContexto("Org1MSP")

		err := registrar(ctx, "evid-002", hashA, ts)

		require.Error(t, err, ts)
		require.Contains(t, err.Error(), "timestamp da coleta inválido")
		require.Equal(t, 0, stub.PutStateCallCount())
	}
}

// TestRegistrarEvidencia_CamposObrigatorios rejeita metadados vazios.
func TestRegistrarEvidencia_CamposObrigatorios(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	contract := CustodyContract{}

	err := contract.RegistrarEvidencia(ctx, "evid-003", hashA, coleta, "", "us-east-1", "imagem")

	require.Error(t, err)
	require.Contains(t, err.Error(), "obrigatórios")
	require.Equal(t, 0, stub.PutStateCallCount())
}

// TestRegistrarEvidencia_IdentidadeIndisponivel não grava sem identidade.
func TestRegistrarEvidencia_IdentidadeIndisponivel(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	ctx.GetClientIdentityReturns(nil)

	err := registrar(ctx, "evid-001", hashA, coleta)

	require.Error(t, err)
	require.Contains(t, err.Error(), "identidade do chamador indisponível")
	require.Equal(t, 0, stub.PutStateCallCount())
}

// --- TransferirCustodia -------------------------------------------------

func evidenciaCustodiadaPor(t *testing.T, msp string) []byte {
	return evidenciaJSON(t, Evidencia{
		ID: "evid-001", HashSHA256: hashA, AgenteColetorMSP: msp, CustodianteAtual: msp,
		HistoricoTransferencias: []TransferenciaCustodia{},
	})
}

// TestTransferirCustodia_Sucesso valida a transferência feita pelo
// custodiante atual: o cedente vem do ledger e o instante, da transação.
func TestTransferirCustodia_Sucesso(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(evidenciaCustodiadaPor(t, "Org1MSP"), nil)

	contract := CustodyContract{}
	err := contract.TransferirCustodia(ctx, "evid-001", "Org2MSP", "encaminhamento ao laboratório pericial")

	require.NoError(t, err)
	require.Equal(t, 1, stub.PutStateCallCount())
	_, e := gravada(t, stub, 0)
	require.Equal(t, "Org2MSP", e.CustodianteAtual)
	require.Len(t, e.HistoricoTransferencias, 1)
	require.Equal(t, TransferenciaCustodia{
		MSPCedente: "Org1MSP", MSPCessionario: "Org2MSP",
		Timestamp: instanteTx, Motivacao: "encaminhamento ao laboratório pericial",
	}, e.HistoricoTransferencias[0])
}

// TestTransferirCustodia_EvidenciaInexistente garante rejeição de
// transferência para evidência não registrada.
func TestTransferirCustodia_EvidenciaInexistente(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(nil, nil)

	contract := CustodyContract{}
	err := contract.TransferirCustodia(ctx, "evid-inexistente", "Org2MSP", "motivo qualquer")

	require.Error(t, err)
	require.Contains(t, err.Error(), "não encontrada")
}

// TestTransferirCustodia_ChamadorNaoCustodiante garante que somente o
// custodiante atual cede a custódia (controle de acesso).
func TestTransferirCustodia_ChamadorNaoCustodiante(t *testing.T) {
	ctx, stub := novoContexto("Org2MSP") // não é o custodiante
	stub.GetStateReturns(evidenciaCustodiadaPor(t, "Org1MSP"), nil)

	contract := CustodyContract{}
	err := contract.TransferirCustodia(ctx, "evid-001", "Org2MSP", "tentativa de apropriação")

	require.Error(t, err)
	require.Contains(t, err.Error(), "transferência não autorizada")
	require.Equal(t, 0, stub.PutStateCallCount())
}

// TestTransferirCustodia_CessionarioIgualAoCustodiante rejeita
// transferência vazia de efeito.
func TestTransferirCustodia_CessionarioIgualAoCustodiante(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(evidenciaCustodiadaPor(t, "Org1MSP"), nil)

	contract := CustodyContract{}
	err := contract.TransferirCustodia(ctx, "evid-001", "Org1MSP", "sem efeito")

	require.Error(t, err)
	require.Contains(t, err.Error(), "já é o custodiante atual")
	require.Equal(t, 0, stub.PutStateCallCount())
}

// TestTransferirCustodia_CamposObrigatorios exige cessionário e motivação.
func TestTransferirCustodia_CamposObrigatorios(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(evidenciaCustodiadaPor(t, "Org1MSP"), nil)

	contract := CustodyContract{}
	err := contract.TransferirCustodia(ctx, "evid-001", "Org2MSP", "")

	require.Error(t, err)
	require.Contains(t, err.Error(), "obrigatórios")
	require.Equal(t, 0, stub.PutStateCallCount())
}

// --- VerificarIntegridade ----------------------------------------------

func evidenciaComHash(t *testing.T, hash string) []byte {
	return evidenciaJSON(t, Evidencia{ID: "evid-001", HashSHA256: hash})
}

// TestVerificarIntegridade_HashValido valida que hashes idênticos
// retornam integridade confirmada.
func TestVerificarIntegridade_HashValido(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(evidenciaComHash(t, hashA), nil)

	contract := CustodyContract{}
	resultado, err := contract.VerificarIntegridade(ctx, "evid-001", hashA)

	require.NoError(t, err)
	require.True(t, resultado.IntegridadeValida)
}

// TestVerificarIntegridade_HashDivergente valida que um hash bem
// formado, mas diferente do original, sinaliza violação de integridade.
func TestVerificarIntegridade_HashDivergente(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(evidenciaComHash(t, hashA), nil)

	contract := CustodyContract{}
	resultado, err := contract.VerificarIntegridade(ctx, "evid-001", hashB)

	require.NoError(t, err)
	require.False(t, resultado.IntegridadeValida, "deveria sinalizar violação de integridade")
	require.Equal(t, hashA, resultado.HashOriginal)
	require.Equal(t, hashB, resultado.HashRecalculado)
}

// TestVerificarIntegridade_HashMalformado distingue erro de entrada de
// violação de integridade.
func TestVerificarIntegridade_HashMalformado(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(evidenciaComHash(t, hashA), nil)

	contract := CustodyContract{}
	_, err := contract.VerificarIntegridade(ctx, "evid-001", "hash_diferente_xyz")

	require.Error(t, err)
	require.Contains(t, err.Error(), "hash SHA-256 inválido")
}

// TestVerificarIntegridade_EvidenciaInexistente rejeita ID desconhecido.
func TestVerificarIntegridade_EvidenciaInexistente(t *testing.T) {
	ctx, stub := novoContexto("Org1MSP")
	stub.GetStateReturns(nil, nil)

	contract := CustodyContract{}
	_, err := contract.VerificarIntegridade(ctx, "evid-x", hashA)

	require.Error(t, err)
	require.Contains(t, err.Error(), "não encontrada")
}

var _ contractapi.TransactionContextInterface = (*mocks.TransactionContext)(nil)
