"""
Prepara os emuladores multi-nuvem com as evidencias SINTETICAS usadas nos
cenarios C1 e C3 (nenhum conteudo real ou explicito).

Os emuladores (LocalStack, Azurite e fake-gcs-server) nao persistem dados
entre reinicios, entao este script deve ser executado antes dos cenarios:

  poetry run python -m modulo_integracao.cenarios_simulacao.preparar_ambiente_c1_c3

Evidencias criadas (idempotente):
- AWS S3  ccf-evidence-bucket/evidencia-c1-real.jpg: imagem JPEG neutra
  (cor solida, 224x224), gerada de forma deterministica;
- GCS     ccf-evidence-bucket-gcp/evidencia-teste-integracao.txt;
- Azure   ccf-evidence-container/evidencia-teste-integracao.txt.
"""
import io

import requests
from azure.storage.blob import BlobServiceClient
from PIL import Image

from modulo_coleta.aws_collector import get_s3_client
from modulo_coleta.azure_collector import AZURITE_CONNECTION_STRING

BUCKET_S3 = "ccf-evidence-bucket"
KEY_S3 = "evidencia-c1-real.jpg"
BUCKET_GCS = "ccf-evidence-bucket-gcp"
BLOB_GCS = "evidencia-teste-integracao.txt"
CONTEUDO_GCS = b"conteudo de evidencia simulada para teste gcp"
CONTAINER_AZURE = "ccf-evidence-container"
BLOB_AZURE = "evidencia-teste-integracao.txt"
CONTEUDO_AZURE = b"conteudo de evidencia simulada para teste azure"
GCS_ENDPOINT = "http://localhost:4443"


def imagem_neutra() -> bytes:
    """JPEG sintetico de cor solida, sem qualquer conteudo de pessoas."""
    buf = io.BytesIO()
    Image.new("RGB", (224, 224), (100, 150, 200)).save(buf, "JPEG")
    return buf.getvalue()


def main():
    s3 = get_s3_client()
    if BUCKET_S3 not in [b["Name"] for b in s3.list_buckets()["Buckets"]]:
        s3.create_bucket(Bucket=BUCKET_S3)
    s3.put_object(Bucket=BUCKET_S3, Key=KEY_S3, Body=imagem_neutra())
    print(f"AWS   : s3://{BUCKET_S3}/{KEY_S3}")

    requests.post(f"{GCS_ENDPOINT}/storage/v1/b?project=ccf-project", json={"name": BUCKET_GCS})
    requests.post(
        f"{GCS_ENDPOINT}/upload/storage/v1/b/{BUCKET_GCS}/o?uploadType=media&name={BLOB_GCS}",
        data=CONTEUDO_GCS,
    ).raise_for_status()
    print(f"GCP   : gs://{BUCKET_GCS}/{BLOB_GCS}")

    azure = BlobServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
    container = azure.get_container_client(CONTAINER_AZURE)
    if not container.exists():
        container.create_container()
    container.upload_blob(BLOB_AZURE, CONTEUDO_AZURE, overwrite=True)
    print(f"Azure : {CONTAINER_AZURE}/{BLOB_AZURE}")


if __name__ == "__main__":
    main()
