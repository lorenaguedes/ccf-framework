"""Preparo do container do C2 (executor Docker injetado)."""
from types import SimpleNamespace

from modulo_integracao.cenarios_simulacao import insumos_c4 as insumos
from modulo_integracao.cenarios_simulacao.preparar_ambiente_c2 import preparar_container_c2


def _docker(status):
    chamadas = []

    def executar(cmd, **kw):
        chamadas.append((cmd, kw))
        return SimpleNamespace(returncode=0, stdout=status, stderr="")
    return executar, chamadas


def test_cria_container_ausente_e_grava_conversa_suspeita():
    executar, chamadas = _docker("")
    assert preparar_container_c2(False, executar) == "criado"
    assert any(c[0][:3] == ["docker", "run", "-d"] for c in chamadas)
    assert chamadas[-1][1]["input"] == insumos.CONVERSA_SUSPEITA


def test_reinicia_parado_e_grava_conversa_de_controle():
    executar, chamadas = _docker("Exited (0) 2 hours ago")
    assert preparar_container_c2(True, executar) == "reiniciado"
    assert chamadas[-1][1]["input"] == insumos.CONVERSA_NORMAL


def test_reutiliza_em_execucao():
    executar, chamadas = _docker("Up 3 minutes")
    assert preparar_container_c2(False, executar) == "reutilizado"
    assert not any(c[0][:2] in (["docker", "run"], ["docker", "start"]) for c in chamadas)
