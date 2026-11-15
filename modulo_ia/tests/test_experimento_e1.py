"""Testes do experimento E1 (PDQ) - corpus sintetico pequeno."""
import numpy as np

from modulo_ia.experimentos import experimento_e1 as e1


def test_gerar_imagem_deterministica():
    a, b = e1.gerar_imagem(7), e1.gerar_imagem(7)
    assert np.array_equal(np.array(a), np.array(b))
    assert not np.array_equal(np.array(a), np.array(e1.gerar_imagem(8)))


def test_distancias_hamming():
    h = np.zeros((2, 256), dtype=np.uint8)
    h[1, :5] = 1
    d = e1.distancias(h, h)
    assert d[0, 0] == 0 and d[0, 1] == 5 and d[1, 0] == 5


def test_wilson_limites():
    lo, hi = e1.wilson(0, 2000)
    assert lo == 0.0 and 0 < hi < 0.01
    assert e1.wilson(0, 0) == (None, None)


def test_executar_pequeno_estrutura_e_jpeg_robusto():
    r = e1.executar(n_ref=12, n_neg=30)
    assert r["configuracao"]["n_referencias"] == 12
    leves = r["transformacoes_leves"]["por_transformacao_revocacao"]
    assert leves["jpeg_q90"]["31"] == 1.0
    assert "global_qualidade_ge_50" in r["transformacoes_leves"]
    assert r["transformacoes_no_limite_declarado"]["por_transformacao_revocacao"]["espelho_horizontal"]["10"] == 0.0
