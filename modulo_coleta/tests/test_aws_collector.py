"""
Testes de integração para o conector de coleta AWS (LocalStack).

Estes testes exigem o LocalStack em execução (docker compose up -d).
Diferente do módulo de hashing (testes unitários puros), aqui validamos
o conector contra o emulador real, coerente com a proposta do PGT de
usar emuladores oficiais em vez de mocks de biblioteca.

Referência: RF (Módulo de Coleta Multi-Nuvem) — coleta com registro de
hash de integridade no momento da coleta.
"""
import boto3
import pytest
from datetime import datetime, timezone

from modulo_coleta.aws_collector import collect_from_s3, get_s3_client

BUCKET_TESTE = "ccf-evidence-bucket"
CHAVE_TESTE = "evidencia-teste-integracao.txt"
CONTEUDO_TESTE = b"conteudo de evidencia simulada para teste de integracao"


@pytest.fixture(scope="module")
def s3_client_setup():
    """Prepara o bucket e o objeto de teste no LocalStack antes dos
    testes, usando boto3 diretamente (não o nosso conector) — evita
    testar a implementação contra si mesma."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=BUCKET_TESTE)
    except Exception:
        client.create_bucket(Bucket=BUCKET_TESTE)

    client.put_object(Bucket=BUCKET_TESTE, Key=CHAVE_TESTE, Body=CONTEUDO_TESTE)
    yield client


def test_get_s3_client_returns_boto3_client():
    """O client deve ser uma instância válida de boto3 apontando para
    o endpoint do LocalStack, não para a AWS real."""
    client = get_s3_client()
    assert client.meta.endpoint_url is not None
    assert "4566" in client.meta.endpoint_url or "localhost" in client.meta.endpoint_url


def test_collect_from_s3_returns_expected_structure(s3_client_setup):
    """O registro retornado deve conter todos os campos exigidos para
    rastreabilidade forense: bucket, key, hashes, tamanho, timestamp."""
    resultado = collect_from_s3(BUCKET_TESTE, CHAVE_TESTE)

    assert resultado["bucket"] == BUCKET_TESTE
    assert resultado["key"] == CHAVE_TESTE
    assert resultado["cloud_provider"] == "aws"
    assert "sha256" in resultado["hashes"]
    assert "md5" in resultado["hashes"]
    assert resultado["size_bytes"] == len(CONTEUDO_TESTE)
    assert "collected_at" in resultado


def test_collect_from_s3_hash_matches_known_content(s3_client_setup):
    """O hash retornado deve corresponder exatamente ao hash do
    conteúdo original, calculado de forma independente."""
    import hashlib
    hash_esperado = hashlib.sha256(CONTEUDO_TESTE).hexdigest()

    resultado = collect_from_s3(BUCKET_TESTE, CHAVE_TESTE)

    assert resultado["hashes"]["sha256"] == hash_esperado


def test_collect_from_s3_timestamp_is_valid_iso8601(s3_client_setup):
    """O timestamp de coleta deve ser um ISO8601 válido em UTC —
    necessário para reconstrução cronológica da cadeia de custódia."""
    resultado = collect_from_s3(BUCKET_TESTE, CHAVE_TESTE)
    # Deve ser parseável sem exceção
    parsed = datetime.fromisoformat(resultado["collected_at"])
    assert parsed.tzinfo is not None  # timestamp deve ter timezone explícito


def test_collect_from_s3_nonexistent_key_raises_error(s3_client_setup):
    """Tentar coletar uma chave inexistente deve falhar de forma
    explícita — silenciar esse erro mascararia falha real de coleta."""
    with pytest.raises(Exception):
        collect_from_s3(BUCKET_TESTE, "chave-que-nao-existe.txt")
