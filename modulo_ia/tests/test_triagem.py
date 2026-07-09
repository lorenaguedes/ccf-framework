"""
Testes unitários para a camada de triagem por hash perceptual —
comparação contra base de hashes conhecidos (proxy de NCMEC/Interpol),
conforme Estágio E1 da Tabela 12 (PGT).
"""
from PIL import Image

from modulo_ia.perceptual_hash import calculate_pdq_hash
from modulo_ia.triagem import KnownHashDatabase, triage


def _gerar_imagem_teste(cor: tuple, tamanho=(256, 256)) -> Image.Image:
    return Image.new("RGB", tamanho, color=cor)


def test_known_hash_database_starts_empty():
    """Uma base recém-criada não deve conter nenhum hash registrado."""
    db = KnownHashDatabase()
    assert db.count() == 0


def test_known_hash_database_add_and_count():
    """Adicionar um hash conhecido deve incrementar a contagem da base."""
    db = KnownHashDatabase()
    imagem = _gerar_imagem_teste((10, 20, 30))
    hash_valor = calculate_pdq_hash(imagem)

    db.add("item-conhecido-001", hash_valor)

    assert db.count() == 1


def test_triage_returns_match_for_known_content():
    """Uma evidência idêntica a um item da base deve ser sinalizada
    como MATCH, com score de similaridade máximo."""
    db = KnownHashDatabase()
    imagem_conhecida = _gerar_imagem_teste((50, 100, 150))
    hash_conhecido = calculate_pdq_hash(imagem_conhecida)
    db.add("item-conhecido-001", hash_conhecido)

    resultado = triage(imagem_conhecida, db, threshold=10)

    assert resultado["flag"] == "MATCH"
    assert resultado["matched_id"] == "item-conhecido-001"
    assert resultado["score_similaridade"] == 1.0


def test_triage_returns_nomatch_for_unknown_content():
    """Uma evidência completamente diferente de tudo na base deve ser
    sinalizada como NOMATCH."""
    db = KnownHashDatabase()
    imagem_conhecida = _gerar_imagem_teste((0, 0, 0))
    db.add("item-conhecido-001", calculate_pdq_hash(imagem_conhecida))

    imagem_nova = _gerar_imagem_teste((255, 255, 255))
    resultado = triage(imagem_nova, db, threshold=10)

    assert resultado["flag"] == "NOMATCH"
    assert resultado["matched_id"] is None


def test_triage_empty_database_always_returns_nomatch():
    """Contra uma base vazia, qualquer evidência deve retornar NOMATCH
    — não há nada com que comparar."""
    db = KnownHashDatabase()
    imagem = _gerar_imagem_teste((100, 100, 100))

    resultado = triage(imagem, db, threshold=10)

    assert resultado["flag"] == "NOMATCH"
    assert resultado["matched_id"] is None
    assert resultado["score_similaridade"] == 0.0


def test_triage_returns_closest_match_among_multiple_known_items():
    """Quando há múltiplos itens na base, a triagem deve retornar o
    item mais similar (menor distância de Hamming), não apenas o
    primeiro encontrado."""
    db = KnownHashDatabase()

    imagem_a = _gerar_imagem_teste((10, 10, 10))
    imagem_b = _gerar_imagem_teste((200, 200, 200))
    db.add("item-A", calculate_pdq_hash(imagem_a))
    db.add("item-B", calculate_pdq_hash(imagem_b))

    # Imagem de teste mais próxima de A (mesma cor exata)
    resultado = triage(imagem_a, db, threshold=10)

    assert resultado["matched_id"] == "item-A"
