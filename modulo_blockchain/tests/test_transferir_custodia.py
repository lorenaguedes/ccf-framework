"""Testes do cliente de transferencia de custodia, com o peer CLI e o contrato simulados."""
import json
from types import SimpleNamespace

import pytest

from modulo_blockchain.registrar_custodia import ambiente_peer, transferir_custodia

HASH = "b" * 64


class RedeFalsa:
    """Simula o contrato: so o custodiante atual (MSP do ambiente) transfere."""

    def __init__(self, custodiante="Org1MSP", confirma_apos=0):
        self.ev = {"id": "e1", "hash_sha256": HASH, "custodiante_atual": custodiante,
                   "historico_transferencias": []}
        self.pendente, self.confirma_apos, self.consultas, self.orgs = None, confirma_apos, 0, []

    def __call__(self, cmd, env=None, capture_output=True, text=True):
        corpo = json.loads(cmd[cmd.index("-c") + 1])
        if cmd[2] == "invoke":
            msp = env["CORE_PEER_LOCALMSPID"]
            self.orgs.append(msp)
            _, cessionario, motivo = corpo["Args"]
            if msp != self.ev["custodiante_atual"]:
                return SimpleNamespace(returncode=1, stdout="", stderr=(
                    "Error: endorsement failure: message:\"transfer\\303\\252ncia n\\303\\243o autorizada: "
                    f"o custodiante atual \\303\\251 '{self.ev['custodiante_atual']}'\""))
            self.pendente = (msp, cessionario, motivo)
            return SimpleNamespace(returncode=0, stdout="", stderr="Chaincode invoke successful. result: status:200")
        self.consultas += 1
        if self.pendente and self.consultas > self.confirma_apos + 1:
            ced, ces, mot = self.pendente
            self.ev["historico_transferencias"].append({"msp_cedente": ced, "msp_cessionario": ces, "motivacao": mot})
            self.ev["custodiante_atual"], self.pendente = ces, None
        return SimpleNamespace(returncode=0, stdout=json.dumps(self.ev), stderr="")


def _t(rede, **kw):
    return transferir_custodia("e1", "Org2MSP", "motivo", runner=rede, dormir=lambda s: None, **kw)


def test_transfere_com_identidade_da_org_e_confirma():
    rede = RedeFalsa()
    r = _t(rede, org=1)
    assert r["status"] == "success" and r["custodiante_atual"] == "Org2MSP" and r["n_transferencias"] == 1
    assert rede.orgs == ["Org1MSP"]


def test_usa_identidade_da_org2():
    rede = RedeFalsa(custodiante="Org2MSP")
    _t(rede, org=2)
    assert rede.orgs == ["Org2MSP"]


def test_espera_a_confirmacao_do_bloco():
    rede = RedeFalsa(confirma_apos=3)
    assert _t(rede, org=1)["n_transferencias"] == 1
    assert rede.consultas > 3


def test_rejeicao_do_contrato_vira_erro_com_mensagem_decodificada():
    rede = RedeFalsa(custodiante="Org2MSP")
    with pytest.raises(RuntimeError, match="não autorizada"):
        _t(rede, org=1)


def test_nao_confirmada_no_prazo():
    rede = RedeFalsa(confirma_apos=99)
    with pytest.raises(RuntimeError, match="nao confirmada"):
        _t(rede, org=1, tentativas_confirmacao=3)


def test_campos_obrigatorios():
    with pytest.raises(ValueError):
        transferir_custodia("e1", "", "motivo", runner=RedeFalsa())


def test_evidencia_inexistente():
    class Vazia:
        def __call__(self, cmd, **kw):
            return SimpleNamespace(returncode=1, stdout="", stderr="evidência com ID 'e1' não encontrada")
    with pytest.raises(RuntimeError, match="nao encontrada"):
        transferir_custodia("e1", "Org2MSP", "m", runner=Vazia())


def test_ambientes_das_duas_orgs_diferem():
    e1, e2 = ambiente_peer(org=1), ambiente_peer(org=2)
    assert e1["CORE_PEER_LOCALMSPID"] == "Org1MSP" and e2["CORE_PEER_LOCALMSPID"] == "Org2MSP"
    assert e1["CORE_PEER_ADDRESS"].endswith("7051") and e2["CORE_PEER_ADDRESS"].endswith("9051")
    assert "org2.example.com" in e2["CORE_PEER_MSPCONFIGPATH"]
