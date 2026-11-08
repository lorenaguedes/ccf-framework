"""
Testes do laudo de caso multimodal (C4): o conteudo deve refletir o que
cada estagio retornou, sem afirmar o que nao ocorreu.
"""
import pytest

from modulo_integracao.cenarios_simulacao.cenario_c4 import executar_cenario_c4
from modulo_integracao.laudo_pericial import montar_conteudo_laudo_caso


def _coleta(provedor, h, ident):
    return {"cloud_provider": provedor, "hashes": {"sha256": h * 64, "md5": "d" * 32},
            "collected_at": "2026-11-08T04:00:00+00:00", "bucket": "b", "blob_name": ident}


def _caso(e1="MATCH", e4="SUSPEITO", e5="NORMAL", custodia=None, simulada=False):
    def triagem(img):
        r = {"flag": e1, "matched_id": "ref", "score_similaridade": 0.99}
        if simulada:
            r["base_referencia_simulada"] = True
        return r

    return executar_cenario_c4(
        coletar_imagem=lambda: (_coleta("aws", "a", "img.jpg"), "IMG"),
        coletar_texto=lambda: (_coleta("azure", "b", "conversa.txt"), ["m1"]),
        coletar_logs=lambda: (_coleta("gcp", "c", "log.csv"), "REG"),
        triagem_fn=triagem,
        explicito_fn=lambda i: {"flag": "SFW", "probabilidade_nsfw": 0.01},
        idade_fn=lambda i: {"flag": "ADULTO", "idade_estimada": 30.0},
        grooming_fn=lambda m: {"flag": e4, "score_grooming": 0.87,
                               "trechos_relevantes": ["segredo entre nos"]},
        anomalias_fn=lambda r: {"flag": e5, "n_registros": 8, "n_anomalos": 2},
        custody_register_fn=custodia or (lambda eid, h, meta: {
            "status": "success", "evidence_id": f"evid-{meta['modalidade']}", "acao": "registrada",
            "hash": h}),
    )


def _por_modalidade(c, m):
    return next(e for e in c["evidencias"] if e["modalidade"] == m)


def test_laudo_traz_avaliacao_evidencias_e_declaracoes():
    c = montar_conteudo_laudo_caso(_caso(), limiar_e4=0.3997,
                                   declaracoes=["Base de referencia do E1 simulada."])
    assert c["cenario"] == "C4"
    assert c["avaliacao_caso"]["prioridade"] == "ALTA"
    assert [e["modalidade"] for e in c["evidencias"]] == ["imagem", "texto", "logs"]
    assert c["declaracoes"] == ["Base de referencia do E1 simulada."]


def test_explicacao_so_existe_para_texto_com_indicio():
    c = montar_conteudo_laudo_caso(_caso(), limiar_e4=0.3997)
    texto = _por_modalidade(c, "texto")["artefatos_xai"]
    assert texto["metodo"].startswith("Oclusao por mensagem")
    assert texto["limiar"] == 0.3997 and texto["trechos_relevantes"] == ["segredo entre nos"]
    # imagem com indicio (E1 MATCH): nao ha explicacao nesta modalidade
    assert "nao gerado para esta modalidade" in _por_modalidade(c, "imagem")["artefatos_xai"]
    # logs sem indicio: nao aplicavel
    assert "sem indicio" in _por_modalidade(c, "logs")["artefatos_xai"]


def test_estados_da_custodia_sem_afirmar_registro_inexistente():
    def custodia_falha_no_texto(eid, h, meta):
        if meta["modalidade"] == "texto":
            raise RuntimeError("rede Fabric inacessivel")
        return {"status": "success", "evidence_id": "e", "acao": "registrada"}
    c = montar_conteudo_laudo_caso(_caso(custodia=custodia_falha_no_texto))
    assert isinstance(_por_modalidade(c, "imagem")["historico_blockchain"], dict)
    assert "Falha no registro" in _por_modalidade(c, "texto")["historico_blockchain"]
    assert "sem indicio" in _por_modalidade(c, "logs")["historico_blockchain"]


def test_estagio_nao_executado_consta_como_tal_e_nao_como_resultado():
    c = montar_conteudo_laudo_caso(_caso())
    linhas = _por_modalidade(c, "imagem")["estagios"]
    e3 = next(linha for linha in linhas if linha.startswith("E3"))
    assert "nao executado" in e3
    assert "ADULTO" not in e3  # nao afirma uma classificacao de idade que nao ocorreu


def test_referencia_simulada_e_declarada_no_resumo_do_estagio():
    c = montar_conteudo_laudo_caso(_caso(simulada=True))
    e1 = next(linha for linha in _por_modalidade(c, "imagem")["estagios"] if linha.startswith("E1"))
    assert "referencia SIMULADA" in e1


def test_indicios_de_cada_evidencia_acompanham_o_laudo():
    c = montar_conteudo_laudo_caso(_caso(e5="ANOMALO"))
    assert _por_modalidade(c, "logs")["indicios"][0]["forca"] == "contextual"
    assert _por_modalidade(c, "imagem")["indicios"][0]["forca"] == "forte"


def test_caso_sem_avaliacao_nao_gera_laudo():
    def falha():
        raise ConnectionError("fora do ar")
    r = executar_cenario_c4(
        coletar_imagem=falha, coletar_texto=falha, coletar_logs=falha,
        triagem_fn=None, explicito_fn=None, idade_fn=None, grooming_fn=None,
        anomalias_fn=None, custody_register_fn=None)
    with pytest.raises(ValueError, match="sem avaliacao"):
        montar_conteudo_laudo_caso(r)


def test_cenario_invalido_e_rejeitado():
    with pytest.raises(ValueError):
        montar_conteudo_laudo_caso(_caso(), cenario="C99")
