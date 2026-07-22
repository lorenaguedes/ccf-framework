"""
Orquestrador do Cenario C2 - Grooming em Plataforma de Mensagens
(Tabela 16, PGT).

Pipeline: Coleta Docker -> NLP BERT -> SHAP -> Blockchain

Mesma estrategia de injecao de dependencia do Cenario C1.
"""
from typing import Callable


def executar_cenario_c2(
    container_id: str,
    log_path: str,
    texto_conversa: str,
    collector_fn: Callable[[str, str], dict],
    grooming_classifier_fn: Callable[[str], dict],
    custody_register_fn: Callable[[str, str, dict], dict],
) -> dict:
    """Executa o pipeline completo do Cenario C2: coleta de logs de
    conversa via Docker, deteccao de grooming, e registro condicional
    na cadeia de custodia.

    Args:
        container_id: identificador do container Docker de origem.
        log_path: caminho do arquivo de log dentro do container.
        texto_conversa: conteudo textual da conversa a ser analisada.
        collector_fn: funcao de coleta de logs via Docker.
        grooming_classifier_fn: funcao de classificacao de grooming
            (ex: deteccao_grooming.classify_grooming).
        custody_register_fn: funcao de registro na blockchain.

    Returns:
        Dicionario com o resultado de cada etapa:
        - coleta: resultado da coleta (ou None se falhou)
        - classificacao_grooming: resultado da classificacao
        - registro_custodia: resultado do registro (ou None se
          conversa nao for suspeita)
        - status_pipeline: "SUCESSO" ou "FALHA"
        - erro: mensagem de erro, presente apenas se status for FALHA
    """
    resultado = {
        "coleta": None,
        "classificacao_grooming": None,
        "registro_custodia": None,
        "status_pipeline": None,
    }

    try:
        resultado["coleta"] = collector_fn(container_id, log_path)
    except Exception as e:
        resultado["status_pipeline"] = "FALHA"
        resultado["erro"] = f"Falha na etapa de coleta: {e}"
        return resultado

    try:
        resultado["classificacao_grooming"] = grooming_classifier_fn(texto_conversa)
    except Exception as e:
        resultado["status_pipeline"] = "FALHA"
        resultado["erro"] = f"Falha na etapa de classificacao de grooming: {e}"
        return resultado

    if resultado["classificacao_grooming"]["flag"] == "SUSPEITO":
        try:
            resultado["registro_custodia"] = custody_register_fn(
                log_path,
                resultado["coleta"]["hashes"]["sha256"],
                resultado["coleta"],
            )
        except Exception as e:
            resultado["status_pipeline"] = "FALHA"
            resultado["erro"] = f"Falha no registro de custodia: {e}"
            return resultado

    resultado["status_pipeline"] = "SUCESSO"
    return resultado