"""
Avaliacao de caso multimodal - prioridade de revisao pericial (Cenario C4).

Combina os resultados dos estagios de IA aplicados a evidencias de
modalidades diferentes (imagem, texto e logs de nuvem) em UMA prioridade
de revisao humana, por REGRAS EXPLICITAS E RASTREAVEIS.

Decisao de projeto - por que regras e nao uma soma de escores:
os escores dos estagios vem de modelos e conjuntos de dados distintos e
nao sao calibrados entre si (probabilidade NSFW, escore de aliciamento,
escore de anomalia). Somar ou ponderar esses valores produziria uma
precisao aparente sem validacao, e nao ha dados rotulados de casos
multimodais para ajustar ou avaliar uma fusao aprendida. As regras abaixo
sao uma heuristica de PRIORIZACAO, nao uma medida de probabilidade de
crime, e nao foram validadas empiricamente (ver secao 4.6 do PGT).

Forca dos indicios:
- forte:      E1 MATCH (correspondencia com base de referencia) ou
              E2 NSFW confirmado por E3 MENOR;
- moderado:   E2 NSFW isolado; E4 SUSPEITO;
- contextual: E5 ANOMALO (comportamento atipico de acesso: nao indica
              conteudo ilicito por si so).
E3 MENOR nunca e indicio isolado: a presenca de um menor numa imagem nao
e, em si, suspeita; ele apenas agrava um E2 NSFW.

Regras (aplicadas em ordem; a primeira que casa define a prioridade):
- R1 (ALTA):  existe ao menos um indicio forte;
- R2 (ALTA):  indicios em duas ou mais modalidades distintas, com ao menos
              um moderado ou forte (reforco entre modalidades);
- R3 (MEDIA): indicio moderado em uma unica modalidade;
- R4 (BAIXA): nenhum indicio moderado ou forte (indicios contextuais sao
              listados, mas nao elevam a prioridade).
"""

FORTE, MODERADO, CONTEXTUAL = "forte", "moderado", "contextual"
_ORDEM = {CONTEXTUAL: 0, MODERADO: 1, FORTE: 2}

REGRAS = {
    "R1": ("ALTA", "ha ao menos um indicio forte"),
    "R2": ("ALTA", "indicios em duas ou mais modalidades distintas, com ao menos um moderado ou forte"),
    "R3": ("MEDIA", "indicio moderado em uma unica modalidade"),
    "R4": ("BAIXA", "nenhum indicio moderado ou forte"),
}

RESSALVA = (
    "Prioridade de revisao pericial obtida por regras heuristicas, sem validacao empirica; "
    "nao e probabilidade nem conclusao sobre a pratica de crime. Cada estagio de IA e uma "
    "triagem sujeita a revisao humana."
)


def _executado(estagio: dict | None) -> bool:
    return bool(estagio) and estagio.get("executado", True) is not False


def extrair_indicios(evidencia: dict) -> list:
    """Indicios de UMA evidencia, a partir dos resultados de seus estagios.

    Args:
        evidencia: dict com 'modalidade' ('imagem', 'texto' ou 'logs') e
            'estagios' ({'E1': {...}, 'E2': {...}, ...}); um estagio nao
            executado traz 'executado': False e e ignorado.
    """
    modalidade = evidencia["modalidade"]
    estagios = evidencia.get("estagios", {})
    indicios = []

    def indicio(estagio, forca, descricao):
        indicios.append({"modalidade": modalidade, "estagio": estagio,
                         "forca": forca, "descricao": descricao})

    if modalidade == "imagem":
        e1, e2, e3 = estagios.get("E1"), estagios.get("E2"), estagios.get("E3")
        if _executado(e1) and e1.get("flag") == "MATCH":
            indicio("E1", FORTE, "correspondencia de hash perceptual com a base de referencia "
                                 f"(similaridade {e1.get('score_similaridade')})")
        if _executado(e2) and e2.get("flag") == "NSFW":
            if _executado(e3) and e3.get("flag") == "MENOR":
                indicio("E2+E3", FORTE, "conteudo explicito (E2) com pessoa estimada como menor (E3)")
            else:
                indicio("E2", MODERADO, "conteudo potencialmente explicito "
                                        f"(probabilidade {e2.get('probabilidade_nsfw')})")
    elif modalidade == "texto":
        e4 = estagios.get("E4")
        if _executado(e4) and e4.get("flag") == "SUSPEITO":
            indicio("E4", MODERADO, f"conversa com padrao de aliciamento (escore {e4.get('score_grooming')})")
    elif modalidade == "logs":
        e5 = estagios.get("E5")
        if _executado(e5) and e5.get("flag") == "ANOMALO":
            indicio("E5", CONTEXTUAL, "comportamento atipico de acesso a nuvem "
                                      f"({e5.get('n_anomalos')} de {e5.get('n_registros')} registros)")
    return indicios


def avaliar_caso(evidencias: list, pendencias: list | None = None) -> dict:
    """Avalia o caso: lista os indicios e aplica as regras R1 a R4.

    Args:
        evidencias: evidencias do caso (cada uma com 'modalidade' e 'estagios').
        pendencias: o que deveria ter entrado na avaliacao e nao entrou
            (coletas que falharam, como 'coleta:logs', e estagios que
            falharam, como 'E2'); se houver, a avaliacao e marcada como
            incompleta.

    Returns:
        {'prioridade', 'regra_aplicada', 'justificativa', 'indicios',
         'modalidades_com_indicio', 'avaliacao_incompleta', 'pendencias',
         'ressalva'}
    """
    indicios = [i for ev in evidencias for i in extrair_indicios(ev)]
    modalidades = sorted({i["modalidade"] for i in indicios})
    forca_max = max((_ORDEM[i["forca"]] for i in indicios), default=-1)

    if forca_max >= _ORDEM[FORTE]:
        regra = "R1"
    elif len(modalidades) >= 2 and forca_max >= _ORDEM[MODERADO]:
        regra = "R2"
    elif forca_max >= _ORDEM[MODERADO]:
        regra = "R3"
    else:
        regra = "R4"

    prioridade, justificativa = REGRAS[regra]
    pend = list(pendencias or [])
    return {
        "prioridade": prioridade,
        "regra_aplicada": regra,
        "justificativa": justificativa,
        "indicios": indicios,
        "modalidades_com_indicio": modalidades,
        "avaliacao_incompleta": bool(pend),
        "pendencias": pend,
        "ressalva": RESSALVA,
    }
