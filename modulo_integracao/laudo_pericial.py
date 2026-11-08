"""
Modulo de geracao de laudo pericial - RF12 (Tabela 10, PGT).

"Gerar laudos periciais automaticos em PDF, contendo: hashes,
metadados, classificacoes IA com artefatos XAI e historico blockchain."

Referencia normativa: ECA art. 241-B; LGPD art. 6º.

Estrategia de design: separa a MONTAGEM do conteudo (funcao pura,
testavel) da RENDERIZACAO do PDF (via reportlab, validada manualmente -
ver gerar_pdf_laudo).
"""
from datetime import datetime, timezone

CENARIOS_VALIDOS = {"C1", "C2", "C3"}
FLAGS_BENIGNOS = {"SFW", "NORMAL"}


def montar_conteudo_laudo(
    evidencia: dict,
    classificacao: dict,
    xai_info: dict | None,
    historico_blockchain: dict | None,
    cenario: str,
) -> dict:
    """Monta a estrutura de conteudo de um laudo pericial, a partir
    dos resultados de um pipeline de investigacao (coleta, IA, XAI,
    blockchain).

    Args:
        evidencia: resultado da coleta (bucket/container, key, hashes,
            cloud_provider, collected_at).
        classificacao: resultado da classificacao de IA (flag,
            probabilidade/score).
        xai_info: informacoes de explicabilidade (metodo, regioes
            relevantes), ou None. Sem artefato, o laudo distingue tres
            estados: conteudo classificado como benigno (SFW/NORMAL),
            classificacao nao executada (sem flag) e conteudo sinalizado
            sem artefato de explicacao.
        historico_blockchain: resultado do registro na cadeia de
            custodia (tx_id, status), ou None se nao registrado.
        cenario: identificador do cenario de simulacao (C1, C2 ou C3,
            conforme Tabela 16 do PGT).

    Returns:
        Dicionario estruturado com todas as secoes exigidas pelo RF12.

    Raises:
        ValueError: se o cenario informado nao for C1, C2 ou C3.
    """
    if cenario not in CENARIOS_VALIDOS:
        raise ValueError(
            f"Cenario invalido: '{cenario}'. Deve ser um de {CENARIOS_VALIDOS} "
            "(Tabela 16, PGT)."
        )

    flag = (classificacao or {}).get("flag")
    benigno = flag in FLAGS_BENIGNOS

    if xai_info is not None:
        artefatos_xai = xai_info
    elif benigno:
        artefatos_xai = f"Nao aplicavel - conteudo classificado como {flag}"
    elif flag is None:
        # Nao afirma classificacao que nao ocorreu (ex.: cenario C3,
        # que valida coleta e custodia, sem etapa de IA).
        artefatos_xai = "Nao aplicavel - classificacao por IA nao executada neste cenario"
    else:
        artefatos_xai = (
            f"Artefato de explicabilidade nao gerado para conteudo classificado como {flag}"
        )

    if historico_blockchain is not None:
        historico_blockchain_final = historico_blockchain
    elif benigno:
        historico_blockchain_final = "Evidencia nao registrada na cadeia de custodia (conteudo benigno)"
    else:
        historico_blockchain_final = "Evidencia nao registrada na cadeia de custodia neste laudo"

    return {
        "cenario": cenario,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "hash": evidencia["hashes"],
        "metadados": {
            "origem": evidencia.get("bucket") or evidencia.get("container") or evidencia.get("container_id"),
            "identificador": evidencia.get("key") or evidencia.get("blob_name") or evidencia.get("log_path"),
            "cloud_provider": evidencia["cloud_provider"],
            "coletado_em": evidencia["collected_at"],
        },
        "classificacao_ia": classificacao,
        "artefatos_xai": artefatos_xai,
        "historico_blockchain": historico_blockchain_final,
    }


def montar_xai_texto(classificacao: dict, limiar: float | None = None) -> dict | None:
    """Monta o artefato de explicabilidade para uma classificacao textual
    do estagio E4 (secao 4.4.6 do PGT).

    O artefato reune o metodo (oclusao por mensagem), o escore, o limiar
    usado e os trechos relevantes, isto e, as mensagens da janela cuja
    remocao mais reduz o escore. Descreve o comportamento do modelo e
    nao constitui justificativa causal: sujeito a revisao pericial.

    Args:
        classificacao: resultado de classify_grooming/classificar_conversa
            (score_grooming, flag, trechos_relevantes).
        limiar: limiar de decisao aplicado, para constar no laudo.

    Returns:
        Dicionario com o artefato, ou None se a conversa nao foi
        sinalizada (nao ha o que explicar).
    """
    if classificacao.get("flag") != "SUSPEITO":
        return None
    return {
        "metodo": "Oclusao por mensagem (E4)",
        "escore": classificacao["score_grooming"],
        "limiar": limiar,
        "trechos_relevantes": list(classificacao.get("trechos_relevantes", [])),
        "ressalva": "Explicacao do comportamento do modelo, nao causal; "
                    "sujeita a revisao pericial humana.",
    }


def gerar_pdf_laudo(conteudo: dict, output_path: str) -> None:  # pragma: no cover
    """Renderiza o conteudo estruturado do laudo em um arquivo PDF,
    seguindo o formato exigido pelo RF12.

    Nota: excluida da cobertura de testes unitarios propositalmente -
    a renderizacao visual e validada manualmente (inspecao do PDF
    gerado), nao por assercoes automatizadas sobre o layout.

    Args:
        conteudo: dicionario retornado por montar_conteudo_laudo.
        output_path: caminho onde o PDF sera salvo.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    titulo_style = ParagraphStyle(
        "TituloLaudo", parent=styles["Title"], fontSize=16, spaceAfter=12
    )
    secao_style = ParagraphStyle(
        "SecaoLaudo", parent=styles["Heading2"], fontSize=12, spaceBefore=16, spaceAfter=6
    )

    story.append(Paragraph("Laudo Pericial - Framework CCF", titulo_style))
    story.append(Paragraph(
        f"Cenario de Investigacao: {conteudo['cenario']} | Gerado em: {conteudo['gerado_em']}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1. Hash de Integridade da Evidencia", secao_style))
    tabela_hash = Table([
        ["Algoritmo", "Valor"],
        ["SHA-256", conteudo["hash"]["sha256"]],
        ["MD5", conteudo["hash"].get("md5", "N/A")],
    ], colWidths=[4*cm, 12*cm])
    tabela_hash.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(tabela_hash)

    story.append(Paragraph("2. Metadados da Coleta", secao_style))
    meta = conteudo["metadados"]
    story.append(Paragraph(f"<b>Origem:</b> {meta['origem']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Identificador:</b> {meta['identificador']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Provedor de Nuvem:</b> {meta['cloud_provider']}", styles["Normal"]))
    story.append(Paragraph(f"<b>Coletado em:</b> {meta['coletado_em']}", styles["Normal"]))

    story.append(Paragraph("3. Classificacao por Inteligencia Artificial", secao_style))
    story.append(Paragraph(str(conteudo["classificacao_ia"]), styles["Normal"]))

    story.append(Paragraph("4. Artefatos de Explicabilidade (XAI)", secao_style))
    story.append(Paragraph(str(conteudo["artefatos_xai"]), styles["Normal"]))

    story.append(Paragraph("5. Historico de Cadeia de Custodia (Blockchain)", secao_style))
    story.append(Paragraph(str(conteudo["historico_blockchain"]), styles["Normal"]))

    doc.build(story)