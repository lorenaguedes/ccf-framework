"""
Orquestrador do Cenario C1 - Distribuicao de CSAM em Storage S3
(Tabela 16, PGT).

Pipeline: Coleta -> Hash Perceptual -> CNN -> XAI -> Blockchain

Estrategia de design: os componentes de infraestrutura (coletor,
classificador, registrador de custodia) sao recebidos por injecao de
dependencia, permitindo testar a logica de orquestracao com
componentes sinteticos, sem exigir LocalStack ou a rede Fabric
rodando durante o desenvolvimento local.
"""
from typing import Callable


def executar_cenario_c1(
    bucket: str,
    key: str,
    conteudo: bytes,
    collector_fn: Callable[[str, str], dict],
    classifier_fn: Callable[[bytes], dict],
    custody_register_fn: Callable[[str, str, dict], dict],
) -> dict:
    """Executa o pipeline completo do Cenario C1: coleta de um objeto
    S3, classificacao de conteudo explicito, e registro condicional
    na cadeia de custodia.

    Args:
        bucket: nome do bucket S3 (LocalStack).
        key: chave do objeto a ser investigado.
        conteudo: conteudo bruto do objeto (para classificacao).
        collector_fn: funcao de coleta (ex: aws_collector.collect_from_s3).
        classifier_fn: funcao de classificacao (ex:
            visao_computacional.classify_explicit_content, adaptada
            para receber apenas o conteudo).
        custody_register_fn: funcao de registro na blockchain (ex:
            invocacao do chaincode RegistrarEvidencia).

    Returns:
        Dicionario com o resultado de cada etapa do pipeline:
        - coleta: resultado da coleta (ou None se falhou)
        - classificacao: resultado da classificacao (ou None se falhou)
        - registro_custodia: resultado do registro (ou None se
          conteudo nao for NSFW, ou se a etapa nao foi alcancada)
        - status_pipeline: "SUCESSO" ou "FALHA"
        - erro: mensagem de erro, presente apenas se status for FALHA
    """
    resultado = {
        "coleta": None,
        "classificacao": None,
        "registro_custodia": None,
        "status_pipeline": None,
    }

    try:
        resultado["coleta"] = collector_fn(bucket, key)
    except Exception as e:
        resultado["status_pipeline"] = "FALHA"
        resultado["erro"] = f"Falha na etapa de coleta: {e}"
        return resultado

    try:
        resultado["classificacao"] = classifier_fn(conteudo)
    except Exception as e:
        resultado["status_pipeline"] = "FALHA"
        resultado["erro"] = f"Falha na etapa de classificacao: {e}"
        return resultado

    if resultado["classificacao"]["flag"] == "NSFW":
        try:
            resultado["registro_custodia"] = custody_register_fn(
                key,
                resultado["coleta"]["hashes"]["sha256"],
                resultado["coleta"],
            )
        except Exception as e:
            resultado["status_pipeline"] = "FALHA"
            resultado["erro"] = f"Falha no registro de custodia: {e}"
            return resultado

    resultado["status_pipeline"] = "SUCESSO"
    return resultado