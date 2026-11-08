"""
Prepara o container Docker do Cenario C2 (mensagens) com a conversa SINTETICA
(suspeita ou de controle), de forma reprodutivel.

  poetry run python -m modulo_integracao.cenarios_simulacao.preparar_ambiente_c2 [--controle]

Cria (ou reinicia) o container 'container-msgs-c2' e grava /logs/conversa.txt.
A conversa e inventada (ver insumos_c4); nao ha conteudo real.
"""
import argparse
import subprocess

from modulo_integracao.cenarios_simulacao import insumos_c4 as insumos

CONTAINER = "container-msgs-c2"
ARQUIVO = "/logs/conversa.txt"
IMAGEM = "alpine:3"


def _estado(executar) -> str:
    """'ausente', 'parado' ou 'rodando'."""
    r = executar(["docker", "ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Status}}"],
                 capture_output=True, text=True)
    status = r.stdout.strip()
    if not status:
        return "ausente"
    return "rodando" if status.startswith("Up") else "parado"


def preparar_container_c2(controle: bool = False, executar=subprocess.run) -> str:
    """Garante o container em execucao e grava a conversa. Retorna a acao feita."""
    estado = _estado(executar)
    if estado == "ausente":
        executar(["docker", "run", "-d", "--name", CONTAINER, IMAGEM, "sleep", "infinity"],
                 capture_output=True, text=True, check=True)
    elif estado == "parado":
        executar(["docker", "start", CONTAINER], capture_output=True, text=True, check=True)
    executar(["docker", "exec", "-i", CONTAINER, "sh", "-c", f"mkdir -p /logs && cat > {ARQUIVO}"],
             input=insumos.conversa(controle), capture_output=True, text=True, check=True)
    return {"ausente": "criado", "parado": "reiniciado", "rodando": "reutilizado"}[estado]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--controle", action="store_true")
    acao = preparar_container_c2(parser.parse_args().controle)
    print(f"Container {CONTAINER} {acao}; conversa gravada em {ARQUIVO}")
