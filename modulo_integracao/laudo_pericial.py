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
            relevantes), ou None se nao aplicavel (ex: conteudo
            benigno, sem necessidade de explicacao).
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

    if xai_info is None:
        artefatos_xai = "Nao aplicavel - conteudo classificado como SFW"
    else:
        artefatos_xai = xai_info

    if historico_blockchain is None:
        historico_blockchain_final = "Evidencia nao registrada na cadeia de custodia (conteudo benigno)"
    else:
        historico_blockchain_final = historico_blockchain

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