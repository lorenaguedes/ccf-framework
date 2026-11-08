"""
Testes dos laudos de C1 e C3: o conteudo deve refletir exatamente o que o
log registra, sem afirmar classificacao que nao ocorreu.
"""
import json

import pytest

from modulo_integracao.cenarios_simulacao.gerar_laudos_c1_c3 import (
    conteudo_laudo_c1,
    conteudo_laudo_consolidado_c3,
    conteudos_laudo_c3,
)
from modulo_integracao.laudo_pericial import montar_conteudo_laudo_consolidado

H_AWS, H_GCP, H_AZ = "a" * 64, "b" * 64, "c" * 64


def _ev(provedor, h):
    return {"cloud_provider": provedor, "bucket": "b", "key": "k.jpg",
            "collected_at": "2026-01-01T00:00:00+00:00",
            "hashes": {"sha256": h, "md5": "d" * 32}}


def _log(tmp_path, resultado):
    caminho = tmp_path / "log.json"
    caminho.write_text(json.dumps({"resultado": resultado}), encoding="utf-8")
    return caminho


def test_laudo_c3_nao_afirma_classificacao_e_inclui_verificacao(tmp_path):
    log = _log(tmp_path, {
        "evidencias": [_ev("aws", H_AWS), _ev("gcp", H_GCP), _ev("azure", H_AZ)],
        "registros_custodia": [
            {"status": "success", "evidence_id": f"e{i}", "hash": h}
            for i, h in enumerate((H_AWS, H_GCP, H_AZ))
        ],
        "verificacoes_integridade": [
            {"cloud_provider": p, "hash_original": h, "hash_recalculado": h, "integridade_valida": True}
            for p, h in (("aws", H_AWS), ("gcp", H_GCP), ("azure", H_AZ))
        ],
    })
    conteudos = conteudos_laudo_c3(log)
    assert set(conteudos) == {"aws", "gcp", "azure"}
    aws = conteudos["aws"]
    assert "SFW" not in str(aws["artefatos_xai"])
    assert "nao executada" in aws["artefatos_xai"]
    assert aws["classificacao_ia"]["classificacao_executada"] is False
    assert aws["historico_blockchain"]["evidence_id"] == "e0"
    assert aws["historico_blockchain"]["verificacao_integridade"]["integridade_valida"] is True


def test_laudo_c1_sfw_sem_registro_consta_como_benigno(tmp_path):
    log = _log(tmp_path, {
        "coleta": _ev("aws", H_AWS),
        "classificacao": {"probabilidade_nsfw": 0.08, "flag": "SFW"},
        "registro_custodia": None,
    })
    cpath = tmp_path / "log.json"
    conteudo = conteudo_laudo_c1(cpath)
    assert conteudo["artefatos_xai"] == "Nao aplicavel - conteudo classificado como SFW"
    assert "benigno" in conteudo["historico_blockchain"]


def test_laudo_c1_com_classificador_forcado_declara_o_forcamento(tmp_path):
    log = _log(tmp_path, {
        "coleta": _ev("aws", H_AWS),
        "classificacao": {"probabilidade_nsfw": 0.08, "flag": "NSFW",
                          "flag_original": "SFW", "classificador_forcado": True},
        "registro_custodia": {"status": "success", "evidence_id": "e1", "hash": H_AWS},
        "verificacao_integridade": {"hash_original": H_AWS, "hash_recalculado": H_AWS,
                                    "integridade_valida": True},
    })
    conteudo = conteudo_laudo_c1(log)
    assert conteudo["classificacao_ia"]["classificador_forcado"] is True
    assert "nao gerado" in conteudo["artefatos_xai"]
    assert conteudo["historico_blockchain"]["verificacao_integridade"]["integridade_valida"] is True


def _log_c3_completo(tmp_path, registrar_gcp=True):
    registros = [{"status": "success", "evidence_id": "e-aws", "hash": H_AWS},
                 {"status": "success", "evidence_id": "e-az", "hash": H_AZ}]
    if registrar_gcp:
        registros.insert(1, {"status": "success", "evidence_id": "e-gcp", "hash": H_GCP})
    return _log(tmp_path, {
        "evidencias": [_ev("aws", H_AWS), _ev("gcp", H_GCP), _ev("azure", H_AZ)],
        "registros_custodia": registros,
        "correlacao": {"total_csps_envolvidos": 3, "providers_presentes": ["aws", "azure", "gcp"]},
        "verificacoes_integridade": [
            {"cloud_provider": p, "hash_original": h, "hash_recalculado": h, "integridade_valida": True}
            for p, h in (("aws", H_AWS), ("gcp", H_GCP), ("azure", H_AZ))
        ],
    })


def test_laudo_consolidado_c3_correlaciona_os_tres_provedores_em_uma_peca(tmp_path):
    """Criterio de sucesso do C3: evidencias de 3 CSPs no mesmo laudo."""
    c = conteudo_laudo_consolidado_c3(_log_c3_completo(tmp_path))
    assert c["cenario"] == "C3"
    assert c["correlacao"]["total_csps_envolvidos"] == 3
    assert [e["cloud_provider"] for e in c["evidencias"]] == ["aws", "gcp", "azure"]
    assert [e["hash"]["sha256"] for e in c["evidencias"]] == [H_AWS, H_GCP, H_AZ]
    assert "nao executada" in c["classificacao_ia"]
    assert "SFW" not in str(c)
    gcp = c["evidencias"][1]["historico_blockchain"]
    assert gcp["evidence_id"] == "e-gcp"
    assert gcp["verificacao_integridade"]["integridade_valida"] is True


def test_laudo_consolidado_declara_evidencia_nao_registrada(tmp_path):
    c = conteudo_laudo_consolidado_c3(_log_c3_completo(tmp_path, registrar_gcp=False))
    gcp = next(e for e in c["evidencias"] if e["cloud_provider"] == "gcp")
    assert "nao registrada" in gcp["historico_blockchain"]


def test_laudo_consolidado_rejeita_entradas_invalidas():
    with pytest.raises(ValueError):
        montar_conteudo_laudo_consolidado([], {}, {}, cenario="C3")
    with pytest.raises(ValueError):
        montar_conteudo_laudo_consolidado([_ev("aws", H_AWS)], {}, {}, cenario="C9")
