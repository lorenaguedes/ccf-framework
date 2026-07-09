package main

// Evidencia representa o estado de uma evidência digital na cadeia de
// custódia, conforme especificado na Seção 2.4.3 do PGT: registro de
// identificador, hash de integridade, metadados de coleta e histórico
// de transferências de custódia.
type Evidencia struct {
	ID                      string                `json:"id"`
	HashSHA256              string                `json:"hash_sha256"`
	Timestamp               string                `json:"timestamp"`
	CSPOrigem               string                `json:"csp_origem"`
	Regiao                  string                `json:"regiao"`
	TipoArtefato            string                `json:"tipo_artefato"`
	AgenteColetorMSP        string                `json:"agente_coletor_msp"`
	CustodianteAtual        string                `json:"custodiante_atual"`
	HistoricoTransferencias []TransferenciaCustodia `json:"historico_transferencias"`
}

// TransferenciaCustodia representa um único evento de mudança de
// responsável pela evidência (coletor → laboratório → MP → Judiciário),
// conforme função "transferir custódia" descrita no PGT.
type TransferenciaCustodia struct {
	MSPCedente     string `json:"msp_cedente"`
	MSPCessionario string `json:"msp_cessionario"`
	Timestamp      string `json:"timestamp"`
	Motivacao      string `json:"motivacao"`
}

// ResultadoVerificacao representa o resultado da verificação de
// integridade de uma evidência, incluindo o histórico completo de
// custódia para reconstrução da trajetória probatória (Seção 2.4.3, PGT).
type ResultadoVerificacao struct {
	EvidenciaID             string                  `json:"evidencia_id"`
	HashOriginal             string                  `json:"hash_original"`
	HashRecalculado          string                  `json:"hash_recalculado"`
	IntegridadeValida        bool                    `json:"integridade_valida"`
	HistoricoTransferencias  []TransferenciaCustodia `json:"historico_transferencias"`
}
