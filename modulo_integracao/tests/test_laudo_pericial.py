"""
Testes unitarios para o modulo de geracao de laudo pericial (RF12,
Tabela 10, PGT): "Gerar laudos periciais automaticos em PDF, contendo:
hashes, metadados, classificacoes IA com artefatos XAI e historico
blockchain."

Estrategia de teste: separa a logica de MONTAGEM do conteudo (testavel,
pura) da RENDERIZACAO do PDF (validada manualmente via reportlab,
excluida de cobertura - mesmo padrao das integracoes reais de modelo).
"""
import pytest

from modulo_integracao.laudo_pericial import montar_conteudo_laudo


def test_montar_conteudo_laudo_returns_expected_sections():
    """O laudo deve conter todas as secoes exigidas pelo RF12: hash,
    metadados, classificacao IA, artefatos XAI e historico blockchain."""
    conteudo = montar_conteudo_laudo(
        evidencia={
            "bucket": "ccf-evidence-bucket",
            "key": "evidencia-teste.jpg",
            "cloud_provider": "aws",
            "hashes": {"sha256": "abc123", "md5": "def456"},
            "collected_at": "2026-07-22T10:00:00+00:00",
        },
        classificacao={"probabilidade_nsfw": 0.95, "flag": "NSFW"},
        xai_info={"metodo": "LIME", "regioes_relevantes": 3},
        historico_blockchain={"tx_id": "tx-001", "status": "success"},
        cenario="C1",
    )

    assert "hash" in conteudo
    assert "metadados" in conteudo
    assert "classificacao_ia" in conteudo
    assert "artefatos_xai" in conteudo
    assert "historico_blockchain" in conteudo
    assert "cenario" in conteudo


def test_montar_conteudo_laudo_includes_correct_hash():
    """O hash exibido no laudo deve ser exatamente o hash SHA-256 da
    evidencia coletada - integridade referencial do laudo (RNF01)."""
    conteudo = montar_conteudo_laudo(
        evidencia={
            "bucket": "b", "key": "k", "cloud_provider": "aws",
            "hashes": {"sha256": "hash-real-da-evidencia", "md5": "m"},
            "collected_at": "2026-07-22T10:00:00+00:00",
        },
        classificacao={"probabilidade_nsfw": 0.1, "flag": "SFW"},
        xai_info=None,
        historico_blockchain=None,
        cenario="C1",
    )

    assert conteudo["hash"]["sha256"] == "hash-real-da-evidencia"


def test_montar_conteudo_laudo_handles_missing_xai_gracefully():
    """Ausencia de artefatos XAI (ex: conteudo SFW, sem necessidade de
    explicacao) nao deve quebrar o laudo - deve indicar explicitamente
    que XAI nao foi gerado, nao omitir silenciosamente."""
    conteudo = montar_conteudo_laudo(
        evidencia={
            "bucket": "b", "key": "k", "cloud_provider": "aws",
            "hashes": {"sha256": "h", "md5": "m"},
            "collected_at": "2026-07-22T10:00:00+00:00",
        },
        classificacao={"probabilidade_nsfw": 0.05, "flag": "SFW"},
        xai_info=None,
        historico_blockchain=None,
        cenario="C1",
    )

    assert conteudo["artefatos_xai"] == "Nao aplicavel - conteudo classificado como SFW"


def test_montar_conteudo_laudo_requires_valid_cenario():
    """Apenas os cenarios C1, C2 ou C3 (Tabela 16, PGT) sao validos -
    protege contra referencia a um cenario inexistente no laudo."""
    with pytest.raises(ValueError):
        montar_conteudo_laudo(
            evidencia={"bucket": "b", "key": "k", "cloud_provider": "aws",
                       "hashes": {"sha256": "h", "md5": "m"}, "collected_at": "x"},
            classificacao={"flag": "SFW"},
            xai_info=None,
            historico_blockchain=None,
            cenario="C99",
        )

def test_montar_xai_texto_traz_metodo_escore_limiar_e_trechos():
    """Conversa sinalizada gera artefato com os trechos que embasaram a
    decisao, o escore e o limiar (secao 4.4.6 do PGT)."""
    from modulo_integracao.laudo_pericial import montar_xai_texto

    artefato = montar_xai_texto(
        {"score_grooming": 0.62, "flag": "SUSPEITO", "trechos_relevantes": ["m1", "m2"]},
        limiar=0.4,
    )
    assert artefato["metodo"].startswith("Oclusao")
    assert artefato["escore"] == 0.62 and artefato["limiar"] == 0.4
    assert artefato["trechos_relevantes"] == ["m1", "m2"]


def test_montar_xai_texto_sem_sinalizacao_retorna_none():
    """Conversa nao sinalizada nao tem o que explicar."""
    from modulo_integracao.laudo_pericial import montar_xai_texto

    assert montar_xai_texto({"score_grooming": 0.1, "flag": "NORMAL", "trechos_relevantes": []}) is None


def _evidencia_minima():
    return {
        "bucket": "b", "key": "k", "cloud_provider": "aws",
        "collected_at": "2026-01-01T00:00:00+00:00",
        "hashes": {"sha256": "a" * 64, "md5": "b" * 32},
    }


def test_laudo_sem_classificacao_nao_afirma_classificacao_inexistente():
    """Cenario sem etapa de IA (ex.: C3) nao pode constar como
    'classificado como SFW': o laudo deve declarar que a classificacao
    nao foi executada."""
    from modulo_integracao.laudo_pericial import montar_conteudo_laudo

    conteudo = montar_conteudo_laudo(
        evidencia=_evidencia_minima(),
        classificacao={"observacao": "correlacao multi-nuvem"},
        xai_info=None,
        historico_blockchain={"status": "success"},
        cenario="C3",
    )
    assert "SFW" not in conteudo["artefatos_xai"]
    assert "nao executada" in conteudo["artefatos_xai"]


def test_laudo_conteudo_sinalizado_sem_artefato_nao_diz_nao_aplicavel():
    """Conteudo sinalizado sem artefato de explicacao deve constar como
    explicacao nao gerada, e nao como 'nao aplicavel'."""
    from modulo_integracao.laudo_pericial import montar_conteudo_laudo

    conteudo = montar_conteudo_laudo(
        evidencia=_evidencia_minima(),
        classificacao={"flag": "SUSPEITO", "score_grooming": 0.9},
        xai_info=None,
        historico_blockchain=None,
        cenario="C2",
    )
    assert "nao gerado" in conteudo["artefatos_xai"]
    assert "SUSPEITO" in conteudo["artefatos_xai"]
    assert "benigno" not in conteudo["historico_blockchain"]


def test_laudo_conteudo_normal_e_tratado_como_benigno():
    """Flag NORMAL (texto) segue a mesma regra do SFW (imagem)."""
    from modulo_integracao.laudo_pericial import montar_conteudo_laudo

    conteudo = montar_conteudo_laudo(
        evidencia=_evidencia_minima(),
        classificacao={"flag": "NORMAL", "score_grooming": 0.05},
        xai_info=None,
        historico_blockchain=None,
        cenario="C2",
    )
    assert conteudo["artefatos_xai"] == "Nao aplicavel - conteudo classificado como NORMAL"
