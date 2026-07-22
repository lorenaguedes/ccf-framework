"""
Teste do orquestrador do Cenario C3 - Operacao Combinada em
Multi-Nuvem (Tabela 16, PGT).

Modulos exercitados: todos (coleta multi-nuvem, hash, CNN, NLP,
anomalias, XAI, blockchain). Criterio de sucesso: pipeline end-to-end
sem erros, correlacao de evidencias de 3 CSPs no mesmo laudo.
"""
import pytest

from modulo_integracao.cenarios_simulacao.cenario_c3 import executar_cenario_c3


def _aws_collector_fn(bucket, key):
    return {"cloud_provider": "aws", "hashes": {"sha256": "hash-aws-001"}, "flag_explicito": True}


def _gcp_collector_fn(bucket, key):
    return {"cloud_provider": "gcp", "hashes": {"sha256": "hash-gcp-001"}, "anomalia_detectada": True}


def _azure_collector_fn(container, blob):
    return {"cloud_provider": "azure", "hashes": {"sha256": "hash-azure-001"}, "metadados_suspeitos": True}

def _custody_register_fn_sucesso(evidence_id, hash_sha256, metadata):
    return {"status": "success", "tx_id": f"tx-{evidence_id}"}


def test_executar_cenario_c3_returns_expected_structure():
    """O resultado deve conter evidencias correlacionadas dos 3 CSPs."""
    resultado = executar_cenario_c3(
        aws_collector_fn=_aws_collector_fn,
        gcp_collector_fn=_gcp_collector_fn,
        azure_collector_fn=_azure_collector_fn,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert "evidencias" in resultado
    assert len(resultado["evidencias"]) == 3
    assert "status_pipeline" in resultado
    assert "correlacao" in resultado


def test_executar_cenario_c3_correlates_all_three_providers():
    """A correlacao deve identificar evidencias vindas de todos os
    3 provedores distintos - criterio de sucesso do C3 (Tabela 16)."""
    resultado = executar_cenario_c3(
        aws_collector_fn=_aws_collector_fn,
        gcp_collector_fn=_gcp_collector_fn,
        azure_collector_fn=_azure_collector_fn,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    providers_encontrados = {ev["cloud_provider"] for ev in resultado["evidencias"]}
    assert providers_encontrados == {"aws", "gcp", "azure"}
    assert resultado["correlacao"]["total_csps_envolvidos"] == 3


def test_executar_cenario_c3_registers_all_evidences_in_custody():
    """Cada evidencia coletada deve gerar seu proprio registro de
    custodia - rastreabilidade individual por CSP de origem."""
    resultado = executar_cenario_c3(
        aws_collector_fn=_aws_collector_fn,
        gcp_collector_fn=_gcp_collector_fn,
        azure_collector_fn=_azure_collector_fn,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert len(resultado["registros_custodia"]) == 3
    assert resultado["status_pipeline"] == "SUCESSO"


def test_executar_cenario_c3_partial_failure_is_reported():
    """Falha em um dos coletores deve ser reportada, mas nao deve
    impedir a coleta dos demais CSPs - resiliencia parcial e
    rastreabilidade de qual CSP falhou."""
    def gcp_collector_fn_falha(bucket, key):
        raise ConnectionError("Falha simulada de conexao com fake-gcs-server")

    resultado = executar_cenario_c3(
        aws_collector_fn=_aws_collector_fn,
        gcp_collector_fn=gcp_collector_fn_falha,
        azure_collector_fn=_azure_collector_fn,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert resultado["status_pipeline"] == "SUCESSO_PARCIAL"
    assert len(resultado["evidencias"]) == 2
    assert "gcp" in resultado["erros_por_provider"]