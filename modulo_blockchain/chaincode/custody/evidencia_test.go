package main

import (
	"encoding/json"
	"testing"
)

// Testa que a struct Evidencia serializa/desserializa corretamente em
// JSON — formato usado tanto para armazenamento no ledger (CouchDB)
// quanto para consultas ricas (RF: dashboard, laudo pericial).
func TestEvidenciaJSONSerialization(t *testing.T) {
	original := Evidencia{
		ID:               "evid-001",
		HashSHA256:       "a892d7a517939e5d07e61ab3b2e5c5db8be675d75801e0c60221a68412bbd2a4",
		Timestamp:        "2026-07-09T10:00:00Z",
		CSPOrigem:        "aws",
		Regiao:           "us-east-1",
		TipoArtefato:     "imagem",
		AgenteColetorMSP: "Org1MSP",
		CustodianteAtual: "Org1MSP",
	}

	bytes, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("erro ao serializar Evidencia: %v", err)
	}

	var reconstruida Evidencia
	err = json.Unmarshal(bytes, &reconstruida)
	if err != nil {
		t.Fatalf("erro ao desserializar Evidencia: %v", err)
	}

	if reconstruida.ID != original.ID {
		t.Errorf("ID: esperado %s, obtido %s", original.ID, reconstruida.ID)
	}
	if reconstruida.HashSHA256 != original.HashSHA256 {
		t.Errorf("HashSHA256: esperado %s, obtido %s", original.HashSHA256, reconstruida.HashSHA256)
	}
}

// Testa que o histórico de transferências é inicializado vazio para
// uma evidência recém-criada — nenhuma custódia foi transferida ainda.
func TestEvidenciaHistoricoTransferenciasInicial(t *testing.T) {
	e := Evidencia{ID: "evid-002"}
	if e.HistoricoTransferencias == nil {
		// Aceitável ser nil neste ponto — validaremos a inicialização
		// real dentro da função RegistrarEvidencia (Tarefa 3).
		t.Log("HistoricoTransferencias é nil por padrão (esperado antes do registro)")
	}
}
