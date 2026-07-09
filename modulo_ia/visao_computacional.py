"""
Modulo de visao computacional - Estagio E2 (Tabela 12, PGT).

Classifica conteudo potencialmente explicito usando o modelo
pre-treinado OpenNSFW2 (Yahoo/bhky), conforme discutido na correcao
metodologica registrada (OpenNSFW2 e um modelo pre-treinado, nao um
dataset - ver ajuste da Tabela 12).

Estrategia de design: a funcao de classificacao recebe a funcao de
predicao do modelo (predict_fn) por injecao de dependencia, permitindo
testes unitarios rapidos sem depender do download dos pesos reais
(~23MB) durante o desenvolvimento local.
"""
from typing import Callable

from PIL import Image


def classify_explicit_content(
    image: Image.Image,
    predict_fn: Callable[[Image.Image], float],
    threshold: float = 0.5,
) -> dict:
    """Classifica uma imagem quanto a conteudo potencialmente
    explicito, usando uma funcao de predicao externa (ex: OpenNSFW2).

    Args:
        image: imagem PIL a ser classificada.
        predict_fn: funcao que recebe uma imagem e retorna a
            probabilidade de conteudo NSFW (0.0 a 1.0).
        threshold: limiar de decisao. Valores >= threshold sao
            classificados como NSFW (decisao conservadora no empate,
            dado o contexto de protecao infantil - RNF de seguranca).

    Returns:
        Dicionario com:
        - probabilidade_nsfw: valor retornado pelo modelo (0.0-1.0)
        - flag: "NSFW" ou "SFW"

    Raises:
        ValueError: se a probabilidade retornada estiver fora do
            intervalo valido [0, 1] - protege contra falhas silenciosas
            de integracao com o modelo real.
    """
    probabilidade = predict_fn(image)

    if not (0.0 <= probabilidade <= 1.0):
        raise ValueError(
            f"Probabilidade NSFW invalida: {probabilidade}. "
            "Deve estar no intervalo [0.0, 1.0]."
        )

    flag = "NSFW" if probabilidade >= threshold else "SFW"

    return {
        "probabilidade_nsfw": probabilidade,
        "flag": flag,
    }

def create_opennsfw2_predict_fn() -> Callable[[Image.Image], float]:
    """Cria a funcao de predicao real usando o modelo OpenNSFW2
    pre-treinado (Yahoo/bhky), para uso em producao (nao em testes
    unitarios, que usam predict_fn sinteticas).

    Returns:
        Funcao compativel com classify_explicit_content, que recebe
        uma imagem PIL e retorna a probabilidade NSFW real.
    """
    import opennsfw2 as n2

    def predict_fn(image: Image.Image) -> float:
        return n2.predict_image(image)

    return predict_fn