import pytest
from modulo_coleta.hashing import calculate_sha256, calculate_md5, calculate_hashes

def test_calculate_sha256_known_value():
    """Verifica que o SHA-256 bate com o valor de referência calculado
    de forma independente via `sha256sum` (evita testar a implementação
    contra si mesma)."""
    conteudo = b"evidencia de teste ccf-framework"
    hash_esperado = "a892d7a517939e5d07e61ab3b2e5c5db8be675d75801e0c60221a68412bbd2a4"
    resultado = calculate_sha256(conteudo)
    assert resultado == hash_esperado


def test_calculate_sha256_deterministic():
    """O mesmo conteúdo deve sempre gerar o mesmo hash (determinismo é
    condição essencial para admissibilidade jurídica da prova)."""
    conteudo = b"conteudo identico"
    hash1 = calculate_sha256(conteudo)
    hash2 = calculate_sha256(conteudo)
    assert hash1 == hash2


def test_calculate_sha256_different_content_different_hash():
    """Conteúdos diferentes devem gerar hashes diferentes (sensibilidade
    do algoritmo — propriedade fundamental de hash criptográfico)."""
    hash1 = calculate_sha256(b"conteudo A")
    hash2 = calculate_sha256(b"conteudo B")
    assert hash1 != hash2


def test_calculate_md5_returns_valid_format():
    """MD5 é mantido por compatibilidade com ferramentas forenses legadas
    mesmo não sendo criptograficamente robusto."""
    resultado = calculate_md5(b"teste")
    assert isinstance(resultado, str)
    assert len(resultado) == 32  # MD5 sempre gera 32 caracteres hex


def test_calculate_hashes_returns_both():
    """Função de conveniência que retorna SHA-256 e MD5 juntos, no
    formato usado pelo registro de evidência (RF: registro no momento
    da coleta)."""
    resultado = calculate_hashes(b"evidencia")
    assert "sha256" in resultado
    assert "md5" in resultado
    assert len(resultado["sha256"]) == 64
    assert len(resultado["md5"]) == 32


def test_calculate_hashes_empty_content_raises_error():
    """Conteúdo vazio não deve ser aceito silenciosamente"""
    with pytest.raises(ValueError):
        calculate_hashes(b"")
