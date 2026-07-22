"""
Teste do orquestrador do Cenario C1 - Distribuicao de CSAM em Storage
S3 (Tabela 16, PGT).

Modulos exercitados: Coleta -> Hash Perceptual -> CNN -> XAI -> Blockchain

Estrategia de teste: a funcao orquestradora recebe cada componente
(coletor, classificador, registrador de custodia) por injecao de
dependencia, permitindo validar a LOGICA DE ORQUESTRACAO com
componentes sinteticos - sem depender de LocalStack ou da rede Fabric
rodando durante o desenvolvimento local. A validacao com a
infraestrutura real ocorre separadamente (execucao manual documentada).
"""
import pytest

from modulo_integracao.cenarios_simulacao.cenario_c1 import executar_cenario_c1


def _collector_fn_sucesso(bucket, key):
    """Simula uma coleta bem-sucedida do modulo_coleta."""
    return {
        "bucket": bucket,
        "key": key,
        "cloud_provider": "aws",
        "hashes": {"sha256": "abc123", "md5": "def456"},
        "size_bytes": 1024,
        "collected_at": "2026-07-22T10:00:00+00:00",
    }


def _classifier_fn_explicito(conteudo):
    """Simula uma classificacao positiva de conteudo explicito."""
    return {"probabilidade_nsfw": 0.95, "flag": "NSFW"}


def _classifier_fn_benigno(conteudo):
    """Simula uma classificacao negativa (conteudo benigno)."""
    return {"probabilidade_nsfw": 0.05, "flag": "SFW"}


def _custody_register_fn_sucesso(evidence_id, hash_sha256, metadata):
    """Simula um registro bem-sucedido na blockchain."""
    return {"status": "success", "tx_id": "tx-simulado-001"}


def test_executar_cenario_c1_returns_expected_structure():
    """O resultado deve conter as etapas do pipeline: coleta,
    classificacao, e registro de custodia."""
    resultado = executar_cenario_c1(
        bucket="ccf-evidence-bucket",
        key="evidencia-teste.jpg",
        conteudo=b"conteudo simulado de imagem",
        collector_fn=_collector_fn_sucesso,
        classifier_fn=_classifier_fn_explicito,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert "coleta" in resultado
    assert "classificacao" in resultado
    assert "registro_custodia" in resultado
    assert "status_pipeline" in resultado


def test_executar_cenario_c1_explicit_content_triggers_custody_registration():
    """Conteudo classificado como NSFW deve ser registrado na cadeia
    de custodia - fluxo principal do Cenario C1 (RF10)."""
    resultado = executar_cenario_c1(
        bucket="ccf-evidence-bucket",
        key="evidencia-teste.jpg",
        conteudo=b"conteudo simulado de imagem",
        collector_fn=_collector_fn_sucesso,
        classifier_fn=_classifier_fn_explicito,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert resultado["classificacao"]["flag"] == "NSFW"
    assert resultado["registro_custodia"] is not None
    assert resultado["status_pipeline"] == "SUCESSO"


def test_executar_cenario_c1_benign_content_skips_custody_registration():
    """Conteudo benigno (SFW) nao deve gerar registro de custodia -
    evita poluir o ledger com eventos irrelevantes (eficiencia)."""
    resultado = executar_cenario_c1(
        bucket="ccf-evidence-bucket",
        key="evidencia-benigna.jpg",
        conteudo=b"conteudo simulado benigno",
        collector_fn=_collector_fn_sucesso,
        classifier_fn=_classifier_fn_benigno,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert resultado["classificacao"]["flag"] == "SFW"
    assert resultado["registro_custodia"] is None
    assert resultado["status_pipeline"] == "SUCESSO"


def test_executar_cenario_c1_collector_failure_is_reported():
    """Falha na etapa de coleta deve ser reportada explicitamente,
    interrompendo o pipeline - nao pode seguir adiante sem a evidencia
    coletada."""
    def collector_fn_falha(bucket, key):
        raise ConnectionError("Falha simulada de conexao com LocalStack")

    resultado = executar_cenario_c1(
        bucket="ccf-evidence-bucket",
        key="evidencia-teste.jpg",
        conteudo=b"conteudo simulado",
        collector_fn=collector_fn_falha,
        classifier_fn=_classifier_fn_explicito,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert resultado["status_pipeline"] == "FALHA"
    assert "erro" in resultado