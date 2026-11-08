"""Testes do cenario de custodia completa (H2) com o contrato simulado em memoria."""
import pytest

from modulo_integracao.cenarios_simulacao.executar_custodia_completa_real import executar_cenario_custodia

HASH = "c" * 64
EVIDENCIA = {"cloud_provider": "aws", "collected_at": "2026-11-08T06:00:00+00:00", "hashes": {"sha256": HASH}}


class ContratoFalso:
    """Reproduz as regras do contrato: so o custodiante transfere; nao ha autotransferencia."""

    def __init__(self, hash_recoleta=HASH, quebra_encadeamento=False, ts=("2026-11-08T06:00:01.5Z", "2026-11-08T06:00:09.25Z")):
        self.ev, self.hash_recoleta, self.quebra, self.ts = None, hash_recoleta, quebra_encadeamento, list(ts)

    def coletar(self):
        return {**EVIDENCIA, "hashes": {"sha256": self.hash_recoleta if self.ev else HASH}}

    def registrar(self, eid, h, ts):
        self.ev = {"id": eid, "hash_sha256": h, "agente_coletor_msp": "Org1MSP",
                   "custodiante_atual": "Org1MSP", "historico_transferencias": []}
        return {"status": "success", "acao": "registrada"}

    def transferir(self, eid, msp, motivo, org):
        chamador = f"Org{org}MSP"
        if chamador != self.ev["custodiante_atual"]:
            raise RuntimeError("transferência não autorizada: o custodiante atual é outro")
        if msp == self.ev["custodiante_atual"]:
            raise RuntimeError("o cessionário já é o custodiante atual")
        ced = "OrgXMSP" if (self.quebra and self.ev["historico_transferencias"]) else chamador
        self.ev["historico_transferencias"].append({
            "msp_cedente": ced, "msp_cessionario": msp, "motivacao": motivo,
            "timestamp": self.ts[len(self.ev["historico_transferencias"])]})
        self.ev["custodiante_atual"] = msp
        return {"status": "success", "custodiante_atual": msp,
                "n_transferencias": len(self.ev["historico_transferencias"]), "latencia_confirmacao_s": 2.0}

    def consultar(self, eid):
        return self.ev

    def verificar(self, eid, h):
        return {"integridade_valida": h == self.ev["hash_sha256"],
                "historico_transferencias": self.ev["historico_transferencias"]}


def _rodar(c):
    return executar_cenario_custodia(coletar=c.coletar, registrar=c.registrar, transferir=c.transferir,
                                     consultar=c.consultar, verificar=c.verificar, sufixo="t1")


def test_cenario_completo_sucesso():
    r = _rodar(ContratoFalso())
    assert r["status_cenario"] == "SUCESSO" and r["n_verificacoes_ok"] == r["n_verificacoes"] == 6
    assert [t["msp_cessionario"] for t in r["cadeia_reconstituida"]] == ["Org2MSP", "Org1MSP"]
    assert r["evidence_id"] == f"evid-custodia-aws-{HASH[:12]}-t1"
    assert set(r["latencias_confirmacao"]) == {"registro_s", "transferencia_org1_para_org2_s", "transferencia_org2_para_org1_s"}


def test_falha_se_o_contrato_aceitar_transferencia_indevida():
    c = ContratoFalso()
    original = c.transferir

    def permissivo(eid, msp, motivo, org):
        try:
            return original(eid, msp, motivo, org)
        except RuntimeError:
            return {"status": "success", "custodiante_atual": msp, "n_transferencias": 99, "latencia_confirmacao_s": 0}
    c.transferir = permissivo
    r = _rodar(c)
    assert r["status_cenario"] == "FALHA"
    assert {v["id"]: v["ok"] for v in r["verificacoes"]}["V3"] is False


def test_falha_se_o_hash_recoletado_diverge():
    r = _rodar(ContratoFalso(hash_recoleta="d" * 64))
    assert r["status_cenario"] == "FALHA"
    assert {v["id"]: v["ok"] for v in r["verificacoes"]}["V6"] is False


def test_falha_se_a_cadeia_nao_encadeia():
    r = _rodar(ContratoFalso(quebra_encadeamento=True))
    assert r["status_cenario"] == "FALHA"


def test_falha_se_os_instantes_decrescem():
    r = _rodar(ContratoFalso(ts=("2026-11-08T06:00:09Z", "2026-11-08T06:00:01Z")))
    assert r["status_cenario"] == "FALHA"


def test_erro_inesperado_na_transferencia_propaga():
    c = ContratoFalso()
    c.transferir = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("rede fora do ar"))
    with pytest.raises(RuntimeError, match="rede fora do ar"):
        _rodar(c)
