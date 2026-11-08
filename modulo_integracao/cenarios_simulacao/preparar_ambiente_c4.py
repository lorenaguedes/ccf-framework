"""
Prepara os emuladores com as evidencias SINTETICAS do Cenario C4 (caso
multimodal) e do seu caso de controle benigno.

Execute depois de subir os emuladores (os dados nao persistem entre
reinicios) e antes do C4:

  poetry run python -m modulo_integracao.cenarios_simulacao.preparar_ambiente_c4

Evidencias criadas (idempotente):
- AWS S3  ccf-evidence-bucket:  evidencia-c4-imagem.jpg (caso) e
                                evidencia-c4-imagem-controle.jpg (controle);
- Azure   ccf-evidence-container: conversa-c4.txt e conversa-c4-controle.txt;
- GCS     ccf-evidence-bucket-gcp: log-acesso-c4.csv e log-acesso-c4-controle.csv.

Todo o conteudo e sintetico (ver insumos_c4).
"""
import requests
from azure.storage.blob import BlobServiceClient

from modulo_coleta.aws_collector import get_s3_client
from modulo_coleta.azure_collector import AZURITE_CONNECTION_STRING
from modulo_integracao.cenarios_simulacao import insumos_c4 as insumos
from modulo_integracao.cenarios_simulacao.preparar_ambiente_c1_c3 import (
    BUCKET_GCS,
    BUCKET_S3,
    CONTAINER_AZURE,
    GCS_ENDPOINT,
    aguardar_localstack,
)

# (nome no armazenamento) para o caso e para o controle
KEY_IMAGEM = {False: "evidencia-c4-imagem.jpg", True: "evidencia-c4-imagem-controle.jpg"}
BLOB_TEXTO = {False: "conversa-c4.txt", True: "conversa-c4-controle.txt"}
BLOB_LOGS = {False: "log-acesso-c4.csv", True: "log-acesso-c4-controle.csv"}


def imagem_do_caso(controle: bool) -> bytes:
    semente = insumos.SEMENTE_PADRAO_CONTROLE if controle else insumos.SEMENTE_PADRAO
    return insumos.jpeg_bytes(insumos.imagem_padrao_sintetica(semente))


def main():
    s3 = get_s3_client()
    aguardar_localstack(s3)
    if BUCKET_S3 not in [b["Name"] for b in s3.list_buckets()["Buckets"]]:
        s3.create_bucket(Bucket=BUCKET_S3)
    requests.post(f"{GCS_ENDPOINT}/storage/v1/b?project=ccf-project", json={"name": BUCKET_GCS})
    azure = BlobServiceClient.from_connection_string(AZURITE_CONNECTION_STRING)
    container = azure.get_container_client(CONTAINER_AZURE)
    if not container.exists():
        container.create_container()

    for controle in (False, True):
        rotulo = "controle" if controle else "caso"
        s3.put_object(Bucket=BUCKET_S3, Key=KEY_IMAGEM[controle], Body=imagem_do_caso(controle))
        container.upload_blob(BLOB_TEXTO[controle], insumos.conversa(controle).encode("utf-8"),
                              overwrite=True)
        requests.post(
            f"{GCS_ENDPOINT}/upload/storage/v1/b/{BUCKET_GCS}/o?uploadType=media&name={BLOB_LOGS[controle]}",
            data=insumos.logs_csv(controle),
        ).raise_for_status()
        print(f"[{rotulo}] AWS {KEY_IMAGEM[controle]} | Azure {BLOB_TEXTO[controle]} | GCP {BLOB_LOGS[controle]}")


if __name__ == "__main__":
    main()
