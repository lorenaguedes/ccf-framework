"""
Cliente Python da cadeia de custodia (chaincode 'custody', RF10).

Invoca e consulta o chaincode na rede Hyperledger Fabric de teste por
meio do peer CLI, substituindo o registro manual por linha de comando
usado nas execucoes iniciais dos cenarios. A automacao elimina duas
falhas do procedimento manual: a digitacao de um hash ou de um
timestamp incorretos e a ausencia de conferencia do que foi gravado.

Garantias:
- o hash e validado (64 caracteres hexadecimais) antes de qualquer
  chamada, de modo que um marcador de posicao nunca chega ao ledger;
- apos o registro, o ledger e consultado e o hash gravado e comparado
  com o hash coletado; o resultado so e "success" se forem iguais;
- o registro e idempotente: se o ID ja existir com o mesmo hash, nao
  ha nova gravacao, e a divergencia de hash e reportada como falha.

A funcao de execucao (runner) e injetavel para testes unitarios sem a
rede Fabric. A integracao com a rede real e validada por execucao
direta (cenarios C1 a C3).
"""
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable

FABRIC_TEST_NETWORK_DIR = Path.home() / "fabric-dev/fabric-samples/test-network"
CANAL = "ccfchannel"
CHAINCODE = "custody"

_RE_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _ambiente(rede_dir: Path) -> dict:
    """Variaveis de ambiente do peer CLI (organizacao 1, administrador)."""
    org = rede_dir / "organizations" / "peerOrganizations" / "org1.example.com"
    env = dict(os.environ)
    env.update({
        "PATH": f"{rede_dir.parent / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}",
        "FABRIC_CFG_PATH": str(rede_dir.parent / "config"),
        "CORE_PEER_TLS_ENABLED": "true",
        "CORE_PEER_LOCALMSPID": "Org1MSP",
        "CORE_PEER_TLS_ROOTCERT_FILE": str(org / "peers/peer0.org1.example.com/tls/ca.crt"),
        "CORE_PEER_MSPCONFIGPATH": str(org / "users/Admin@org1.example.com/msp"),
        "CORE_PEER_ADDRESS": "localhost:7051",
    })
    return env


def _comando_invoke(rede_dir: Path, funcao: str, args: list) -> list:
    orgs = rede_dir / "organizations"
    ca_org1 = orgs / "peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt"
    ca_org2 = orgs / "peerOrganizations/org2.example.com/peers/peer0.org2.example.com/tls/ca.crt"
    ca_orderer = (orgs / "ordererOrganizations/example.com/orderers/orderer.example.com"
                  / "msp/tlscacerts/tlsca.example.com-cert.pem")
    return [
        "peer", "chaincode", "invoke",
        "-o", "localhost:7050", "--ordererTLSHostnameOverride", "orderer.example.com",
        "--tls", "--cafile", str(ca_orderer),
        "-C", CANAL, "-n", CHAINCODE,
        "--peerAddresses", "localhost:7051", "--tlsRootCertFiles", str(ca_org1),
        "--peerAddresses", "localhost:9051", "--tlsRootCertFiles", str(ca_org2),
        "-c", json.dumps({"function": funcao, "Args": args}),
    ]


def _comando_query(funcao: str, args: list) -> list:
    return [
        "peer", "chaincode", "query", "-C", CANAL, "-n", CHAINCODE,
        "-c", json.dumps({"function": funcao, "Args": args}),
    ]


def _mensagem_falha(prefixo: str, stderr: str) -> str:
    """Acrescenta orientacao quando a causa e a rede Fabric fora do ar."""
    detalhe = stderr.strip()
    if "connection refused" in detalhe or "failed to connect" in detalhe:
        return (f"{prefixo}: rede Hyperledger Fabric inacessivel (peer em localhost:7051). "
                "Inicie os containers da rede (docker start dos containers peer/orderer/CA) "
                f"ou suba a rede com ./network.sh up. Detalhe: {detalhe}")
    return f"{prefixo}: {detalhe}"


