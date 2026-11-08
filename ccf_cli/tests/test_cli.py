"""Testes da CLI com executor injetado (sem Docker, Fabric ou modelos)."""
import json
from types import SimpleNamespace

import pytest

from ccf_cli import cli


class Falso:
    """Executor falso: registra chamadas e devolve saidas programadas."""

    def __init__(self, saidas=None, falha_em=None):
        self.chamadas, self.saidas, self.falha_em = [], saidas or {}, falha_em

    def __call__(self, cmd, **kw):
        self.chamadas.append(cmd)
        chave = " ".join(map(str, cmd[:3]))
        rc = 1 if self.falha_em and self.falha_em in " ".join(map(str, cmd)) else 0
        return SimpleNamespace(returncode=rc, stdout=self.saidas.get(chave, ""), stderr="")


def test_cenario_c4_controle_gera_comando():
    f = Falso()
    assert cli.main(["cenario", "c4", "--controle"], f) == 0
    assert f.chamadas == [["poetry", "run", "python", "-m",
                           "modulo_integracao.cenarios_simulacao.executar_c4_real", "--controle"]]


def test_cenario_c1_forcado():
    cmds = cli.comandos_cenario("c1", forcado=True)
    assert cmds[0][-1] == "--validar-ramo-nsfw"


def test_cenario_c2_prepara_antes_de_executar():
    cmds = cli.comandos_cenario("c2", controle=True)
    assert "preparar_ambiente_c2" in cmds[0][4] and "executar_c2_real" in cmds[1][4]
    assert cmds[0][-1] == cmds[1][-1] == "--controle"


def test_todos_executa_seis_cenarios_e_interrompe_na_falha():
    f = Falso()
    cli.main(["cenario", "todos"], f)
    assert len(f.chamadas) == 7  # c2 tem 2 comandos
    f = Falso(falha_em="executar_c1_real")
    assert cli.main(["cenario", "todos"], f) == 1
    assert len(f.chamadas) == 1


def test_status_detecta_chaincode_desatualizado(tmp_path):
    saidas = {"docker ps --format": "localstack\nazurite\nfake-gcs-server\npeer0.org1.example.com\n",
              "peer lifecycle chaincode": "Committed chaincode definition: Version: 1.0, Sequence: 1, Endorsement"}
    itens = cli.verificar_status(Falso(saidas), tmp_path)
    cc = next(i for i in itens if i[0] == "chaincode custody")
    assert cc[1] is False and "1.0" in cc[2] and "esperada 2.0" in cc[2]


def test_status_ok_com_chaincode_v2(tmp_path):
    saidas = {"docker ps --format": "localstack\nazurite\nfake-gcs-server\npeer0.org1.example.com\n",
              "peer lifecycle chaincode": "Version: 2.0, Sequence: 2, Endorsement Plugin: escc"}
    itens = cli.verificar_status(Falso(saidas), tmp_path)
    assert all(ok for r, ok, _ in itens if not r.startswith("log "))


def test_status_sem_docker_retorna_falha(capsys):
    assert cli.main(["status"], Falso()) == 1
    assert "ambiente up" in capsys.readouterr().out


def test_demo_aborta_se_infra_incompleta():
    f = Falso()
    assert cli.main(["demo"], f) == 1
    assert not any("executar_c4_real" in " ".join(c) for c in f.chamadas)


def test_resumo_le_logs(tmp_path):
    (tmp_path / "cenario_c4_execucao.json").write_text(json.dumps(
        {"cenario": "C4", "modo": "caso", "executado_em": "2026-11-08T10:00:00+00:00",
         "resultado": {"avaliacao_caso": {"prioridade": "ALTA"}}}))
    (tmp_path / "quebrado.json").write_text("{")
    linhas = cli.resumo_logs(tmp_path)
    assert any("ALTA" in l[3] for l in linhas) and any(l[3] == "log ilegivel" for l in linhas)


def _deploy(f):
    return next(c for c in f.chamadas if "deployCC" in c)


def test_fabric_deploy_atualizacao_usa_sequencia_seguinte():
    f = Falso({"peer lifecycle chaincode": "Version: 1.0, Sequence: 1, Endorsement"})
    cli.main(["fabric", "deploy"], f)
    cmd = _deploy(f)
    assert cmd[cmd.index("-ccv") + 1] == "2.0" and cmd[cmd.index("-ccs") + 1] == "2"


def test_fabric_iniciar_em_rede_nova_usa_sequencia_1():
    f = Falso()  # nada implantado: querycommitted sem saida
    cli.main(["fabric", "iniciar"], f)
    cmd = _deploy(f)
    assert cmd[cmd.index("-ccv") + 1] == "2.0" and cmd[cmd.index("-ccs") + 1] == "1"


def test_acao_invalida_rejeitada():
    with pytest.raises(SystemExit):
        cli.main(["fabric", "explodir"], Falso())


def test_cenario_custodia_gera_comando():
    f = Falso()
    assert cli.main(["cenario", "custodia"], f) == 0
    assert f.chamadas[0][-1].endswith("executar_custodia_completa_real")
