package main

import (
	"log"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// registra o CustodyContract junto ao runtime do Fabric (shim), conforme padrão contractapi.
func main() {
	chaincode, err := contractapi.NewChaincode(&CustodyContract{})
	if err != nil {
		log.Panicf("Erro ao criar o chaincode de custódia: %v", err)
	}

	if err := chaincode.Start(); err != nil {
		log.Panicf("Erro ao iniciar o chaincode de custódia: %v", err)
	}
}
