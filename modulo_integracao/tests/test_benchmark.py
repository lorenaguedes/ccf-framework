"""Testes do benchmark com provedores falsos (sem emuladores nem Fabric)."""
import hashlib

import pytest

from modulo_integracao import benchmark as b


def _provedor_fiel():
    guardado = {}

    def gravar(k, d):
        guardado[k] = d

    def coletar(k):
        d = guardado[k]
        return {"hashes": {"sha256": hashlib.sha256(d).hexdigest()}, "size_bytes": len(d)}
    return gravar, coletar


def test_conteudo_deterministico_e_tamanho_variavel():
    assert b.gerar_conteudo(5) == b.gerar_conteudo(5)
    assert b.gerar_conteudo(5) != b.gerar_conteudo(6)
    assert 1024 <= len(b.gerar_conteudo(7)) <= 256 * 1024


def test_coletas_integras_em_rodizio_entre_provedores():
    r = b.executar_coletas(30, {"aws": _provedor_fiel(), "azure": _provedor_fiel(), "gcp": _provedor_fiel()})
    assert r["global"]["integras"] == 30 and r["global"]["taxa_integridade"] == 1.0
    assert {k: v["coletas"] for k, v in r["por_provedor"].items()} == {"aws": 10, "azure": 10, "gcp": 10}
    assert r["falhas"] == []


def test_hash_divergente_e_detectado_e_contado():
    g, c = _provedor_fiel()

    def coletar_corrompido(k):
        out = c(k)
        if k.endswith("0003.bin"):
            out["hashes"]["sha256"] = "0" * 64
        return out
    r = b.executar_coletas(10, {"aws": (g, coletar_corrompido)})
    assert r["global"]["integras"] == 9 and r["falhas"][0]["status"] == "hash_divergente"


def test_excecao_de_coleta_nao_e_silenciada():
    def coletar(k):
        raise ConnectionError("emulador fora do ar")
    r = b.executar_coletas(4, {"aws": (lambda k, d: None, coletar)})
    assert r["global"]["integras"] == 0 and r["falhas"][0]["status"] == "erro"
    assert "ConnectionError" in r["falhas"][0]["motivo"]


def test_wilson_com_mil_sem_falhas_nao_prova_99_9():
    lo, hi = b.wilson(1000, 1000)
    assert lo < 0.999 and hi == 1.0


def test_percentil_posto_mais_proximo():
    assert b.percentil([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5
    assert b.percentil([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    assert b.percentil([], 50) is None


def test_fabric_latencias_e_falhas():
    t = iter(x * 0.5 for x in range(1000))

    def registrar(eid, h):
        if eid.endswith("0002"):
            raise RuntimeError("falha")
        return {"status": "success", "acao": "registrada"}
    r = b.executar_fabric(5, registrar, "x", relogio=lambda: next(t))
    assert r["confirmadas"] == 4 and r["falhas"] == 1 and r["p50_s"] == 0.5
    assert r["falhas_detalhe"][0]["evidence_id"] == "evid-bench-x-0002"


def test_fabric_ja_registrada_nao_conta_como_confirmada():
    r = b.executar_fabric(2, lambda e, h: {"status": "success", "acao": "ja_registrada"}, "y")
    assert r["confirmadas"] == 0
