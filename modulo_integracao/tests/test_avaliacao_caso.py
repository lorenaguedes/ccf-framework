"""
Testes da avaliacao de caso multimodal (regras R1 a R4): cada regra, os
casos em que um indicio NAO deve ser gerado e a marcacao de avaliacao
incompleta.
"""
from modulo_integracao.avaliacao_caso import avaliar_caso, extrair_indicios


def _imagem(e1="NOMATCH", e2="SFW", e3=None, **extra):
    estagios = {
        "E1": {"executado": True, "flag": e1, "score_similaridade": 0.97},
        "E2": {"executado": True, "flag": e2, "probabilidade_nsfw": 0.91},
    }
    estagios["E3"] = ({"executado": True, "flag": e3, "idade_estimada": 12.0} if e3
                      else {"executado": False, "motivo": "nao aplicado"})
    estagios.update(extra)
    return {"modalidade": "imagem", "estagios": estagios}


def _texto(flag="NORMAL"):
    return {"modalidade": "texto",
            "estagios": {"E4": {"executado": True, "flag": flag, "score_grooming": 0.87}}}


def _logs(flag="NORMAL"):
    return {"modalidade": "logs",
            "estagios": {"E5": {"executado": True, "flag": flag, "n_anomalos": 2, "n_registros": 8}}}


def test_r1_hash_perceptual_com_correspondencia_e_indicio_forte():
    a = avaliar_caso([_imagem(e1="MATCH"), _texto(), _logs()])
    assert (a["prioridade"], a["regra_aplicada"]) == ("ALTA", "R1")
    assert a["indicios"][0]["forca"] == "forte"


def test_r1_nsfw_confirmado_por_menor_e_forte():
    a = avaliar_caso([_imagem(e2="NSFW", e3="MENOR")])
    assert (a["prioridade"], a["regra_aplicada"]) == ("ALTA", "R1")
    assert a["indicios"][0]["estagio"] == "E2+E3"


def test_nsfw_com_adulto_e_apenas_moderado():
    a = avaliar_caso([_imagem(e2="NSFW", e3="ADULTO")])
    assert (a["prioridade"], a["regra_aplicada"]) == ("MEDIA", "R3")


def test_menor_sem_conteudo_explicito_nao_e_indicio():
    """A presenca de um menor numa imagem nao e, por si so, suspeita."""
    a = avaliar_caso([_imagem(e2="SFW", e3="MENOR")])
    assert a["indicios"] == []
    assert a["prioridade"] == "BAIXA"


def test_r3_texto_suspeito_isolado_e_media():
    a = avaliar_caso([_imagem(), _texto("SUSPEITO"), _logs()])
    assert (a["prioridade"], a["regra_aplicada"]) == ("MEDIA", "R3")
    assert a["modalidades_com_indicio"] == ["texto"]


def test_r4_anomalia_de_logs_isolada_nao_eleva_a_prioridade():
    a = avaliar_caso([_imagem(), _texto(), _logs("ANOMALO")])
    assert (a["prioridade"], a["regra_aplicada"]) == ("BAIXA", "R4")
    assert a["indicios"][0]["forca"] == "contextual"  # listado, mas nao eleva


def test_r2_texto_suspeito_reforcado_por_anomalia_de_logs():
    a = avaliar_caso([_imagem(), _texto("SUSPEITO"), _logs("ANOMALO")])
    assert (a["prioridade"], a["regra_aplicada"]) == ("ALTA", "R2")
    assert a["modalidades_com_indicio"] == ["logs", "texto"]


def test_r2_imagem_nsfw_e_texto_suspeito():
    a = avaliar_caso([_imagem(e2="NSFW", e3="ADULTO"), _texto("SUSPEITO")])
    assert (a["prioridade"], a["regra_aplicada"]) == ("ALTA", "R2")


def test_r4_sem_nenhum_indicio():
    a = avaliar_caso([_imagem(), _texto(), _logs()])
    assert (a["prioridade"], a["regra_aplicada"]) == ("BAIXA", "R4")
    assert a["indicios"] == [] and a["avaliacao_incompleta"] is False


def test_estagio_nao_executado_e_ignorado():
    ev = {"modalidade": "imagem",
          "estagios": {"E1": {"executado": False, "flag": "MATCH", "motivo": "falha"}}}
    assert extrair_indicios(ev) == []


def test_pendencias_marcam_a_avaliacao_como_incompleta():
    a = avaliar_caso([_texto("SUSPEITO")], pendencias=["coleta:logs", "E2"])
    assert a["avaliacao_incompleta"] is True
    assert a["pendencias"] == ["coleta:logs", "E2"]
    assert a["prioridade"] == "MEDIA"


def test_toda_avaliacao_traz_a_ressalva_de_heuristica():
    a = avaliar_caso([_texto()])
    assert "heuristicas" in a["ressalva"] and "nao e probabilidade" in a["ressalva"]
