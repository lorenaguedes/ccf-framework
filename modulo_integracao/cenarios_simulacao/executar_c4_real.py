"""
Execucao real do Cenario C4 - Caso multimodal integrado.

Reune, em um unico caso sintetico, evidencias de tres modalidades e tres
provedores (emulados), aplica os estagios de IA reais, avalia o caso por
regras explicitas e registra a custodia na rede Hyperledger Fabric:

- imagem (AWS S3):    E1 PDQ (base de referencia SIMULADA) -> E2 OpenNSFW2
                      -> E3 MiVOLO (somente se o E2 sinalizar NSFW);
- conversa (Azure):   E4 (embeddings multilingues + regressao logistica);
- logs (GCP):         E5 (Isolation Forest, treinado em logs sinteticos).

Uso:
  poetry run python -m modulo_integracao.cenarios_simulacao.preparar_ambiente_c4
  poetry run python -m modulo_integracao.cenarios_simulacao.executar_c4_real
  poetry run python -m modulo_integracao.cenarios_simulacao.executar_c4_real --controle

--controle executa o caso de CONTROLE benigno (imagem sem correspondencia,
conversa normal, logs normais); o resultado esperado e prioridade BAIXA e
nenhum registro de custodia, o que mostra que as regras nao sinalizam tudo.

NOTA METODOLOGICA: dados sinteticos e base de referencia simulada; o
resultado demonstra a integracao dos componentes e a regra de avaliacao,
nao o desempenho do framework em casos reais.
"""
import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from modulo_coleta.hashing import calculate_hashes
from modulo_integracao.cenarios_simulacao import insumos_c4 as insumos
from modulo_integracao.cenarios_simulacao.cenario_c4 import executar_cenario_c4
from modulo_integracao.cenarios_simulacao.custodia_real import criar_custody_register_fn, id_evidencia
from modulo_integracao.cenarios_simulacao.preparar_ambiente_c1_c3 import BUCKET_GCS, BUCKET_S3, CONTAINER_AZURE
from modulo_integracao.cenarios_simulacao.preparar_ambiente_c4 import BLOB_LOGS, BLOB_TEXTO, KEY_IMAGEM

LOGS = Path(__file__).parent.parent / "logs"
CAMINHO_MODELO_E4 = "modulo_ia/models/modelo_e4_embeddings.json"
COLUNAS_E5 = ["volume_transferencia_mb", "frequencia_acesso_hora", "tamanho_medio_arquivo_mb"]


def _mesmo_conteudo(coleta: dict, conteudo: bytes) -> None:
    """O conteudo analisado deve ser o mesmo cujo hash foi coletado."""
    if calculate_hashes(conteudo)["sha256"] != coleta["hashes"]["sha256"]:
        raise RuntimeError("O conteudo mudou entre a coleta e a analise (hash divergente).")


def _coletor_imagem(controle: bool):
    from PIL import Image

    from modulo_coleta.aws_collector import collect_from_s3, get_s3_client

    def coletar():
        key = KEY_IMAGEM[controle]
        coleta = collect_from_s3(BUCKET_S3, key)
        conteudo = get_s3_client().get_object(Bucket=BUCKET_S3, Key=key)["Body"].read()
        _mesmo_conteudo(coleta, conteudo)
        return coleta, Image.open(io.BytesIO(conteudo)).convert("RGB")
    return coletar


def _coletor_texto(controle: bool):
    from modulo_coleta.azure_collector import collect_from_blob, get_blob_service_client

    def coletar():
        blob = BLOB_TEXTO[controle]
        coleta = collect_from_blob(CONTAINER_AZURE, blob)
        conteudo = get_blob_service_client().get_blob_client(
            container=CONTAINER_AZURE, blob=blob).download_blob().readall()
        _mesmo_conteudo(coleta, conteudo)
        return coleta, conteudo.decode("utf-8").splitlines()
    return coletar


def _coletor_logs(controle: bool):
    import pandas as pd

    from modulo_coleta.gcp_collector import collect_from_gcs, get_gcs_client

    def coletar():
        blob = BLOB_LOGS[controle]
        coleta = collect_from_gcs(BUCKET_GCS, blob)
        conteudo = get_gcs_client().bucket(BUCKET_GCS).blob(blob).download_as_bytes()
        _mesmo_conteudo(coleta, conteudo)
        return coleta, pd.read_csv(io.BytesIO(conteudo))
    return coletar


