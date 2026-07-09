"""
Testes unitarios para o modulo de deteccao de grooming (Estagio E4,
RF06, Tabela 12 - PGT).

Estrategia de teste: a funcao de classificacao recebe a funcao de
predicao (predict_fn) por injecao de dependencia, permitindo testes
rapidos com uma funcao sintetica, sem depender do fine-tuning real do
BERTimbau (pesado, exige GPU/Colab).
"""
import pytest

from modulo_ia.deteccao_grooming import classify_grooming


def _predict_fn_baixo_risco(texto: str) -> dict:
    """Simula o BERTimbau retornando baixo score de grooming, sem
    tokens relevantes destacados."""
    return {"score": 0.05, "tokens_relevantes": []}


def _predict_fn_alto_risco(texto: str) -> dict:
    """Simula o BERTimbau retornando alto score de grooming, com
    tokens suspeitos destacados."""
    return {"score": 0.91, "tokens_relevantes": ["segredo", "não conta pra ninguém"]}


def test_classify_returns_expected_structure():
    """O resultado deve conter score, flag e tokens relevantes."""
    resultado = classify_grooming("Oi, tudo bem com você?", _predict_fn_baixo_risco)

    assert "score_grooming" in resultado
    assert "flag" in resultado
    assert "tokens_relevantes" in resultado


def test_classify_low_score_returns_normal_flag():
    """Score baixo deve ser classificado como comunicacao normal."""
    resultado = classify_grooming(
        "Oi, tudo bem com você?", _predict_fn_baixo_risco, threshold=0.5
    )
    assert resultado["flag"] == "NORMAL"


def test_classify_high_score_returns_suspicious_flag():
    """Score alto deve ser sinalizado como suspeito, conforme RF06."""
    resultado = classify_grooming(
        "Isso é nosso segredo, ok?", _predict_fn_alto_risco, threshold=0.5
    )
    assert resultado["flag"] == "SUSPEITO"


def test_classify_suspicious_result_includes_relevant_tokens():
    """Quando sinalizado como suspeito, os tokens que embasaram a
    decisao devem estar presentes - essencial para explicabilidade
    textual exigida pelo RF08/laudo pericial."""
    resultado = classify_grooming(
        "Isso é nosso segredo, ok?", _predict_fn_alto_risco, threshold=0.5
    )
    assert len(resultado["tokens_relevantes"]) > 0
    assert "segredo" in resultado["tokens_relevantes"]


def test_classify_empty_text_raises_error():
    """Texto vazio nao deve ser processado silenciosamente - pode
    indicar falha na extracao da conversa, nao um caso valido de
    ausencia de grooming."""
    with pytest.raises(ValueError):
        classify_grooming("", _predict_fn_baixo_risco)


def test_classify_invalid_score_raises_error():
    """Uma funcao de predicao retornando score fora de [0, 1] deve
    ser rejeitada - protege contra falha silenciosa na integracao com
    o modelo real."""
    def predict_fn_invalido(texto):
        return {"score": 1.7, "tokens_relevantes": []}

    with pytest.raises(ValueError):
        classify_grooming("texto qualquer", predict_fn_invalido)