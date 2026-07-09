"""
Conector de coleta forense — GCP (via fake-gcs-server).

Coleta objetos de buckets Google Cloud Storage, calculando hash de
integridade no momento da coleta, conforme RNF01 e RF de Coleta
Multi-Nuvem (Tabela 10/11, PGT).

Nota técnica: o SDK google-cloud-storage é projetado para o GCS real,
sem suporte nativo trivial a endpoint customizado. Contornamos isso
configurando client_options com api_endpoint apontando para o
fake-gcs-server, e desabilitando autenticação real via credenciais
anônimas — abordagem padrão documentada pelo próprio fake-gcs-server.

Referência normativa: ISO/IEC 27037:2012 §7.
"""
import os
from datetime import datetime, timezone

from google.auth.credentials import AnonymousCredentials
from google.cloud import storage

from modulo_coleta.hashing import calculate_hashes

FAKE_GCS_ENDPOINT = os.environ.get("GCS_ENDPOINT_URL", "http://localhost:4443")


def get_gcs_client() -> storage.Client:
    """Cria e retorna um client do Google Cloud Storage apontando para
    o fake-gcs-server, usando credenciais anônimas (o emulador não
    valida autenticação real).

    Returns:
        Cliente storage.Client configurado para o endpoint local.
    """
    return storage.Client(
        credentials=AnonymousCredentials(),
        project="ccf-project",
        client_options={"api_endpoint": FAKE_GCS_ENDPOINT},
    )


def collect_from_gcs(bucket: str, blob_name: str) -> dict:
    """Coleta um objeto do Google Cloud Storage (via fake-gcs-server),
    calculando hashes de integridade no momento da coleta.

    Args:
        bucket: nome do bucket GCS.
        blob_name: nome do objeto (blob) dentro do bucket.

    Returns:
        Dicionário com estrutura de evidência forense, consistente com
        aws_collector e azure_collector:
        - bucket, blob_name: identificação da origem
        - cloud_provider: "gcp"
        - hashes: dict com sha256 e md5
        - size_bytes: tamanho do conteúdo coletado
        - collected_at: timestamp ISO8601 em UTC

    Raises:
        Exception: se o objeto não existir ou a coleta falhar.
    """
    client = get_gcs_client()
    bucket_ref = client.bucket(bucket)
    blob = bucket_ref.blob(blob_name)

    conteudo = blob.download_as_bytes()

    hashes = calculate_hashes(conteudo)

    return {
        "bucket": bucket,
        "blob_name": blob_name,
        "cloud_provider": "gcp",
        "hashes": hashes,
        "size_bytes": len(conteudo),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