def _estagios():
    """Estagios reais (carregamento tardio dos modelos)."""
    from modulo_ia.deteccao_anomalias import detect_anomalies, fit_isolation_forest, generate_synthetic_logs
    from modulo_ia.deteccao_grooming import carregar_config, classificar_conversa, create_embedding_predict_fn
    from modulo_ia.estimativa_idade import classify_age, create_mivolo_predict_fn
    from modulo_ia.perceptual_hash import calculate_pdq_hash
    from modulo_ia.triagem import KnownHashDatabase, triage
    from modulo_ia.visao_computacional import classify_explicit_content, create_opennsfw2_predict_fn

    # E1: base de referencia SIMULADA (hash do padrao sintetico de semente 7)
    base = KnownHashDatabase()
    base.add("ref-sintetica-001", calculate_pdq_hash(insumos.imagem_padrao_sintetica(insumos.SEMENTE_PADRAO)))

    def triagem(imagem):
        return {**triage(imagem, base), "base_referencia_simulada": True}

    pred = {}

    def explicito(imagem):
        pred.setdefault("e2", create_opennsfw2_predict_fn())
        return classify_explicit_content(imagem, pred["e2"])

    def idade(imagem):  # so e chamado se o E2 sinalizar NSFW
        pred.setdefault("e3", create_mivolo_predict_fn())
        return classify_age(imagem, pred["e3"])

    limiar = carregar_config(CAMINHO_MODELO_E4)["limiar_f1max"]

    def grooming(linhas):
        pred.setdefault("e4", create_embedding_predict_fn(CAMINHO_MODELO_E4))
        return classificar_conversa(linhas, pred["e4"], threshold=limiar)

    treino = generate_synthetic_logs(1000, 100, random_state=42)
    modelo_e5 = fit_isolation_forest(treino[COLUNAS_E5], contamination=0.1, random_state=42)

    def anomalias(registros):
        r = detect_anomalies(registros, modelo_e5, COLUNAS_E5)
        n = int((r["flag"] == "ANOMALO").sum())
        return {"flag": "ANOMALO" if n else "NORMAL", "n_registros": int(len(r)),
                "n_anomalos": n, "menor_score": round(float(r["anomaly_score"].min()), 4)}

    return triagem, explicito, idade, grooming, anomalias, limiar


def _declaracoes(resultado: dict) -> list:
    d = [
        "Todas as evidencias sao sinteticas: imagem abstrata gerada por script, conversa inventada "
        "e registros de acesso gerados por simulacao; nao ha material real.",
        "A base de referencia do E1 e simulada (contem o hash perceptual de um padrao sintetico); "
        "a correspondencia demonstra o mecanismo, nao a deteccao de material ilicito real.",
        "O E5 foi treinado com logs sinteticos do mesmo processo gerador dos registros avaliados; "
        "o resultado nao mede o desempenho em logs reais.",
    ]
    imagem = next((e for e in resultado["evidencias"] if e["modalidade"] == "imagem"), None)
    if imagem and imagem["estagios"].get("E3", {}).get("executado") is False:
        d.append("O E3 (idade) so e aplicado a imagens sinalizadas pelo E2 e exige rosto recortado; "
                 "nao foi executado neste caso.")
    return d


def main(controle: bool = False):
    from modulo_blockchain.registrar_custodia import verificar_integridade
    from modulo_integracao.laudo_pericial import gerar_pdf_laudo_caso, montar_conteudo_laudo_caso

    triagem, explicito, idade, grooming, anomalias, limiar = _estagios()
    coletores = {"imagem": _coletor_imagem(controle), "texto": _coletor_texto(controle),
                 "logs": _coletor_logs(controle)}

    resultado = executar_cenario_c4(
        coletar_imagem=coletores["imagem"], coletar_texto=coletores["texto"],
        coletar_logs=coletores["logs"], triagem_fn=triagem, explicito_fn=explicito,
        idade_fn=idade, grooming_fn=grooming, anomalias_fn=anomalias,
        custody_register_fn=criar_custody_register_fn("c4"),
    )

    # Verificacao de integridade: recoleta cada evidencia registrada e confere com o ledger.
    for ev in resultado["evidencias"]:
        registro = ev["registro_custodia"]
        if not registro or registro.get("status") != "success":
            continue
        recoleta, _ = coletores[ev["modalidade"]]()
        eid = id_evidencia("c4", ev["coleta"], ev["coleta"]["hashes"]["sha256"])
        v = verificar_integridade(eid, recoleta["hashes"]["sha256"])
        registro["verificacao_integridade"] = {
            "hash_original": v["hash_original"], "hash_recalculado": v["hash_recalculado"],
            "integridade_valida": v["integridade_valida"]}

    sufixo = "controle" if controle else "execucao"
    log = {"cenario": "C4", "modo": "controle_benigno" if controle else "caso",
           "executado_em": datetime.now(timezone.utc).isoformat(), "resultado": resultado}
    caminho = LOGS / f"cenario_c4_{sufixo}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, default=str, ensure_ascii=False)
    print(json.dumps(log, indent=2, default=str, ensure_ascii=False))
    print(f"\nLog salvo em: {caminho}")

    if resultado["avaliacao_caso"] is None:
        print("Nenhuma evidencia foi analisada: laudo nao emitido.")
        return
    conteudo = montar_conteudo_laudo_caso(resultado, limiar_e4=limiar,
                                          declaracoes=_declaracoes(resultado))
    saida = LOGS / ("laudo_c4_controle.pdf" if controle else "laudo_c4.pdf")
    gerar_pdf_laudo_caso(conteudo, str(saida))
    print(f"Laudo salvo em: {saida}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o cenario C4 (caso multimodal) com componentes reais.")
    parser.add_argument("--controle", action="store_true", help="executa o caso de controle benigno")
    main(parser.parse_args().controle)
