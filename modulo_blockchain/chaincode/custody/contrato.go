package main

import (
	"encoding/json"
	"fmt"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// CustodyContract implementa a lógica de cadeia de custódia forense,
// conforme especificado na Seção 2.4.3 do PGT: registro de evidência,
// transferência de custódia e verificação de integridade.
type CustodyContract struct {
	contractapi.Contract
}

// RegistrarEvidencia registra uma nova evidência digital no ledger,
// imediatamente após sua coleta em ambiente de nuvem (RF10).
//
// Rejeita: ID duplicado (uma evidência só pode ter uma origem) e
// hash vazio (evidência sem hash não tem valor probatório - RNF01).
func (c *CustodyContract) RegistrarEvidencia(
	ctx contractapi.TransactionContextInterface,
	id string,
	hashSHA256 string,
	timestamp string,
	cspOrigem string,
	regiao string,
	tipoArtefato string,
	agenteColetorMSP string,
) error {
	if hashSHA256 == "" {
		return fmt.Errorf("hash SHA-256 não pode ser vazio: evidência sem hash não tem valor probatório")
	}

	existente, err := ctx.GetStub().GetState(id)
	if err != nil {
		return fmt.Errorf("erro ao consultar ledger: %v", err)
	}
	if existente != nil {
		return fmt.Errorf("evidência com ID '%s' já está registrada: não é possível sobrescrever origem", id)
	}

	evidencia := Evidencia{
		ID:                      id,
		HashSHA256:              hashSHA256,
		Timestamp:               timestamp,
		CSPOrigem:               cspOrigem,
		Regiao:                  regiao,
		TipoArtefato:            tipoArtefato,
		AgenteColetorMSP:        agenteColetorMSP,
		CustodianteAtual:        agenteColetorMSP,
		HistoricoTransferencias: []TransferenciaCustodia{},
	}

	bytes, err := json.Marshal(evidencia)
	if err != nil {
		return fmt.Errorf("erro ao serializar evidência: %v", err)
	}

	return ctx.GetStub().PutState(id, bytes)
}

// TransferirCustodia registra uma mudança de responsável pela
// evidência (coletor → laboratório → MP → Judiciário), conforme
// função descrita na Seção 2.4.3 do PGT.
func (c *CustodyContract) TransferirCustodia(
	ctx contractapi.TransactionContextInterface,
	id string,
	mspCessionario string,
	timestamp string,
	motivacao string,
) error {
	bytes, err := ctx.GetStub().GetState(id)
	if err != nil {
		return fmt.Errorf("erro ao consultar ledger: %v", err)
	}
	if bytes == nil {
		return fmt.Errorf("evidência com ID '%s' não encontrada: não é possível transferir custódia de evidência inexistente", id)
	}

	var evidencia Evidencia
	if err := json.Unmarshal(bytes, &evidencia); err != nil {
		return fmt.Errorf("erro ao desserializar evidência: %v", err)
	}

	transferencia := TransferenciaCustodia{
		MSPCedente:     evidencia.CustodianteAtual,
		MSPCessionario: mspCessionario,
		Timestamp:      timestamp,
		Motivacao:      motivacao,
	}

	evidencia.HistoricoTransferencias = append(evidencia.HistoricoTransferencias, transferencia)
	evidencia.CustodianteAtual = mspCessionario

	novoBytes, err := json.Marshal(evidencia)
	if err != nil {
		return fmt.Errorf("erro ao serializar evidência atualizada: %v", err)
	}

	return ctx.GetStub().PutState(id, novoBytes)
}

// VerificarIntegridade recalcula (a partir de um hash fornecido pelo
// chamador) e compara com o hash originalmente registrado, retornando
// o resultado da verificação e o histórico completo de custódia.
func (c *CustodyContract) VerificarIntegridade(
	ctx contractapi.TransactionContextInterface,
	id string,
	hashRecalculado string,
) (*ResultadoVerificacao, error) {
	bytes, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("erro ao consultar ledger: %v", err)
	}
	if bytes == nil {
		return nil, fmt.Errorf("evidência com ID '%s' não encontrada", id)
	}

	var evidencia Evidencia
	if err := json.Unmarshal(bytes, &evidencia); err != nil {
		return nil, fmt.Errorf("erro ao desserializar evidência: %v", err)
	}

	return &ResultadoVerificacao{
		EvidenciaID:             id,
		HashOriginal:            evidencia.HashSHA256,
		HashRecalculado:         hashRecalculado,
		IntegridadeValida:       evidencia.HashSHA256 == hashRecalculado,
		HistoricoTransferencias: evidencia.HistoricoTransferencias,
	}, nil
}

// ConsultarEvidencia retorna o estado completo de uma evidência —
// função auxiliar de consulta, usada pelos testes e futuramente pelo
// dashboard XAI (RF13).
func (c *CustodyContract) ConsultarEvidencia(
	ctx contractapi.TransactionContextInterface,
	id string,
) (*Evidencia, error) {
	bytes, err := ctx.GetStub().GetState(id)
	if err != nil {
		return nil, fmt.Errorf("erro ao consultar ledger: %v", err)
	}
	if bytes == nil {
		return nil, fmt.Errorf("evidência com ID '%s' não encontrada", id)
	}

	var evidencia Evidencia
	if err := json.Unmarshal(bytes, &evidencia); err != nil {
		return nil, fmt.Errorf("erro ao desserializar evidência: %v", err)
	}

	return &evidencia, nil
}
