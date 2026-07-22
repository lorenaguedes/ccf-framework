"""
Orquestrador do Cenario C3 - Operacao Combinada em Multi-Nuvem
(Tabela 16, PGT).

Pipeline: coleta multi-nuvem (AWS + GCP + Azure) -> correlacao de
evidencias -> registro individual de cada evidencia na blockchain.

Criterio de sucesso (Tabela 16): pipeline end-to-end sem erros
criticos, correlacao de evidencias de 3 CSPs no mesmo laudo, cadeia de
custodia verificavel por auditoria. Resiliencia parcial: falha em um
CSP nao deve impedir a coleta e registro dos demais.
"""
from typing import Callable


def executar_cenario_c3(
    aws_collector_fn: Callable[[str, str], dict],
    gcp_collector_fn: Callable[[str, str], dict],
    azure_collector_fn: Callable[[str, str], dict],
    custody_register_fn: Callable[[str, str, dict], dict],
) -> dict:
    """Executa o pipeline completo do Cenario C3: coleta paralela de
    evidencias de 3 provedores de nuvem distintos, correlacao das
    evidencias coletadas, e registro individual de cada uma na cadeia
    de custodia.

    Args:
        aws_collector_fn: funcao de coleta AWS (LocalStack S3).
        gcp_collector_fn: funcao de coleta GCP (fake-gcs-server).
        azure_collector_fn: funcao de coleta Azure (Azurite).
        custody_register_fn: funcao de registro na blockchain,
            chamada uma vez para cada evidencia coletada com sucesso.

    Returns:
        Dicionario com:
        - evidencias: lista de evidencias coletadas com sucesso
        - registros_custodia: lista de registros de custodia gerados
        - correlacao: metadados de correlacao (total de CSPs
          envolvidos, provedores presentes)
        - erros_por_provider: dict de erros ocorridos, por provedor
        - status_pipeline: "SUCESSO" (todos os 3 CSPs coletados),
          "SUCESSO_PARCIAL" (pelo menos 1 falhou, mas ao menos 1
          teve sucesso), ou "FALHA" (todos falharam)
    """
    coletores = {
        "aws": lambda: aws_collector_fn("ccf-evidence-bucket", "evidencia-c3.jpg"),
        "gcp": lambda: gcp_collector_fn("ccf-evidence-bucket-gcp", "log-acesso-c3.json"),
        "azure": lambda: azure_collector_fn("ccf-evidence-container", "metadados-conta-c3.json"),
    }

    evidencias = []
    erros_por_provider = {}

    for provider, coletar in coletores.items():
        try:
            evidencia = coletar()
            evidencias.append(evidencia)
        except Exception as e:
            erros_por_provider[provider] = str(e)

    registros_custodia = []
    for evidencia in evidencias:
        registro = custody_register_fn(
            f"evid-c3-{evidencia['cloud_provider']}",
            evidencia["hashes"]["sha256"],
            evidencia,
        )
        registros_custodia.append(registro)

    providers_coletados = {ev["cloud_provider"] for ev in evidencias}

    if len(evidencias) == 3:
        status = "SUCESSO"
    elif len(evidencias) > 0:
        status = "SUCESSO_PARCIAL"
    else:
        status = "FALHA"

    return {
        "evidencias": evidencias,
        "registros_custodia": registros_custodia,
        "correlacao": {
            "total_csps_envolvidos": len(providers_coletados),
            "providers_presentes": sorted(providers_coletados),
        },
        "erros_por_provider": erros_por_provider,
        "status_pipeline": status,
    }