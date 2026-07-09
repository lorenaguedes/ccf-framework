"""
Conector de coleta forense — AWS (via LocalStack).

Coleta objetos de buckets S3, calculando hash de integridade no momento
da coleta, conforme RNF01 (Tabela 11, PGT) e RF de Coleta Multi-Nuvem.

Referência normativa: ISO/IEC 27037:2012 §7 — preservação da cadeia de
custódia desde o momento da identificação/coleta da evidência digital.
"""
import os
from datetime import datetime, timezone

import boto3

from modulo_coleta.hashing import calculate_hashes

# Endpoint do LocalStack — configurável via variável de ambiente para
# permitir, no futuro, apontar para AWS real sem alterar código
# (apenas configuração), mantendo o princípio de separação entre
# código e ambiente.
LOCALSTACK_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")


def get_s3_client():
    """Cria e retorna um client boto3 apontando para o LocalStack.

    Usa credenciais fictícias (LocalStack não valida credenciais reais
    por padrão), evitando qualquer risco de uso acidental contra a AWS
    de produção.

    Returns:
        Cliente boto3 S3 configurado para o endpoint local.
    """
    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def collect_from_s3(bucket: str, key: str) -> dict:
    """Coleta um objeto do S3 (via LocalStack), calculando hashes de
    integridade no momento da coleta.

    Args:
        bucket: nome do bucket S3.
        key: chave (caminho) do objeto dentro do bucket.

    Returns:
        Dicionário com estrutura de evidência forense:
        - bucket, key: identificação da origem
        - cloud_provider: "aws" (para rastreabilidade multi-nuvem)
        - hashes: dict com sha256 e md5
        - size_bytes: tamanho do conteúdo coletado
        - collected_at: timestamp ISO8601 em UTC do momento da coleta

    Raises:
        Exception: se o objeto não existir ou a coleta falhar (erro do
            boto3/ClientError é propagado sem tratamento silencioso —
            falha de coleta deve ser sempre visível e auditável).
    """
    client = get_s3_client()

    response = client.get_object(Bucket=bucket, Key=key)
    conteudo = response["Body"].read()

    hashes = calculate_hashes(conteudo)

    return {
        "bucket": bucket,
        "key": key,
        "cloud_provider": "aws",
        "hashes": hashes,
        "size_bytes": len(conteudo),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
