"""
Conector de coleta forense — Azure (via Azurite).

Coleta blobs de containers Azure Storage, calculando hash de
integridade no momento da coleta, conforme RNF01 e RF de Coleta
Multi-Nuvem (Tabela 10/11, PGT).

Referência normativa: ISO/IEC 27037:2012 §7.
"""
import os
from datetime import datetime, timezone

from azure.storage.blob import BlobServiceClient

from modulo_coleta.hashing import calculate_hashes

# Connection string padrão do Azurite — configurável via variável de
# ambiente para permitir, futuramente, apontar para Azure real sem
# alterar código.
AZURITE_CONNECTION_STRING = os.environ.get(
    "AZURE_STORAGE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;",
)


def get_blob_service_client() -> BlobServiceClient:
    """Cria e retorna um client do Azure Storage apontando para o
    Azurite (ou Azure real, se a variável de ambiente for sobrescrita).

    Returns:
        Cliente BlobServiceClient configurado.
    """
    return BlobServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)


def collect_from_blob(container: str, blob_name: str) -> dict:
    """Coleta um blob do Azure Storage (via Azurite), calculando
    hashes de integridade no momento da coleta.

    Args:
        container: nome do container Azure Storage.
        blob_name: nome do blob dentro do container.

    Returns:
        Dicionário com estrutura de evidência forense, no mesmo
        formato do aws_collector (consistência entre provedores):
        - container, blob_name: identificação da origem
        - cloud_provider: "azure"
        - hashes: dict com sha256 e md5
        - size_bytes: tamanho do conteúdo coletado
        - collected_at: timestamp ISO8601 em UTC

    Raises:
        Exception: se o blob não existir ou a coleta falhar — erro do
            SDK Azure é propagado sem tratamento silencioso.
    """
    client = get_blob_service_client()
    blob_client = client.get_blob_client(container=container, blob=blob_name)

    conteudo = blob_client.download_blob().readall()

    hashes = calculate_hashes(conteudo)

    return {
        "container": container,
        "blob_name": blob_name,
        "cloud_provider": "azure",
        "hashes": hashes,
        "size_bytes": len(conteudo),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
