"""
Testes unitarios para o modulo de estimativa de idade (Estagio E3,
RF05, Tabela 12, PGT).

Estrategia de teste: a funcao de classificacao recebe a funcao de
predicao (predict_fn) por injecao de dependencia, permitindo testes
rapidos com uma funcao sintetica, sem depender do download/inferencia
real do MiVOLO durante o desenvolvimento local.
"""
import pytest

from modulo_ia.estimativa_idade import classify_age


def _predict_fn_crianca(image):
    """Simula o MiVOLO estimando uma idade de crianca."""
    return 8.0


def _predict_fn_adulto(image):
    """Simula o MiVOLO estimando uma idade adulta."""
    return 35.0


def _predict_fn_limite(image):
    """Simula uma estimativa exatamente no limiar de decisao."""
    return 18.0


def test_classify_age_returns_expected_structure():
    resultado = classify_age("imagem_fake", _predict_fn_crianca)

    assert "idade_estimada" in resultado
    assert "flag" in resultado
    assert resultado["idade_estimada"] == 8.0


def test_classify_age_child_returns_menor_flag():
    resultado = classify_age("imagem_fake", _predict_fn_crianca, threshold=18)
    assert resultado["flag"] == "MENOR"


def test_classify_age_adult_returns_adulto_flag():
    resultado = classify_age("imagem_fake", _predict_fn_adulto, threshold=18)
    assert resultado["flag"] == "ADULTO"


def test_classify_age_threshold_is_exclusive_for_menor():
    """Uma idade estimada exatamente igual ao threshold (18) deve ser
    classificada como ADULTO (decisao conservadora quanto a alarmes
    falsos, mas segura: o limiar juridico e 'menor de 18', ou seja,
    17 anos e 364 dias e MENOR, exatos 18 anos completos e ADULTO)."""
    resultado = classify_age("imagem_fake", _predict_fn_limite, threshold=18)
    assert resultado["flag"] == "ADULTO"


def test_classify_age_negative_estimate_raises_error():
    """Uma estimativa de idade negativa e fisicamente impossivel -
    deve ser rejeitada, protegendo contra falha silenciosa do modelo."""
    def predict_fn_invalido(image):
        return -5.0

    with pytest.raises(ValueError):
        classify_age("imagem_fake", predict_fn_invalido)


def test_classify_age_custom_threshold_changes_classification():
    """Valida que o threshold e um parametro real, nao hardcoded."""
    resultado_18 = classify_age("imagem_fake", lambda img: 20.0, threshold=18)
    resultado_25 = classify_age("imagem_fake", lambda img: 20.0, threshold=25)

    assert resultado_18["flag"] == "ADULTO"
    assert resultado_25["flag"] == "MENOR"