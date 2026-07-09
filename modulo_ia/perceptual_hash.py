"""
Módulo de hash perceptual (PDQ Hash) — Estágio E1 do pipeline
multi-modal (Tabela 12, PGT).

Triagem inicial por hash perceptual: identifica similaridade com
conteúdo previamente conhecido, mesmo diante de pequenas transformações
(recorte, recompressão, redimensionamento), diferentemente do hash
criptográfico (SHA-256), que é sensível a qualquer alteração mínima.

Referência: Facebook/Meta PDQ Hash (open-source), usado por bases de
referência como NCMEC/Interpol para identificação de material conhecido.
"""
import numpy as np
import pdqhash
from PIL import Image


def calculate_pdq_hash(image: Image.Image) -> np.ndarray:
    """Calcula o hash perceptual PDQ (256 bits) de uma imagem PIL.

    Args:
        image: imagem PIL (RGB).

    Returns:
        Array numpy de 256 bits representando o hash perceptual.
    """
    image_array = np.array(image.convert("RGB"))
    hash_vector, quality = pdqhash.compute(image_array)
    return hash_vector


def hamming_distance(hash1: np.ndarray, hash2: np.ndarray) -> int:
    """Calcula a distância de Hamming entre dois hashes perceptuais —
    número de bits diferentes entre os dois vetores.

    Quanto menor a distância, mais similares são as imagens
    originais. Distância 0 = hashes idênticos.

    Args:
        hash1, hash2: vetores de hash PDQ (256 bits cada).

    Returns:
        Número inteiro de bits divergentes.
    """
    return int(np.count_nonzero(hash1 != hash2))


def is_similar(hash1: np.ndarray, hash2: np.ndarray, threshold: int = 10) -> bool:
    """Determina se duas imagens são similares (MATCH) com base na
    distância de Hamming entre seus hashes perceptuais.

    O threshold padrão (10 bits de diferença em 256) é conservador,
    adequado para triagem inicial (Tabela 12) — valores mais permissivos
    aumentam a sensibilidade a transformações, ao custo de mais falsos
    positivos.

    Args:
        hash1, hash2: vetores de hash PDQ.
        threshold: distância máxima de Hamming para considerar MATCH.

    Returns:
        True se a distância estiver dentro do threshold (MATCH),
        False caso contrário (NOMATCH).
    """
    return hamming_distance(hash1, hash2) <= threshold
