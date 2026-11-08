package main

import (
	"encoding/json"
	"fmt"
	"regexp"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// reHashSHA256 define o formato aceito para o hash de integridade:
// exatamente 64 caracteres hexadecimais minúsculos (SHA-256).
var reHashSHA256 = regexp.MustCompile(`^[0-9a-f]{64}$`)

// CustodyContract implementa a lógica de cadeia de custódia forense,
// conforme especificado na Seção 2.4.3 do PGT: registro de evidência,
// transferência de custódia e verificação de integridade.
//
// Três garantias são aplicadas pelo próprio contrato, e não apenas pelo
// cliente: (i) o hash deve ter o formato SHA-256; (ii) a autoria do
// registro e da transferência é a identidade criptográfica (MSP) do
// certificado que assinou a transação, nunca um argumento informado pelo
// chamador; e (iii) o instante de registro é o carimbo da transação,
// idêntico para todos os endossantes.
type CustodyContract struct {
	contractapi.Contract
}

// validarHash rejeita hash vazio ou fora do formato SHA-256.
func validarHash(hash string) error {
	if hash == "" {
		return fmt.Errorf("hash SHA-256 não pode ser vazio: evidência sem hash não tem valor probatório")
	}
	if !reHashSHA256.MatchString(hash) {
		return fmt.Errorf("hash SHA-256 inválido: esperados 64 caracteres hexadecimais minúsculos, recebido %q", hash)
	}
	return nil
}

// mspDoChamador devolve o MSP do certificado que assinou a transação.
func mspDoChamador(ctx contractapi.TransactionContextInterface) (string, error) {
	identidade := ctx.GetClientIdentity()
	if identidade == nil {
		return "", fmt.Errorf("identidade do chamador indisponível")
	}
	msp, err := identidade.GetMSPID()
	if err != nil {
		return "", fmt.Errorf("erro ao obter o MSP do chamador: %v", err)
	}
	if msp == "" {
		return "", fmt.Errorf("MSP do chamador vazio")
	}
	return msp, nil
}

// carimboDaTransacao devolve o instante da transação (UTC, RFC 3339),
// determinístico entre os endossantes.
func carimboDaTransacao(ctx contractapi.TransactionContextInterface) (string, error) {
	ts, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return "", fmt.Errorf("erro ao obter o carimbo da transação: %v", err)
	}
	if ts == nil {
		return "", fmt.Errorf("carimbo da transação indisponível")
	}
	return ts.AsTime().UTC().Format(time.RFC3339Nano), nil
}

// RegistrarEvidencia registra uma nova evidência digital no ledger,
// imediatamente após sua coleta em ambiente de nuvem (RF10).
//
// O parâmetro timestamp é o instante da coleta, declarado pelo cliente
// (RFC 3339); o instante do registro é obtido da transação e gravado em
// registrado_em. O agente coletor é o MSP do chamador.
//
// Rejeita: ID, provedor, região ou tipo vazios; hash fora do formato
// SHA-256; timestamp que não seja RFC 3339; e ID duplicado (uma
// evidência só pode ter uma origem).
func (c *CustodyContract) RegistrarEvidencia(
	ctx contractapi.TransactionContextInterface,
	id string,
	hashSHA256 string,
	timestamp string,
	cspOrigem string,
	regiao string,
	tipoArtefato string,
) error {
	if err := validarHash(hashSHA256); err != nil {
		return err
	}
	if id == "" || cspOrigem == "" || regiao == "" || tipoArtefato == "" {
		return fmt.Errorf("id, csp_origem, regiao e tipo_artefato são obrigatórios")
	}
	if _, err := time.Parse(time.RFC3339, timestamp); err != nil {
		return fmt.Errorf("timestamp da coleta inválido (esperado RFC 3339): %q", timestamp)
	}

	agente, err := mspDoChamador(ctx)
	if err != nil {
		return err
	}
	registradoEm, err := carimboDaTransacao(ctx)
	if err != nil {
		return err
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
		RegistradoEm:            registradoEm,
		CSPOrigem:               cspOrigem,
		Regiao:                  regiao,
		TipoArtefato:            tipoArtefato,
		AgenteColetorMSP:        agente,
		CustodianteAtual:        agente,
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
//
// Somente o custodiante atual pode ceder a custódia: o MSP do chamador
// deve ser igual a custodiante_atual. O cedente é sempre o custodiante
// atual gravado no ledger, e o instante é o carimbo da transação.
func (c *CustodyContract) TransferirCustodia(
	ctx contractapi.TransactionContextInterface,
	id string,
	mspCessionario string,
	motivacao string,
) error {
	if mspCessionario == "" || motivacao == "" {
		return fmt.Errorf("msp_cessionario e motivacao são obrigatórios")
	}

	chamador, err := mspDoChamador(ctx)
	if err != nil {
		return err
	}
	instante, err := carimboDaTransacao(ctx)
	if err != nil {
		return err
	}

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

	if chamador != evidencia.CustodianteAtual {
		return fmt.Errorf("transferência não autorizada: o custodiante atual é '%s' e o chamador é '%s'",
			evidencia.CustodianteAtual, chamador)
	}
	if mspCessionario == evidencia.CustodianteAtual {
		return fmt.Errorf("o cessionário '%s' já é o custodiante atual", mspCessionario)
	}

	transferencia := TransferenciaCustodia{
		MSPCedente:     evidencia.CustodianteAtual,
		MSPCessionario: mspCessionario,
		Timestamp:      instante,
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

// VerificarIntegridade compara o hash fornecido pelo chamador (calculado
// a partir de uma nova coleta) com o hash originalmente registrado,
// retornando o resultado da verificação e o histórico completo de
// custódia. Um hash fora do formato SHA-256 é erro de entrada, e não
// "integridade inválida".
func (c *CustodyContract) VerificarIntegridade(
	ctx contractapi.TransactionContextInterface,
	id string,
	hashRecalculado string,
) (*ResultadoVerificacao, error) {
	if err := validarHash(hashRecalculado); err != nil {
		return nil, err
	}

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
