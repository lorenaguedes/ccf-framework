"""
Orquestrador do Cenario C4 - Caso multimodal integrado.

CENARIO ADICIONAL: nao consta da Tabela 16 do PGT (C1 a C3); foi incluido
para exercitar, em um unico caso, os estagios de IA sobre modalidades
diferentes e a avaliacao conjunta do caso (desvio registrado na secao
de desvios do PGT).

Caso: uma imagem (armazenamento de objetos), uma conversa (mensagens) e
registros de acesso (logs de nuvem), possivelmente em provedores distintos.

Pipeline:
- imagem: coleta -> E1 (hash perceptual) -> E2 (conteudo explicito) ->
  E3 (idade), este SOMENTE se o E2 sinalizar NSFW (Tabela 12: o E3 e
  aplicado apos a deteccao de conteudo explicito);
- texto:  coleta -> E4 (aliciamento);
- logs:   coleta -> E5 (anomalias);
- avaliacao do caso por regras explicitas (modulo avaliacao_caso);
- registro de custodia das evidencias que apresentam algum indicio.

Resiliencia: a falha de uma coleta, de um estagio ou do registro de
custodia e registrada e nao aborta o caso; a avaliacao e marcada como
incompleta e lista as pendencias. Se nenhuma evidencia for coletada, nao
ha avaliacao (nao se afirma prioridade BAIXA para um caso nao analisado).

Mesma estrategia de injecao de dependencia dos demais cenarios.
"""
from typing import Any, Callable

from modulo_integracao.avaliacao_caso import avaliar_caso, extrair_indicios


def _rodar_estagio(nome: str, fn: Callable, entrada: Any, erros: dict) -> dict:
    """Executa um estagio; uma falha vira 'executado: False' com o motivo."""
    try:
        return {"executado": True, **fn(entrada)}
    except Exception as e:
        erros[nome] = str(e)
        return {"executado": False, "motivo": f"falha: {e}"}


def executar_cenario_c4(
    coletar_imagem: Callable[[], tuple],
    coletar_texto: Callable[[], tuple],
    coletar_logs: Callable[[], tuple],
    triagem_fn: Callable[[Any], dict],
    explicito_fn: Callable[[Any], dict],
    idade_fn: Callable[[Any], dict],
    grooming_fn: Callable[[Any], dict],
    anomalias_fn: Callable[[Any], dict],
    custody_register_fn: Callable[[str, str, dict], dict],
) -> dict:
    """Executa o caso multimodal.

    Args:
        coletar_imagem/coletar_texto/coletar_logs: funcoes sem argumentos que
            coletam a evidencia e devolvem (coleta, conteudo), em que
            'coleta' e o dict de evidencia (hashes, cloud_provider,
            collected_at, ...) e 'conteudo' e o objeto a analisar (imagem,
            lista de mensagens, registros).
        triagem_fn, explicito_fn, idade_fn: estagios E1, E2 e E3 (imagem).
        grooming_fn: estagio E4 (recebe as mensagens).
        anomalias_fn: estagio E5 (recebe os registros).
        custody_register_fn: registro de custodia (evidence_id, hash, metadados).

    Returns:
        {'evidencias', 'avaliacao_caso', 'erros_coleta', 'erros_estagio',
         'erros_custodia', 'status_pipeline'}; status 'SUCESSO',
        'SUCESSO_PARCIAL' (algo falhou, mas ha evidencia analisada) ou 'FALHA'.
    """
    fontes = {"imagem": coletar_imagem, "texto": coletar_texto, "logs": coletar_logs}
    evidencias, erros_coleta, erros_estagio = [], {}, {}

    for modalidade, coletar in fontes.items():
        try:
            coleta, conteudo = coletar()
        except Exception as e:
            erros_coleta[modalidade] = str(e)
            continue

        estagios: dict = {}
        if modalidade == "imagem":
            estagios["E1"] = _rodar_estagio("E1", triagem_fn, conteudo, erros_estagio)
            estagios["E2"] = _rodar_estagio("E2", explicito_fn, conteudo, erros_estagio)
            if estagios["E2"].get("flag") == "NSFW":
                estagios["E3"] = _rodar_estagio("E3", idade_fn, conteudo, erros_estagio)
            else:
                estagios["E3"] = {"executado": False,
                                  "motivo": "E3 so e aplicado a imagens sinalizadas pelo E2 (Tabela 12)"}
        elif modalidade == "texto":
            estagios["E4"] = _rodar_estagio("E4", grooming_fn, conteudo, erros_estagio)
        else:
            estagios["E5"] = _rodar_estagio("E5", anomalias_fn, conteudo, erros_estagio)

        evidencia = {"modalidade": modalidade, "coleta": coleta, "estagios": estagios,
                     "registro_custodia": None}
        evidencia["indicios"] = extrair_indicios(evidencia)
        evidencias.append(evidencia)

    avaliacao = None
    if evidencias:
        pendencias = [f"coleta:{m}" for m in erros_coleta] + sorted(erros_estagio)
        avaliacao = avaliar_caso(evidencias, pendencias)

    # Custodia: evidencias com algum indicio (inclusive contextual).
    erros_custodia = {}
    for ev in evidencias:
        if not ev["indicios"]:
            continue
        provedor = ev["coleta"]["cloud_provider"]
        try:
            ev["registro_custodia"] = custody_register_fn(
                f"evid-c4-{provedor}",
                ev["coleta"]["hashes"]["sha256"],
                {**ev["coleta"], "modalidade": ev["modalidade"]},
            )
        except Exception as e:
            erros_custodia[ev["modalidade"]] = str(e)

    if not evidencias:
        status = "FALHA"
    elif erros_coleta or erros_estagio or erros_custodia:
        status = "SUCESSO_PARCIAL"
    else:
        status = "SUCESSO"

    return {
        "evidencias": evidencias,
        "avaliacao_caso": avaliacao,
        "erros_coleta": erros_coleta,
        "erros_estagio": erros_estagio,
        "erros_custodia": erros_custodia,
        "status_pipeline": status,
    }
