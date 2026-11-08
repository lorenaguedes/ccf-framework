
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
    random_state: int = 42,
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

    explainer = lime_image.LimeImageExplainer(random_state=random_state)
    explicacao = explainer.explain_instance(
        image,
        predict_fn_lime,
        hide_color=0,
        num_samples=num_samples,
        random_seed=random_state,
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


# --- Explicabilidade de imagem para o laudo (E2) -----------------------------

def criar_predict_lote(predict_fn: Callable) -> Callable[[np.ndarray], np.ndarray]:
    """Adapta uma funcao de predicao de UMA imagem PIL (ex.: OpenNSFW2, que
    retorna a probabilidade NSFW) para a assinatura em lote usada pelo LIME."""
    from PIL import Image

    def predict_lote(imagens: np.ndarray) -> np.ndarray:
        return np.array([float(predict_fn(Image.fromarray(img.astype("uint8")))) for img in imagens])
    return predict_lote


def _regioes_altas(mascara: np.ndarray, threshold: float) -> np.ndarray:
    """Mascara booleana das regioes de alta importancia (mesmo criterio de
    identify_high_importance_regions)."""
    alta = np.zeros(mascara.shape, dtype=bool)
    coords = identify_high_importance_regions(mascara, threshold=threshold)
    if coords:
        linhas, colunas = zip(*coords)
        alta[list(linhas), list(colunas)] = True
    return alta


def resumir_mascara(mascara: np.ndarray, threshold: float = 0.5) -> dict:
    """Resumo numerico de um mapa de importancia: fracao da area de alta
    importancia e caixa delimitadora (linha_min, coluna_min, linha_max, coluna_max)."""
    alta = _regioes_altas(mascara, threshold)
    if not alta.any():
        return {"sinal_suficiente": False, "fracao_area_alta_importancia": 0.0, "caixa_delimitadora": None}
    linhas, colunas = np.where(alta)
    return {
        "sinal_suficiente": True,
        "fracao_area_alta_importancia": round(float(alta.mean()), 4),
        "caixa_delimitadora": [int(linhas.min()), int(colunas.min()), int(linhas.max()), int(colunas.max())],
    }


def jaccard_regioes(mascara_a: np.ndarray, mascara_b: np.ndarray, threshold: float = 0.5) -> float | None:
    """Indice de Jaccard entre as regioes de alta importancia de duas
    explicacoes (estabilidade entre execucoes, Secao 3.2.1 do PGT).

    Retorna None quando nenhuma das duas tem sinal (nao ha regiao a comparar)."""
    a, b = _regioes_altas(mascara_a, threshold), _regioes_altas(mascara_b, threshold)
    uniao = int((a | b).sum())
    if uniao == 0:
        return None
    return round(int((a & b).sum()) / uniao, 4)


def explicar_imagem_lime(
    imagem: np.ndarray,
    predict_lote: Callable[[np.ndarray], np.ndarray],
    num_samples: int = 200,
    sementes: tuple = (42, 43),
    threshold: float = 0.5,
) -> dict:
    """Explica a saida do modelo para uma imagem por LIME, com duas ou mais
    sementes para medir a estabilidade da explicacao (o LIME e amostral).

    Returns:
        {"mascara": ndarray da primeira semente, "metodo", "num_samples",
         "sementes", "threshold", "resumo", "estabilidade_jaccard"}
        em que estabilidade_jaccard e o Jaccard medio entre a primeira
        semente e as demais (None se nao houver sinal).
    """
    mascaras = [generate_lime_explanation(imagem, predict_lote, num_samples=num_samples, random_state=s)
                for s in sementes]
    jaccards = [jaccard_regioes(mascaras[0], m, threshold) for m in mascaras[1:]]
    validos = [j for j in jaccards if j is not None]
    return {
        "mascara": mascaras[0],
        "metodo": "LIME (segmentos de imagem)",
        "num_samples": num_samples,
        "sementes": list(sementes),
        "threshold": threshold,
        "resumo": resumir_mascara(mascaras[0], threshold),
        "estabilidade_jaccard": round(float(np.mean(validos)), 4) if validos else None,
    }


def salvar_mapa_importancia(imagem: np.ndarray, mascara: np.ndarray, caminho) -> str:
    """Grava a sobreposicao do mapa de importancia (vermelho = contribui para a
    saida, azul = reduz) sobre a imagem e retorna o SHA-256 do arquivo, para
    que o artefato de explicabilidade tambem tenha integridade verificavel."""
    import hashlib
    from pathlib import Path

    from PIL import Image

    maximo = float(np.abs(mascara).max()) or 1.0
    norm = mascara / maximo
    overlay = np.zeros(imagem.shape, dtype=np.float64)
    overlay[..., 0] = np.clip(norm, 0, 1) * 255
    overlay[..., 2] = np.clip(-norm, 0, 1) * 255
    peso = np.clip(np.abs(norm), 0, 1)[..., None] * 0.6
    misto = (imagem.astype(np.float64) * (1 - peso) + overlay * peso).clip(0, 255).astype("uint8")
    caminho = Path(caminho)
    Image.fromarray(misto).save(caminho, format="PNG")
    return hashlib.sha256(caminho.read_bytes()).hexdigest()
