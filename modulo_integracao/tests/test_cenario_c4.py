"""
Testes do orquestrador do Cenario C4 (caso multimodal), com coletores,
estagios de IA e custodia sinteticos: a logica de orquestracao, o gatilho
do E3, a avaliacao do caso e a resiliencia sao verificados sem modelos,
emuladores ou rede Fabric.
"""
from modulo_integracao.cenarios_simulacao.cenario_c4 import executar_cenario_c4


def _coleta(provedor, h, ident):
    return {"cloud_provider": provedor, "hashes": {"sha256": h * 64, "md5": "d" * 32},
            "collected_at": "2026-11-08T04:00:00+00:00", "blob_name": ident}


def _imagem():
    return _coleta("aws", "a", "img.jpg"), "IMG"


def _texto():
    return _coleta("azure", "b", "conversa.txt"), ["m1", "m2"]


def _logs():
    return _coleta("gcp", "c", "log.csv"), "REGISTROS"


class Casos:
    """Estagios sinteticos configuraveis, com contagem de chamadas."""

    def __init__(self, e1="NOMATCH", e2="SFW", e3="ADULTO", e4="NORMAL", e5="NORMAL"):
        self.cfg = dict(e1=e1, e2=e2, e3=e3, e4=e4, e5=e5)
        self.chamadas = []
        self.registros = []

    def triagem(self, img):
        self.chamadas.append("E1")
        return {"flag": self.cfg["e1"], "matched_id": None, "score_similaridade": 0.99}

    def explicito(self, img):
        self.chamadas.append("E2")
        return {"flag": self.cfg["e2"], "probabilidade_nsfw": 0.9}

    def idade(self, img):
        self.chamadas.append("E3")
        return {"flag": self.cfg["e3"], "idade_estimada": 10.0}

    def grooming(self, msgs):
        self.chamadas.append("E4")
        return {"flag": self.cfg["e4"], "score_grooming": 0.87, "trechos_relevantes": ["m1"]}

    def anomalias(self, regs):
        self.chamadas.append("E5")
        return {"flag": self.cfg["e5"], "n_registros": 8, "n_anomalos": 2}

    def custodia(self, eid, h, meta):
        self.registros.append((eid, h, meta))
        return {"status": "success", "evidence_id": eid, "hash": h}


def _executar(c, imagem=_imagem, texto=_texto, logs=_logs, custodia=None):
    return executar_cenario_c4(
        coletar_imagem=imagem, coletar_texto=texto, coletar_logs=logs,
        triagem_fn=c.triagem, explicito_fn=c.explicito, idade_fn=c.idade,
        grooming_fn=c.grooming, anomalias_fn=c.anomalias,
        custody_register_fn=custodia or c.custodia)


def test_caso_com_indicios_em_tres_modalidades_e_registrado_e_priorizado():
    c = Casos(e1="MATCH", e4="SUSPEITO", e5="ANOMALO")
    r = _executar(c)
    assert r["status_pipeline"] == "SUCESSO"
    assert r["avaliacao_caso"]["prioridade"] == "ALTA"
    assert r["avaliacao_caso"]["regra_aplicada"] == "R1"
    assert len(c.registros) == 3
    assert r["avaliacao_caso"]["avaliacao_incompleta"] is False


def test_caso_de_controle_benigno_nao_registra_custodia():
    c = Casos()
    r = _executar(c)
    assert r["avaliacao_caso"]["prioridade"] == "BAIXA"
    assert c.registros == []
    assert r["status_pipeline"] == "SUCESSO"


def test_e3_nao_roda_quando_o_e2_nao_sinaliza_nsfw():
    c = Casos(e2="SFW")
    r = _executar(c)
    assert "E3" not in c.chamadas
    e3 = r["evidencias"][0]["estagios"]["E3"]
    assert e3["executado"] is False and "E2" in e3["motivo"]


def test_e3_roda_quando_o_e2_sinaliza_nsfw_e_menor_gera_indicio_forte():
    c = Casos(e2="NSFW", e3="MENOR")
    r = _executar(c)
    assert "E3" in c.chamadas
    assert r["avaliacao_caso"]["regra_aplicada"] == "R1"
    assert r["avaliacao_caso"]["indicios"][0]["estagio"] == "E2+E3"


def test_custodia_recebe_a_modalidade_nos_metadados():
    c = Casos(e4="SUSPEITO")
    _executar(c)
    assert c.registros[0][2]["modalidade"] == "texto"


def test_falha_de_um_estagio_nao_derruba_o_caso_e_marca_avaliacao_incompleta():
    c = Casos(e4="SUSPEITO")

    def grooming_falha(msgs):
        raise RuntimeError("modelo indisponivel")
    r = executar_cenario_c4(
        coletar_imagem=_imagem, coletar_texto=_texto, coletar_logs=_logs,
        triagem_fn=c.triagem, explicito_fn=c.explicito, idade_fn=c.idade,
        grooming_fn=grooming_falha, anomalias_fn=c.anomalias, custody_register_fn=c.custodia)
    assert r["status_pipeline"] == "SUCESSO_PARCIAL"
    assert r["erros_estagio"] == {"E4": "modelo indisponivel"}
    texto = next(e for e in r["evidencias"] if e["modalidade"] == "texto")
    assert texto["estagios"]["E4"]["executado"] is False
    assert r["avaliacao_caso"]["avaliacao_incompleta"] is True
    assert "E4" in r["avaliacao_caso"]["pendencias"]
    assert {"E1", "E2", "E5"} <= set(c.chamadas)  # os demais estagios rodaram


def test_falha_de_coleta_de_uma_modalidade_e_reportada_e_o_caso_prossegue():
    c = Casos(e4="SUSPEITO")

    def logs_falha():
        raise ConnectionError("fake-gcs-server fora do ar")
    r = _executar(c, logs=logs_falha)
    assert r["status_pipeline"] == "SUCESSO_PARCIAL"
    assert "logs" in r["erros_coleta"]
    assert len(r["evidencias"]) == 2
    assert "coleta:logs" in r["avaliacao_caso"]["pendencias"]
    assert "E5" not in c.chamadas


def test_sem_nenhuma_evidencia_coletada_nao_ha_avaliacao():
    """Nao se afirma prioridade BAIXA para um caso que nao foi analisado."""
    c = Casos()

    def falha():
        raise ConnectionError("fora do ar")
    r = _executar(c, imagem=falha, texto=falha, logs=falha)
    assert r["status_pipeline"] == "FALHA"
    assert r["avaliacao_caso"] is None
    assert c.chamadas == []


def test_falha_de_custodia_de_uma_evidencia_nao_impede_as_demais():
    c = Casos(e4="SUSPEITO", e5="ANOMALO")

    def custodia(eid, h, meta):
        if meta["modalidade"] == "logs":
            raise RuntimeError("rede Fabric inacessivel")
        return c.custodia(eid, h, meta)
    r = _executar(c, custodia=custodia)
    assert r["status_pipeline"] == "SUCESSO_PARCIAL"
    assert list(r["erros_custodia"]) == ["logs"]
    assert len(c.registros) == 1
    texto = next(e for e in r["evidencias"] if e["modalidade"] == "texto")
    assert texto["registro_custodia"]["status"] == "success"
