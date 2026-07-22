"""
Conector de coleta forense - Containers Docker.

Coleta logs de conversas de containers Docker em execucao, conforme
RF03 (Tabela 10, PGT): "Suportar coleta de logs de containers Docker e
pods Kubernetes em execucao."

Referencia normativa: RFC 3227 (IETF, 2002).
"""
import subprocess
from datetime import datetime, timezone

from modulo_coleta.hashing import calculate_hashes


def collect_from_docker_log(container_id: str, log_path: str) -> dict:
    """Coleta o conteudo de um arquivo de log de dentro de um
    container Docker em execucao, calculando hashes de integridade no
    momento da coleta.

    Args:
        container_id: nome ou ID do container Docker.
        log_path: caminho do arquivo de log dentro do container.

    Returns:
        Dicionario com estrutura de evidencia forense, consistente
        com os demais conectores (aws_collector, azure_collector,
        gcp_collector):
        - container_id, log_path: identificacao da origem
        - cloud_provider: "docker"
        - hashes: dict com sha256 e md5
        - size_bytes: tamanho do conteudo coletado
        - collected_at: timestamp ISO8601 em UTC
        - conteudo_texto: texto bruto coletado (necessario para
          alimentar o classificador de grooming)

    Raises:
        subprocess.CalledProcessError: se o container nao existir ou
            o arquivo de log nao puder ser lido.
    """
    resultado = subprocess.run(
        ["docker", "exec", container_id, "cat", log_path],
        capture_output=True,
        check=True,
        text=True,
    )
    conteudo_texto = resultado.stdout
    conteudo_bytes = conteudo_texto.encode("utf-8")

    hashes = calculate_hashes(conteudo_bytes)

    return {
        "container_id": container_id,
        "log_path": log_path,
        "cloud_provider": "docker",
        "hashes": hashes,
        "size_bytes": len(conteudo_bytes),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "conteudo_texto": conteudo_texto,
    }