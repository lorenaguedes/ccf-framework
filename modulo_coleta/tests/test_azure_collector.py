"""
Testes de integração para o conector de coleta Azure (Azurite).

Requer o Azurite em execução (docker compose up -d). Segue o mesmo
padrão de teste de integração contra emulador real usado no
aws_collector, para consistência metodológica entre conectores.

Referência: RF (Módulo de Coleta Multi-Nuvem).
"""
import hashlib
from datetime import datetime

import pytest
from azure.storage.blob import BlobServiceClient

from modulo_coleta.azure_collector import collect_from_blob, get_blob_service_client

CONTAINER_TESTE = "ccf-evidence-container"
BLOB_TESTE = "evidencia-teste-integracao.txt"
CONTEUDO_TESTE = b"conteudo de evidencia simulada para teste azure"

# Connection string padrão do Azurite 
AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)


@pytest.fixture(scope="module")
def blob_setup():
    """Prepara o container e o blob de teste no Azurite diretamente via
    SDK, não via nosso conector — evita testar contra si mesmo."""
    client = BlobServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
    container_client = client.get_container_client(CONTAINER_TESTE)

    if not container_client.exists():
        container_client.create_container()

    container_client.upload_blob(BLOB_TESTE, CONTEUDO_TESTE, overwrite=True)
    yield client


def test_get_blob_service_client_returns_valid_client():
    """O client deve apontar para o Azurite local, não para uma conta
    Azure real."""
    client = get_blob_service_client()
    assert "127.0.0.1" in client.url or "localhost" in client.url


def test_collect_from_blob_returns_expected_structure(blob_setup):
    """O registro retornado deve conter todos os campos exigidos para
    rastreabilidade forense, no mesmo formato do conector AWS (garante
    consistência entre provedores para consumo posterior pelo módulo
    de blockchain)."""
    resultado = collect_from_blob(CONTAINER_TESTE, BLOB_TESTE)

    assert resultado["container"] == CONTAINER_TESTE
    assert resultado["blob_name"] == BLOB_TESTE
    assert resultado["cloud_provider"] == "azure"
    assert "sha256" in resultado["hashes"]
    assert "md5" in resultado["hashes"]
    assert resultado["size_bytes"] == len(CONTEUDO_TESTE)
    assert "collected_at" in resultado


def test_collect_from_blob_hash_matches_known_content(blob_setup):
    """Hash deve corresponder ao cálculo independente do conteúdo
    original."""
    hash_esperado = hashlib.sha256(CONTEUDO_TESTE).hexdigest()
    resultado = collect_from_blob(CONTAINER_TESTE, BLOB_TESTE)
    assert resultado["hashes"]["sha256"] == hash_esperado


def test_collect_from_blob_timestamp_is_valid_iso8601(blob_setup):
    """Timestamp deve ser ISO8601 com timezone explícito."""
    resultado = collect_from_blob(CONTAINER_TESTE, BLOB_TESTE)
    parsed = datetime.fromisoformat(resultado["collected_at"])
    assert parsed.tzinfo is not None


def test_collect_from_blob_nonexistent_raises_error(blob_setup):
    """Blob inexistente deve falhar de forma explícita."""
    with pytest.raises(Exception):
        collect_from_blob(CONTAINER_TESTE, "blob-que-nao-existe.txt")
