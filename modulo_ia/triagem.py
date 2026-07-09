"""
Camada de triagem por hash perceptual — Estágio E1 do pipeline
multi-modal (Tabela 12, PGT).

Compara uma evidência nova contra uma base de hashes conhecidos (proxy
de bases de referência como NCMEC/Interpol), retornando score de
similaridade e flag MATCH/NOMATCH, conforme especificado na Tabela 12.
"""
from typing import Optional

import numpy as np
from PIL import Image

from modulo_ia.perceptual_hash import calculate_pdq_hash, hamming_distance

HASH_LENGTH_BITS = 256


class KnownHashDatabase:
    """Representa uma base de hashes perceptuais conhecidos — proxy
    ético de bases de referência reais (NCMEC/Interpol), conforme
    salvaguarda da Seção 1.6.2 do PGT (sem acesso a material real)."""

    def __init__(self):
        self._hashes: dict[str, np.ndarray] = {}

    def add(self, item_id: str, hash_value: np.ndarray) -> None:
        """Adiciona um hash conhecido à base, associado a um
        identificador único."""
        self._hashes[item_id] = hash_value

    def count(self) -> int:
        """Retorna o número de itens registrados na base."""
        return len(self._hashes)

    def all_items(self):
        """Retorna todos os pares (item_id, hash) da base."""
        return self._hashes.items()


def triage(
    image: Image.Image,
    database: KnownHashDatabase,
    threshold: int = 10,
) -> dict:
    """Realiza a triagem de uma imagem contra a base de hashes
    conhecidos, retornando o item mais similar (se houver) e a
    classificação MATCH/NOMATCH.

    Args:
        image: imagem PIL a ser triada.
        database: base de hashes conhecidos.
        threshold: distância máxima de Hamming para considerar MATCH.

    Returns:
        Dicionário com:
        - flag: "MATCH" ou "NOMATCH"
        - matched_id: ID do item mais similar encontrado (ou None)
        - score_similaridade: normalizado entre 0.0 e 1.0
          (1.0 = hashes idênticos; 0.0 = totalmente diferentes ou base vazia)
    """
    if database.count() == 0:
        return {
            "flag": "NOMATCH",
            "matched_id": None,
            "score_similaridade": 0.0,
        }

    query_hash = calculate_pdq_hash(image)

    menor_distancia: Optional[int] = None
    item_mais_proximo: Optional[str] = None

    for item_id, known_hash in database.all_items():
        distancia = hamming_distance(query_hash, known_hash)
        if menor_distancia is None or distancia < menor_distancia:
            menor_distancia = distancia
            item_mais_proximo = item_id

    score_similaridade = 1.0 - (menor_distancia / HASH_LENGTH_BITS)

    if menor_distancia <= threshold:
        return {
            "flag": "MATCH",
            "matched_id": item_mais_proximo,
            "score_similaridade": round(score_similaridade, 4),
        }

    return {
        "flag": "NOMATCH",
        "matched_id": None,
        "score_similaridade": round(score_similaridade, 4),
    }
