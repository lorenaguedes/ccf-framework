"""
Teste do orquestrador do Cenario C2 - Grooming em Plataforma de
Mensagens (Tabela 16, PGT).

Modulos exercitados: Coleta Docker -> NLP BERT -> SHAP -> Blockchain

Mesma estrategia de injecao de dependencia do Cenario C1.
"""
import pytest

from modulo_integracao.cenarios_simulacao.cenario_c2 import executar_cenario_c2


def _collector_fn_sucesso(container_id, log_path):
    """Simula uma coleta bem-sucedida de logs de conversa via Docker."""
    return {
        "container_id": container_id,
        "log_path": log_path,
        "hashes": {"sha256": "abc123", "md5": "def456"},
        "size_bytes": 512,
        "collected_at": "2026-07-22T10:00:00+00:00",
    }


def _grooming_classifier_fn_suspeito(texto):
    """Simula deteccao positiva de grooming."""
    return {
        "score_grooming": 0.91,
        "flag": "SUSPEITO",
        "tokens_relevantes": ["segredo", "nao conta pra ninguem"],
    }


def _grooming_classifier_fn_normal(texto):
    """Simula conversa normal, sem grooming."""
    return {"score_grooming": 0.05, "flag": "NORMAL", "tokens_relevantes": []}


def _custody_register_fn_sucesso(evidence_id, hash_sha256, metadata):
    return {"status": "success", "tx_id": "tx-simulado-002"}


def test_executar_cenario_c2_returns_expected_structure():
    """O resultado deve conter todas as etapas do pipeline C2."""
    resultado = executar_cenario_c2(
        container_id="container-msgs-001",
        log_path="/logs/conversa.txt",
        texto_conversa="Isso e nosso segredo, ok?",
        collector_fn=_collector_fn_sucesso,
        grooming_classifier_fn=_grooming_classifier_fn_suspeito,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert "coleta" in resultado
    assert "classificacao_grooming" in resultado
    assert "registro_custodia" in resultado
    assert "status_pipeline" in resultado


def test_executar_cenario_c2_suspicious_conversation_triggers_custody():
    """Conversa suspeita deve ser registrada na cadeia de custodia,
    com os tokens relevantes preservados para o laudo (RF12)."""
    resultado = executar_cenario_c2(
        container_id="container-msgs-001",
        log_path="/logs/conversa.txt",
        texto_conversa="Isso e nosso segredo, ok?",
        collector_fn=_collector_fn_sucesso,
        grooming_classifier_fn=_grooming_classifier_fn_suspeito,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert resultado["classificacao_grooming"]["flag"] == "SUSPEITO"
    assert resultado["registro_custodia"] is not None
    assert len(resultado["classificacao_grooming"]["tokens_relevantes"]) > 0
    assert resultado["status_pipeline"] == "SUCESSO"


def test_executar_cenario_c2_normal_conversation_skips_custody():
    """Conversa normal nao deve gerar registro de custodia."""
    resultado = executar_cenario_c2(
        container_id="container-msgs-001",
        log_path="/logs/conversa.txt",
        texto_conversa="Oi, tudo bem?",
        collector_fn=_collector_fn_sucesso,
        grooming_classifier_fn=_grooming_classifier_fn_normal,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert resultado["registro_custodia"] is None
    assert resultado["status_pipeline"] == "SUCESSO"


def test_executar_cenario_c2_collector_failure_is_reported():
    """Falha na coleta deve interromper o pipeline explicitamente."""
    def collector_fn_falha(container_id, log_path):
        raise FileNotFoundError("Log nao encontrado no container simulado")

    resultado = executar_cenario_c2(
        container_id="container-msgs-001",
        log_path="/logs/inexistente.txt",
        texto_conversa="texto qualquer",
        collector_fn=collector_fn_falha,
        grooming_classifier_fn=_grooming_classifier_fn_suspeito,
        custody_register_fn=_custody_register_fn_sucesso,
    )

    assert resultado["status_pipeline"] == "FALHA"
    assert "erro" in resultado