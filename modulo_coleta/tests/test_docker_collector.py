"""
Testes de integracao para o conector de coleta Docker.

Requer um container Docker em execucao com um arquivo de log
acessivel (ver setup manual documentado no Cenario C2).
"""
import subprocess

import pytest

from modulo_coleta.docker_collector import collect_from_docker_log

CONTAINER_TESTE = "container-msgs-c2"
LOG_PATH_TESTE = "/logs/conversa.txt"


@pytest.fixture(scope="module")
def docker_container_setup():
    """Verifica que o container de teste existe antes dos testes."""
    resultado = subprocess.run(
        ["docker", "inspect", CONTAINER_TESTE],
        capture_output=True,
    )
    if resultado.returncode != 0:
        pytest.skip(f"Container '{CONTAINER_TESTE}' nao encontrado - pule ou crie manualmente")
    yield


def test_collect_from_docker_log_returns_expected_structure(docker_container_setup):
    resultado = collect_from_docker_log(CONTAINER_TESTE, LOG_PATH_TESTE)

    assert resultado["container_id"] == CONTAINER_TESTE
    assert resultado["cloud_provider"] == "docker"
    assert "sha256" in resultado["hashes"]
    assert "conteudo_texto" in resultado


def test_collect_from_docker_log_hash_matches_known_content(docker_container_setup):
    import hashlib

    resultado = collect_from_docker_log(CONTAINER_TESTE, LOG_PATH_TESTE)
    hash_esperado = hashlib.sha256(resultado["conteudo_texto"].encode("utf-8")).hexdigest()

    assert resultado["hashes"]["sha256"] == hash_esperado


def test_collect_from_docker_log_nonexistent_container_raises_error():
    with pytest.raises(subprocess.CalledProcessError):
        collect_from_docker_log("container-que-nao-existe", LOG_PATH_TESTE)