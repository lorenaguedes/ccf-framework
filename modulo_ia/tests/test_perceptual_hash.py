"""
Testes unitários para o módulo de hash perceptual (PDQ Hash).

Referência: Tabela 12 (PGT) — Estágio E1 do pipeline multi-modal,
triagem por hash perceptual (PDQ Hash) contra bases de referência.

As imagens de teste são geradas programaticamente (formas geométricas
simples via Pillow), garantindo reprodutibilidade total (RNF02) sem
dependência de arquivos externos ou datasets de terceiros.
"""
import io

import pytest
from PIL import Image

from modulo_ia.perceptual_hash import (
    calculate_pdq_hash,
    hamming_distance,
    is_similar,
)


def _gerar_imagem_teste(cor: tuple, tamanho=(256, 256)) -> Image.Image:
    """Gera uma imagem sintética sólida de cor única, para uso
    determinístico nos testes de hash perceptual."""
    return Image.new("RGB", tamanho, color=cor)


def test_calculate_pdq_hash_returns_correct_format():
    """O hash PDQ deve ser um array/sequência de 256 bits."""
    imagem = _gerar_imagem_teste((255, 0, 0))
    hash_resultado = calculate_pdq_hash(imagem)
    assert len(hash_resultado) == 256


def test_calculate_pdq_hash_deterministic():
    """A mesma imagem deve sempre gerar o mesmo hash perceptual."""
    imagem = _gerar_imagem_teste((0, 255, 0))
    hash1 = calculate_pdq_hash(imagem)
    hash2 = calculate_pdq_hash(imagem)
    assert list(hash1) == list(hash2)


def test_hamming_distance_identical_images_is_zero():
    """Duas imagens idênticas devem ter distância de Hamming zero —
    caso MATCH perfeito na triagem (Tabela 12)."""
    imagem = _gerar_imagem_teste((0, 0, 255))
    hash1 = calculate_pdq_hash(imagem)
    hash2 = calculate_pdq_hash(imagem)
    assert hamming_distance(hash1, hash2) == 0


def test_hamming_distance_very_different_images_is_high():
    """Imagens com cores completamente diferentes devem ter distância
    de Hamming alta — caso NOMATCH claro."""
    imagem_preta = _gerar_imagem_teste((0, 0, 0))
    imagem_branca = _gerar_imagem_teste((255, 255, 255))

    hash_preta = calculate_pdq_hash(imagem_preta)
    hash_branca = calculate_pdq_hash(imagem_branca)

    distancia = hamming_distance(hash_preta, hash_branca)
    assert distancia > 50  # threshold arbitrário alto para cores opostas


def test_is_similar_identical_images_returns_true():
    """Imagens idênticas devem ser sinalizadas como similares (MATCH),
    conforme a saída esperada do Estágio E1 (Tabela 12)."""
    imagem = _gerar_imagem_teste((128, 64, 200))
    hash1 = calculate_pdq_hash(imagem)
    hash2 = calculate_pdq_hash(imagem)
    assert is_similar(hash1, hash2, threshold=10) is True


def test_is_similar_different_images_returns_false():
    """Imagens muito diferentes não devem ser sinalizadas como
    similares (NOMATCH)."""
    imagem_preta = _gerar_imagem_teste((0, 0, 0))
    imagem_branca = _gerar_imagem_teste((255, 255, 255))
    hash_preta = calculate_pdq_hash(imagem_preta)
    hash_branca = calculate_pdq_hash(imagem_branca)
    assert is_similar(hash_preta, hash_branca, threshold=10) is False
