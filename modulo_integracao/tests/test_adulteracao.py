"""
Testes do teste negativo de integridade (adulteracao), com storage,
coleta e ledger simulados: a logica de decisao e verificada sem rede.
"""
import hashlib

import pytest

from modulo_integracao.cenarios_simulacao.executar_adulteracao_real import (
    adulterar_um_byte,
    executar_teste_adulteracao,
)


class Ambiente:
    """Storage, coletor e ledger em memoria."""

    def __init__(self, conteudo=b"evidencia-sintetica-0123456789"):
        self.objetos = {"orig": conteudo}
        self.ledger = {}

    def ler(self, key):
        return self.objetos[key]

    def gravar(self, key, dados):
        self.objetos[key] = dados

    def coletar(self, key):
        return {"cloud_provider": "aws", "collected_at": "2026-11-08T04:00:00+00:00",
                "hashes": {"sha256": hashlib.sha256(self.objetos[key]).hexdigest()}}

    def registrar(self, eid, hash_sha256, ts):
        self.ledger.setdefault(eid, hash_sha256)
        return {"status": "success", "evidence_id": eid}

    def verificar(self, eid, hash_recalculado):
        return {"evidencia_id": eid, "hash_original": self.ledger[eid],
                "hash_recalculado": hash_recalculado,
                "integridade_valida": self.ledger[eid] == hash_recalculado}


def _executar(amb, **kw):
    return executar_teste_adulteracao(
        ler=amb.ler, gravar=amb.gravar, coletar=amb.coletar, registrar=amb.registrar,
        verificar=amb.verificar, key="orig", key_adulterada="copia", **kw)


def test_adulteracao_de_um_byte_e_detectada_e_controle_passa():
    amb = Ambiente()
    r = _executar(amb)
    assert r["status_teste"] == "SUCESSO"
    assert r["controle_ok"] and r["adulteracao_detectada"]
    assert r["verificacao_controle"]["integridade_valida"] is True
    assert r["verificacao_adulterada"]["integridade_valida"] is False
    assert r["hash_adulterado"] != r["hash_original"]


def test_objeto_original_nunca_e_modificado():
    amb = Ambiente()
    original = amb.objetos["orig"]
    _executar(amb)
    assert amb.objetos["orig"] == original
    assert amb.objetos["copia"] != original


def test_adulteracao_altera_exatamente_um_byte():
    dados = bytes(range(32))
    novo, det = adulterar_um_byte(dados)
    diferencas = [i for i in range(len(dados)) if dados[i] != novo[i]]
    assert diferencas == [det["deslocamento"]]
    assert det["byte_antes"] ^ det["byte_depois"] == 1


def test_conteudo_vazio_nao_pode_ser_adulterado():
    with pytest.raises(ValueError):
        adulterar_um_byte(b"")


def test_falha_se_o_verificador_nao_detectar_a_adulteracao():
    """Se o ledger aprovasse a copia adulterada, o teste deve FALHAR."""
    amb = Ambiente()
    amb.verificar = lambda eid, h: {"integridade_valida": True}
    r = _executar(amb)
    assert r["status_teste"] == "FALHA"
    assert r["adulteracao_detectada"] is False


def test_falha_se_o_registro_de_custodia_falhar():
    amb = Ambiente()
    amb.registrar = lambda eid, h, ts: {"status": "falha_hash_divergente"}
    with pytest.raises(RuntimeError):
        _executar(amb)
