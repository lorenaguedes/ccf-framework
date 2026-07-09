"""
Testes unitarios para o modulo de visao computacional (Estagio E2,
Tabela 12, PGT) - classificacao de conteudo explicito via OpenNSFW2.

Estrategia de teste: a funcao de classificacao recebe a funcao de
predicao (predict_fn) por injecao de dependencia, permitindo testes
rapidos com uma funcao sintetica, sem depender do download dos pesos
reais do modelo OpenNSFW2 durante o desenvolvimento local.
"""
import pytest
from PIL import Image

from modulo_ia.visao_computacional import classify_explicit_content


def _gerar_imagem_teste(cor=(100, 100, 100)) -> Image.Image:
    return Image.new("RGB", (224, 224), color=cor)


def _predict_fn_baixa_probabilidade(image) -> float:
    """Simula o OpenNSFW2 retornando probabilidade NSFW baixa."""
    return 0.05


def _predict_fn_alta_probabilidade(image) -> float:
    """Simula o OpenNSFW2 retornando probabilidade NSFW alta."""
    return 0.92


def _predict_fn_limite(image) -> float:
    """Simula uma probabilidade exatamente no limiar de decisao."""
    return 0.5


def test_classify_returns_expected_structure():
    """O resultado deve conter probabilidade e flag de classificacao."""
    imagem = _gerar_imagem_teste()
    resultado = classify_explicit_content(imagem, _predict_fn_baixa_probabilidade)

    assert "probabilidade_nsfw" in resultado
    assert "flag" in resultado
    assert resultado["probabilidade_nsfw"] == 0.05


def test_classify_low_probability_returns_sfw_flag():
    """Probabilidade baixa deve ser classificada como SFW (seguro)."""
    imagem = _gerar_imagem_teste()
    resultado = classify_explicit_content(
        imagem, _predict_fn_baixa_probabilidade, threshold=0.5
    )
    assert resultado["flag"] == "SFW"


def test_classify_high_probability_returns_nsfw_flag():
    """Probabilidade alta deve ser classificada como NSFW (sinalizado
    para revisao), conforme RF do Estagio E2."""
    imagem = _gerar_imagem_teste()
    resultado = classify_explicit_content(
        imagem, _predict_fn_alta_probabilidade, threshold=0.5
    )
    assert resultado["flag"] == "NSFW"


def test_classify_threshold_is_inclusive_for_nsfw():
    """Um valor exatamente igual ao threshold deve ser tratado como
    NSFW (decisao conservadora - erra para o lado da seguranca em
    caso de empate, dado o contexto de protecao infantil)."""
    imagem = _gerar_imagem_teste()
    resultado = classify_explicit_content(
        imagem, _predict_fn_limite, threshold=0.5
    )
    assert resultado["flag"] == "NSFW"


def test_classify_custom_threshold_changes_classification():
    """Um threshold mais permissivo (mais alto) deve reclassificar um
    caso que antes era NSFW para SFW - valida que o parametro
    realmente influencia a decisao, nao esta hardcoded."""
    imagem = _gerar_imagem_teste()

    resultado_threshold_baixo = classify_explicit_content(
        imagem, _predict_fn_alta_probabilidade, threshold=0.5
    )
    resultado_threshold_alto = classify_explicit_content(
        imagem, _predict_fn_alta_probabilidade, threshold=0.95
    )

    assert resultado_threshold_baixo["flag"] == "NSFW"
    assert resultado_threshold_alto["flag"] == "SFW"


def test_classify_invalid_probability_raises_error():
    """Uma funcao de predicao retornando valor fora do intervalo
    [0, 1] deve ser rejeitada - protege contra bugs silenciosos na
    integracao com o modelo real."""
    imagem = _gerar_imagem_teste()

    def predict_fn_invalido(image):
        return 1.5

    with pytest.raises(ValueError):
        classify_explicit_content(imagem, predict_fn_invalido)