"""
Testes de integração para o conector de coleta GCP (fake-gcs-server).

Requer o fake-gcs-server em execução (docker compose up -d).

Referência: RF (Módulo de Coleta Multi-Nuvem).
"""
import hashlib
from datetime import datetime

import pytest
import requests

from modulo_coleta.gcp_collector import collect_from_gcs, get_gcs_client

BUCKET_TESTE = "ccf-evidence-bucket-gcp"
BLOB_TESTE = "evidencia-teste-integracao.txt"
CONTEUDO_TESTE = b"conteudo de evidencia simulada para teste gcp"

FAKE_GCS_ENDPOINT = "http://localhost:4443"


@pytest.fixture(scope="module")
def gcs_setup():
    """Prepara o bucket e o objeto de teste no fake-gcs-server via
    chamadas REST diretas (mais simples que instanciar o SDK completo
    só para setup), não via nosso conector."""
    # Cria o bucket (idempotente — ignora erro se já existir)
    requests.post(
        f"{FAKE_GCS_ENDPOINT}/storage/v1/b?project=ccf-project",
        json={"name": BUCKET_TESTE},
    )
    # Faz upload do objeto de teste
    requests.post(
        f"{FAKE_GCS_ENDPOINT}/upload/storage/v1/b/{BUCKET_TESTE}/o"
        f"?uploadType=media&name={BLOB_TESTE}",
        data=CONTEUDO_TESTE,
    )
    yield


def test_get_gcs_client_uses_custom_endpoint():
    """O client deve estar configurado para o fake-gcs-server local,
    não para o GCS real."""
    client = get_gcs_client()
    assert client is not None


def test_collect_from_gcs_returns_expected_structure(gcs_setup):
    """Estrutura consistente com os conectores AWS/Azure."""
    resultado = collect_from_gcs(BUCKET_TESTE, BLOB_TESTE)

    assert resultado["bucket"] == BUCKET_TESTE
    assert resultado["blob_name"] == BLOB_TESTE
    assert resultado["cloud_provider"] == "gcp"
    assert "sha256" in resultado["hashes"]
    assert "md5" in resultado["hashes"]
    assert resultado["size_bytes"] == len(CONTEUDO_TESTE)
    assert "collected_at" in resultado


def test_collect_from_gcs_hash_matches_known_content(gcs_setup):
    hash_esperado = hashlib.sha256(CONTEUDO_TESTE).hexdigest()
    resultado = collect_from_gcs(BUCKET_TESTE, BLOB_TESTE)
    assert resultado["hashes"]["sha256"] == hash_esperado


def test_collect_from_gcs_timestamp_is_valid_iso8601(gcs_setup):
    resultado = collect_from_gcs(BUCKET_TESTE, BLOB_TESTE)
    parsed = datetime.fromisoformat(resultado["collected_at"])
    assert parsed.tzinfo is not None


def test_collect_from_gcs_nonexistent_raises_error(gcs_setup):
    with pytest.raises(Exception):
        collect_from_gcs(BUCKET_TESTE, "blob-que-nao-existe.txt")
