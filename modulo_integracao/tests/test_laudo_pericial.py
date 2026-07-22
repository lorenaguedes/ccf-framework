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