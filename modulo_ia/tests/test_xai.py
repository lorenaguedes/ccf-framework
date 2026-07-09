"""
Testes unitários para o módulo de XAI (Estágio E6, Tabela 12/Seção 2.4.3 PGT).

Estratégia de teste: as funções de explicabilidade (LIME/SHAP) recebem
a função de predição por injeção de dependência (predict_fn), o que
permite testar a lógica de negócio com uma função sintética rápida,
sem depender do MiVOLO real (pesado, exige GPU) durante o
desenvolvimento local. A validação com o modelo real ocorre
separadamente no Colab (documentado no notebook, não neste módulo).

Referência: Tabela 3 (PGT) — comparativo LIME vs. SHAP para aplicação
forense, incluindo divergências entre os métodos.
"""
import numpy as np
import pytest

from modulo_ia.xai import (
    compute_agreement_score,
    generate_lime_explanation,
    identify_high_importance_regions,
)


def _predicao_sintetica_uniforme(images_array: np.ndarray) -> np.ndarray:
    """Função de predição sintética: sempre retorna o mesmo valor,
    independente da imagem — usada para validar que o LIME funciona
    mecanicamente, sem introduzir dependência de um modelo real."""
    return np.full(len(images_array), 20.0)


def _predicao_sintetica_sensivel_a_regiao(images_array: np.ndarray) -> np.ndarray:
    """Função de predição sintética que responde à intensidade média
    dos pixels — usada para validar que o LIME de fato detecta
    sensibilidade a mudanças na imagem (diferente da uniforme acima)."""
    return np.array([img.astype(np.float64).mean() / 10.0 for img in images_array])


def _gerar_imagem_teste(tamanho=(64, 64, 3)) -> np.ndarray:
    """Gera uma imagem sintética determinística (não aleatória) para
    reprodutibilidade total dos testes (RNF02)."""
    imagem = np.zeros(tamanho, dtype=np.uint8)
    imagem[:32, :, :] = 200  # metade superior clara
    imagem[32:, :, :] = 50   # metade inferior escura
    return imagem


def test_generate_lime_explanation_returns_valid_structure():
    """A explicação LIME deve retornar uma máscara de importância do
    mesmo tamanho espacial da imagem original."""
    imagem = _gerar_imagem_teste()
    mascara = generate_lime_explanation(
        imagem, _predicao_sintetica_sensivel_a_regiao, num_samples=50
    )
    assert mascara.shape[:2] == imagem.shape[:2]


def test_identify_high_importance_regions_with_uniform_prediction():
    """Se a predição é sempre constante (não sensível à imagem), não
    deve haver regiões de alta importância detectáveis — sinaliza
    ausência de sensibilidade real do modelo à entrada."""
    imagem = _gerar_imagem_teste()
    mascara = generate_lime_explanation(
        imagem, _predicao_sintetica_uniforme, num_samples=50
    )
    regioes = identify_high_importance_regions(mascara, threshold=0.5)
    assert len(regioes) == 0


def test_identify_high_importance_regions_with_sensitive_prediction():
    """Se a predição é sensível ao conteúdo da imagem, deve haver pelo
    menos uma região de alta importância identificada."""
    imagem = _gerar_imagem_teste()
    mascara = generate_lime_explanation(
        imagem, _predicao_sintetica_sensivel_a_regiao, num_samples=50
    )
    regioes = identify_high_importance_regions(mascara, threshold=0.1)
    assert len(regioes) > 0


def test_compute_agreement_score_identical_masks_returns_one():
    """Duas máscaras de importância idênticas (LIME e SHAP concordando
    perfeitamente) devem retornar score de concordância máximo (1.0)."""
    mascara = np.array([[1, 0], [0, 1]], dtype=np.float64)
    score = compute_agreement_score(mascara, mascara)
    assert score == pytest.approx(1.0)


def test_compute_agreement_score_opposite_masks_returns_low_score():
    """Máscaras completamente opostas (LIME aponta uma região, SHAP
    aponta a região complementar — como no achado da marca d'água)
    devem retornar score de concordância baixo."""
    mascara_lime = np.array([[1, 0], [0, 0]], dtype=np.float64)
    mascara_shap = np.array([[0, 0], [0, 1]], dtype=np.float64)
    score = compute_agreement_score(mascara_lime, mascara_shap)
    assert score < 0.5


def test_compute_agreement_score_requires_same_shape():
    """Máscaras de tamanhos diferentes não podem ser comparadas —
    deve levantar erro explícito, não uma comparação silenciosamente
    incorreta."""
    mascara_a = np.zeros((10, 10))
    mascara_b = np.zeros((20, 20))
    with pytest.raises(ValueError):
        compute_agreement_score(mascara_a, mascara_b)
