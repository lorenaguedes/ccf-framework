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


def montar_conteudo_laudo_consolidado(
    evidencias: list,
    correlacao: dict,
    historicos: dict,
    cenario: str = "C3",
) -> dict:
    """Monta o laudo CONSOLIDADO de uma operacao multi-nuvem: uma unica
    peca que correlaciona as evidencias de todos os provedores (criterio
    de sucesso do Cenario C3, Tabela 16 do PGT).

    A correlacao e por provedor (quantos CSPs e quais), conforme
    produzida pelo orquestrador; nao ha correlacao por conteudo.

    Args:
        evidencias: evidencias coletadas (hashes, cloud_provider,
            collected_at, bucket/container, key/blob_name).
        correlacao: dict com total_csps_envolvidos e providers_presentes.
        historicos: {provedor: registro de custodia (com verificacao) ou
            None}, para cada evidencia.
        cenario: C1, C2 ou C3.

    Raises:
        ValueError: cenario invalido ou lista de evidencias vazia.
    """
    if cenario not in CENARIOS_VALIDOS:
        raise ValueError(f"Cenario invalido: '{cenario}'. Deve ser um de {CENARIOS_VALIDOS}.")
    if not evidencias:
        raise ValueError("O laudo consolidado exige ao menos uma evidencia.")

    itens = []
    for ev in evidencias:
        provedor = ev["cloud_provider"]
        historico = historicos.get(provedor)
        itens.append({
            "cloud_provider": provedor,
            "origem": ev.get("bucket") or ev.get("container"),
            "identificador": ev.get("key") or ev.get("blob_name"),
            "hash": ev["hashes"],
            "coletado_em": ev["collected_at"],
            "historico_blockchain": historico if historico is not None
            else "Evidencia nao registrada na cadeia de custodia neste laudo",
        })
    return {
        "cenario": cenario,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "correlacao": correlacao,
        "evidencias": itens,
        "classificacao_ia": "Nao aplicavel - classificacao por IA nao executada neste cenario",
    }


def gerar_pdf_laudo_consolidado(conteudo: dict, output_path: str) -> None:  # pragma: no cover
    """Renderiza o laudo consolidado (varias evidencias) em PDF.

    Excluida da cobertura automatizada, como gerar_pdf_laudo: a
    renderizacao e validada por inspecao do PDF gerado.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    doc = SimpleDocTemplate(output_path, pagesize=letter, topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=1.8*cm, rightMargin=1.8*cm)
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("TituloLaudoC", parent=styles["Title"], fontSize=16, spaceAfter=12)
    secao = ParagraphStyle("SecaoLaudoC", parent=styles["Heading2"], fontSize=12,
                           spaceBefore=16, spaceAfter=6)
    celula = ParagraphStyle("CelulaLaudoC", parent=styles["Normal"], fontSize=8, leading=10)
    hash_estilo = ParagraphStyle("HashLaudoC", parent=celula, fontName="Courier", fontSize=6.5, leading=8)

    story = [
        Paragraph("Laudo Pericial Consolidado - Framework CCF", titulo),
        Paragraph(f"Cenario de Investigacao: {conteudo['cenario']} | Gerado em: {conteudo['gerado_em']}",
                  styles["Normal"]),
        Spacer(1, 12),
        Paragraph("1. Correlacao de Evidencias entre Provedores", secao),
    ]
    corr = conteudo["correlacao"]
    story.append(Paragraph(
        f"<b>Provedores envolvidos:</b> {corr['total_csps_envolvidos']} "
        f"({', '.join(corr['providers_presentes'])}). A correlacao e feita por provedor de origem; "
        "nao ha correlacao por conteudo.", styles["Normal"]))

    story.append(Paragraph("2. Evidencias, Metadados e Hashes de Integridade", secao))
    linhas = [["Provedor", "Origem / identificador", "Coletado em", "SHA-256"]]
    for ev in conteudo["evidencias"]:
        linhas.append([
            Paragraph(ev["cloud_provider"], celula),
            Paragraph(f"{ev['origem']}<br/>{ev['identificador']}", celula),
            Paragraph(ev["coletado_em"], celula),
            Paragraph(ev["hash"]["sha256"], hash_estilo),
        ])
    tabela = Table(linhas, colWidths=[1.8*cm, 4.8*cm, 3.4*cm, 7.6*cm], repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tabela)

    story.append(Paragraph("3. Classificacao por Inteligencia Artificial", secao))
    story.append(Paragraph(conteudo["classificacao_ia"], styles["Normal"]))

    story.append(Paragraph("4. Historico de Cadeia de Custodia (Blockchain)", secao))
    for ev in conteudo["evidencias"]:
        h = ev["historico_blockchain"]
        if isinstance(h, dict):
            ver = h.get("verificacao_integridade") or {}
            texto = (f"<b>{ev['cloud_provider']}</b>: registrada no ledger "
                     f"(ID {h.get('evidence_id')}; status {h.get('status')}; acao {h.get('acao')}). "
                     f"Integridade na recoleta: {ver.get('integridade_valida', 'nao verificada')}.")
        else:
            texto = f"<b>{ev['cloud_provider']}</b>: {h}"
        story.append(Paragraph(texto, styles["Normal"]))
        story.append(Spacer(1, 4))

    doc.build(story)


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