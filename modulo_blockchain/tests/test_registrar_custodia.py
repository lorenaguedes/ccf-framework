"""
Testes unitarios do cliente da cadeia de custodia (RF10), com o peer CLI
substituido por um executor injetado: a logica de validacao, a
idempotencia e a conferencia do hash sao testadas sem a rede Fabric.
"""
import json
from types import SimpleNamespace

import pytest

from modulo_blockchain.registrar_custodia import (
    consultar_evidencia,
    registrar_e_verificar,
    verificar_integridade,
)

HASH = "a" * 64


class LedgerFalso:
    """Simula o peer CLI: guarda evidencias e responde invoke/query."""

    def __init__(self, ledger=None):
        self.ledger = dict(ledger or {})
        self.chamadas = []

    def __call__(self, cmd, env=None, capture_output=True, text=True):
        self.chamadas.append(cmd)
        corpo = json.loads(cmd[cmd.index("-c") + 1])
        funcao, args = corpo["function"], corpo["Args"]
        if cmd[2] == "invoke":
            self.ledger[args[0]] = {"id": args[0], "hash_sha256": args[1], "timestamp": args[2]}
            return SimpleNamespace(returncode=0, stdout="",
                                   stderr="Chaincode invoke successful. result: status:200")
        if funcao == "ConsultarEvidencia":
            if args[0] not in self.ledger:
                return SimpleNamespace(returncode=1, stdout="",
                                       stderr=f"evidência com ID '{args[0]}' não encontrada")
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.ledger[args[0]]), stderr="")
        if funcao == "VerificarIntegridade":
            original = self.ledger[args[0]]["hash_sha256"]
            return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps(
                {"hash_original": original, "hash_recalculado": args[1],
                 "integridade_valida": original == args[1]}))


def _registrar(runner, **kw):
    return registrar_e_verificar("evid-1", HASH, "2026-01-01T00:00:00+00:00",
                                 "aws", "local", "imagem", runner=runner, **kw)


def test_registra_e_confere_o_hash_gravado():
    runner = LedgerFalso()
    resultado = _registrar(runner)
    assert resultado["status"] == "success"
    assert resultado["acao"] == "registrada"
    assert resultado["hash_no_ledger"] == HASH
    assert runner.ledger["evid-1"]["hash_sha256"] == HASH


def test_hash_com_marcador_de_posicao_e_rejeitado_antes_de_gravar():
    """O erro do registro manual (marcador no lugar do hash) nao pode
    chegar ao ledger."""
    runner = LedgerFalso()
    with pytest.raises(ValueError):
        registrar_e_verificar("evid-1", "COLE_O_HASH_AQUI", "2026-01-01T00:00:00+00:00",
                              "aws", "local", "imagem", runner=runner)
    assert runner.chamadas == []


def test_registro_e_idempotente_quando_o_hash_confere():
    runner = LedgerFalso({"evid-1": {"hash_sha256": HASH}})
    resultado = _registrar(runner)
    assert resultado["acao"] == "ja_registrada"
    assert resultado["status"] == "success"
    assert all(c[2] == "query" for c in runner.chamadas)


def test_id_existente_com_hash_diferente_e_falha():
    runner = LedgerFalso({"evid-1": {"hash_sha256": "b" * 64}})
    resultado = _registrar(runner)
    assert resultado["status"] == "falha_hash_divergente"


def test_falha_do_peer_gera_erro_explicito():
    def runner(cmd, **kw):
        if cmd[2] == "query":
            return SimpleNamespace(returncode=1, stdout="", stderr="evidência com ID 'x' não encontrada")
        return SimpleNamespace(returncode=1, stdout="", stderr="endorsement failure")
    with pytest.raises(RuntimeError):
        _registrar(runner)


def test_consulta_de_id_inexistente_retorna_none():
    assert consultar_evidencia("nao-existe", runner=LedgerFalso()) is None


def test_verificar_integridade_detecta_hash_alterado():
    runner = LedgerFalso({"evid-1": {"hash_sha256": HASH}})
    assert verificar_integridade("evid-1", HASH, runner=runner)["integridade_valida"] is True
    assert verificar_integridade("evid-1", "c" * 64, runner=runner)["integridade_valida"] is False
