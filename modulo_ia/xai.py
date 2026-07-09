
"""
Modulo de Inteligencia Artificial Explicavel (XAI) - Estagio E6
(Tabela 12, PGT), transversal aos estagios E2-E5.

Implementa explicabilidade via LIME, e ferramentas de comparacao entre
diferentes metodos de explicacao (LIME vs. SHAP), fundamentado na
Secao 2.4.3 e Tabela 3 do PGT.

Estrategia de design: as funcoes recebem a funcao de predicao do
modelo (predict_fn) por injecao de dependencia, permitindo testes
unitarios rapidos com funcoes sinteticas, sem depender do modelo real
(MiVOLO, pesado, requer GPU) - a validacao com o modelo real ocorre
separadamente em ambiente Colab (documentada em notebook proprio).
"""
from typing import Callable

import numpy as np
from lime import lime_image


def generate_lime_explanation(
    image: np.ndarray,
    predict_fn: Callable[[np.ndarray], np.ndarray],
    num_samples: int = 200,
) -> np.ndarray:
    """Gera uma mascara de importancia via LIME para uma imagem,
    usando uma funcao de predicao externa (injecao de dependencia).

    Diferente de LIME.get_image_and_mask() (que retorna uma selecao
    binaria dos top-N segmentos, adequada para visualizacao mas nao
    para analise estatistica), esta funcao extrai os coeficientes
    continuos reais calculados pelo modelo linear interno do LIME
    (explicacao.local_exp), preservando a magnitude real da
    contribuicao de cada segmento.

    Args:
        image: imagem de entrada (H, W, 3), uint8.
        predict_fn: funcao que recebe um array de imagens e retorna um
            array de previsoes (ex: idade estimada).
        num_samples: numero de perturbacoes usadas pelo LIME.

    Returns:
        Mascara de importancia continua (H, W).
    """
    def predict_fn_lime(images_array):
        return predict_fn(images_array).reshape(-1, 1)

    explainer = lime_image.LimeImageExplainer()
    explicacao = explainer.explain_instance(
        image,
        predict_fn_lime,
        hide_color=0,
        num_samples=num_samples,
    )

    segments = explicacao.segments
    coeficientes_por_segmento = dict(explicacao.local_exp[0])

    mascara = np.zeros(segments.shape, dtype=np.float64)
    for segment_id, peso in coeficientes_por_segmento.items():
        mascara[segments == segment_id] = peso

    return mascara

def identify_high_importance_regions(
    importance_mask: np.ndarray,
    threshold: float = 0.5,
    min_relative_variation: float = 1e-3,
) -> list:
    """Identifica as coordenadas (linha, coluna) de regioes cuja
    importancia normalizada excede o threshold especificado.

    Args:
        importance_mask: mascara de importancia (H, W).
        threshold: valor minimo (normalizado 0-1) para considerar uma
            regiao de alta importancia.
        min_relative_variation: variacao minima relativa (desvio padrao
            dividido pelo valor maximo absoluto) exigida na mascara
            para considerar que ha sinal real, independente da escala
            numerica dos valores (diferente de um threshold absoluto,
            que falharia dependendo da magnitude dos coeficientes do
            LIME/SHAP).

    Returns:
        Lista de coordenadas (linha, coluna) das regioes relevantes.
    """
    max_abs = np.abs(importance_mask).max()
    if max_abs == 0:
        return []

    variacao_relativa = np.std(importance_mask) / max_abs
    if variacao_relativa < min_relative_variation:
        return []

    mascara_normalizada = np.abs(importance_mask) / max_abs
    coordenadas = np.argwhere(mascara_normalizada >= threshold)

    return [tuple(coord) for coord in coordenadas]


def compute_agreement_score(mask_a: np.ndarray, mask_b: np.ndarray) -> float:
    """Calcula um score de concordancia entre dois mapas de importancia
    (ex: LIME vs. SHAP), usando correlacao de Pearson normalizada para
    o intervalo [0, 1].

    Args:
        mask_a: primeiro mapa de importancia.
        mask_b: segundo mapa de importancia, mesmo formato de mask_a.

    Returns:
        Score de concordancia entre 0.0 e 1.0.

    Raises:
        ValueError: se os mapas tiverem formatos diferentes.
    """
    if mask_a.shape != mask_b.shape:
        raise ValueError(
            "Mascaras de formatos incompativeis: nao e possivel "
            "calcular concordancia entre mapas de tamanhos diferentes."
        )

    a_flat = mask_a.flatten().astype(np.float64)
    b_flat = mask_b.flatten().astype(np.float64)

    if np.std(a_flat) == 0 or np.std(b_flat) == 0:
        return 1.0 if np.array_equal(a_flat, b_flat) else 0.0

    correlacao = np.corrcoef(a_flat, b_flat)[0, 1]

    return (correlacao + 1) / 2
