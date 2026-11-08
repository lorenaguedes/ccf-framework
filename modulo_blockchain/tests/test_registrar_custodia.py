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


def test_invoke_nao_envia_o_agente_coletor():
    """A autoria vem do certificado que assina a transacao (MSP do
    chamador), por isso o invoke leva exatamente 6 argumentos."""
    runner = LedgerFalso()
    _registrar(runner)
    invoke = next(c for c in runner.chamadas if c[2] == "invoke")
    args = json.loads(invoke[invoke.index("-c") + 1])["Args"]
    assert args == ["evid-1", HASH, "2026-01-01T00:00:00+00:00", "aws", "local", "imagem"]


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


def test_registra_quando_peer_devolve_erro_com_acentos_em_octal():
    """Saida real do peer CLI: 'evid\\303\\252ncia ... n\\303\\243o encontrada'.
    Regressao: o cliente tratava essa resposta como falha em vez de
    'ainda nao registrada' (observado em C1 forcado e C3, 08/11/2026)."""
    class PeerReal(LedgerFalso):
        def __call__(self, cmd, **kw):
            r = super().__call__(cmd, **kw)
            if r.returncode != 0 and "encontrada" in r.stderr:
                r.stderr = ("Error: endorsement failure during query. response: status:500 "
                            "message:\"evid\\303\\252ncia com ID 'evid-1' n\\303\\243o encontrada\"")
            return r

    runner = PeerReal()
    resultado = _registrar(runner)
    assert resultado["status"] == "success"
    assert resultado["acao"] == "registrada"


def test_aguarda_confirmacao_do_bloco_apos_o_invoke():
    """Regressao: o invoke retorna antes da confirmacao do bloco; a
    evidencia so fica visivel na consulta alguns instantes depois
    (observado em C1 forcado e C3, 08/11/2026)."""
    class Atrasado(LedgerFalso):
        def __init__(self):
            super().__init__()
            self.consultas_apos_invoke = 0
            self.invocado = False

        def __call__(self, cmd, **kw):
            if cmd[2] == "invoke":
                self.invocado = True
                self.chamadas.append(cmd)
                corpo = json.loads(cmd[cmd.index("-c") + 1])
                self.pendente = corpo["Args"]
                return SimpleNamespace(returncode=0, stdout="",
                                       stderr="Chaincode invoke successful. result: status:200")
            if self.invocado and cmd[2] == "query":
                self.consultas_apos_invoke += 1
                if self.consultas_apos_invoke == 3:  # confirma na 3a consulta
                    a = self.pendente
                    self.ledger[a[0]] = {"id": a[0], "hash_sha256": a[1], "timestamp": a[2]}
            return super().__call__(cmd, **kw)

    runner = Atrasado()
    pausas = []
    resultado = _registrar(runner, dormir=pausas.append)
    assert resultado["status"] == "success"
    assert resultado["acao"] == "registrada"
    assert runner.consultas_apos_invoke == 3
    assert len(pausas) == 2


def test_falha_explicita_se_o_bloco_nunca_confirma():
    class Nunca(LedgerFalso):
        def __call__(self, cmd, **kw):
            if cmd[2] == "invoke":
                return SimpleNamespace(returncode=0, stdout="",
                                       stderr="Chaincode invoke successful. result: status:200")
            return super().__call__(cmd, **kw)

    with pytest.raises(RuntimeError, match="nao confirmada"):
        _registrar(Nunca(), tentativas_confirmacao=3, intervalo_confirmacao=0, dormir=lambda s: None)


def test_decodifica_octal_utf8():
    from modulo_blockchain.registrar_custodia import _decodificar_octal
    assert _decodificar_octal("n\\303\\243o evid\\303\\252ncia") == "não evidência"
    assert _decodificar_octal("sem escapes") == "sem escapes"


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


def test_rede_fora_do_ar_gera_mensagem_orientativa():
    """Peer inacessivel deve gerar erro que orienta a subir a rede, e nao
    um erro opaco do peer CLI."""
    def runner(cmd, **kw):
        return SimpleNamespace(returncode=1, stdout="", stderr="dial tcp 127.0.0.1:7051: connect: connection refused")
    with pytest.raises(RuntimeError, match="rede Hyperledger Fabric inacessivel"):
        _registrar(runner)