def _validar_hash(hash_sha256: str) -> None:
    if not isinstance(hash_sha256, str) or not _RE_SHA256.match(hash_sha256):
        raise ValueError(
            "Hash SHA-256 invalido: esperados 64 caracteres hexadecimais "
            f"em minusculas, recebido {hash_sha256!r}."
        )


def consultar_evidencia(
    evidence_id: str,
    rede_dir: Path = FABRIC_TEST_NETWORK_DIR,
    runner: Callable = subprocess.run,
) -> dict | None:
    """Consulta uma evidencia no ledger. Retorna o dicionario do
    chaincode (hash_sha256, timestamp, ...) ou None se nao existir.

    Raises:
        RuntimeError: se a consulta falhar por outro motivo.
    """
    r = runner(_comando_query("ConsultarEvidencia", [evidence_id]),
               env=_ambiente(rede_dir), capture_output=True, text=True)
    if r.returncode != 0:
        if "não encontrada" in r.stderr or "nao encontrada" in r.stderr:
            return None
        raise RuntimeError(_mensagem_falha("Falha na consulta ao ledger", r.stderr))
    return json.loads(r.stdout)


def verificar_integridade(
    evidence_id: str,
    hash_recalculado: str,
    rede_dir: Path = FABRIC_TEST_NETWORK_DIR,
    runner: Callable = subprocess.run,
) -> dict:
    """Compara um hash recalculado a partir da evidencia recoletada com o
    hash gravado no ledger (funcao VerificarIntegridade do chaincode)."""
    _validar_hash(hash_recalculado)
    r = runner(_comando_query("VerificarIntegridade", [evidence_id, hash_recalculado]),
               env=_ambiente(rede_dir), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(_mensagem_falha("Falha na verificacao de integridade", r.stderr))
    return json.loads(r.stdout)


def registrar_e_verificar(
    evidence_id: str,
    hash_sha256: str,
    timestamp: str,
    csp_origem: str,
    regiao: str,
    tipo_artefato: str,
    agente_msp: str = "Org1MSP",
    rede_dir: Path = FABRIC_TEST_NETWORK_DIR,
    runner: Callable = subprocess.run,
) -> dict:
    """Registra a evidencia no ledger (se ainda nao existir) e confere o
    hash gravado.

    Returns:
        {"status": "success" | "falha_hash_divergente", "evidence_id",
         "chaincode_status", "hash", "hash_no_ledger", "acao"}, em que
        acao e "registrada" ou "ja_registrada".

    Raises:
        ValueError: hash invalido ou timestamp vazio.
        RuntimeError: se a gravacao ou a consulta ao ledger falhar.
    """
    _validar_hash(hash_sha256)
    if not timestamp or not evidence_id:
        raise ValueError("evidence_id e timestamp sao obrigatorios.")

    existente = consultar_evidencia(evidence_id, rede_dir, runner)
    acao = "ja_registrada"
    if existente is None:
        args = [evidence_id, hash_sha256, timestamp, csp_origem, regiao,
                tipo_artefato, agente_msp]
        r = runner(_comando_invoke(rede_dir, "RegistrarEvidencia", args),
                   env=_ambiente(rede_dir), capture_output=True, text=True)
        saida = f"{r.stdout}\n{r.stderr}"
        if r.returncode != 0 or "status:200" not in saida:
            raise RuntimeError(f"Falha ao registrar a evidencia: {saida.strip()}")
        acao = "registrada"
        existente = consultar_evidencia(evidence_id, rede_dir, runner)
        if existente is None:
            raise RuntimeError("Evidencia registrada nao foi encontrada na consulta ao ledger.")

    hash_ledger = existente.get("hash_sha256")
    return {
        "status": "success" if hash_ledger == hash_sha256 else "falha_hash_divergente",
        "evidence_id": evidence_id,
        "chaincode_status": 200,
        "hash": hash_sha256,
        "hash_no_ledger": hash_ledger,
        "acao": acao,
    }
