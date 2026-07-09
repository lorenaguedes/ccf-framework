"""
Modulo de deteccao de grooming (aliciamento) - Estagio E4 (RF06,
Tabela 12, PGT).

Classifica textos de conversas quanto a padroes linguisticos de
aliciamento, usando um modelo BERTimbau fine-tuned (fora do escopo
deste modulo - ver notebook Colab), seguido de extracao de tokens
relevantes para explicabilidade textual (RF08).

Estrategia de design: a funcao de classificacao recebe a funcao de
predicao do modelo (predict_fn) por injecao de dependencia, permitindo
testes unitarios rapidos sem depender do fine-tuning real (pesado,
exige GPU/Colab) durante o desenvolvimento local.
"""
from typing import Callable


def classify_grooming(
    text: str,
    predict_fn: Callable[[str], dict],
    threshold: float = 0.5,
) -> dict:
    """Classifica um texto quanto a padroes de grooming, usando uma
    funcao de predicao externa (ex: BERTimbau fine-tuned).

    Args:
        text: texto da conversa a ser analisado.
        predict_fn: funcao que recebe um texto e retorna um dicionario
            com "score" (float, 0.0-1.0) e "tokens_relevantes"
            (lista de strings que mais contribuiram para o score).
        threshold: limiar de decisao. Valores >= threshold sao
            classificados como SUSPEITO (decisao conservadora no
            empate, dado o contexto de protecao infantil).

    Returns:
        Dicionario com:
        - score_grooming: valor retornado pelo modelo (0.0-1.0)
        - flag: "SUSPEITO" ou "NORMAL"
        - tokens_relevantes: tokens que embasaram a classificacao
          (explicabilidade textual, RF08)

    Raises:
        ValueError: se o texto for vazio, ou se o score retornado
            estiver fora do intervalo valido [0, 1].
    """
    if not text or not text.strip():
        raise ValueError(
            "Texto vazio nao pode ser classificado: pode indicar "
            "falha na extracao da conversa, nao ausencia valida de grooming."
        )

    resultado_predicao = predict_fn(text)
    score = resultado_predicao["score"]
    tokens_relevantes = resultado_predicao.get("tokens_relevantes", [])

    if not (0.0 <= score <= 1.0):
        raise ValueError(
            f"Score de grooming invalido: {score}. "
            "Deve estar no intervalo [0.0, 1.0]."
        )

    flag = "SUSPEITO" if score >= threshold else "NORMAL"

    return {
        "score_grooming": score,
        "flag": flag,
        "tokens_relevantes": tokens_relevantes,
    }