"""
Execucao real do Cenario C1 - Distribuicao de CSAM em Storage S3.

Conecta os componentes reais (nao sinteticos):
- modulo_coleta.aws_collector (LocalStack)
- modulo_ia.visao_computacional (OpenNSFW2)
- Chaincode 'custody' na rede Hyperledger Fabric real (registro e
  conferencia do hash via modulo_blockchain.registrar_custodia)

Uso:
  poetry run python -m modulo_integracao.cenarios_simulacao.executar_c1_real
      Execucao com a classificacao real. A imagem do cenario e sintetica
      e neutra, entao o resultado esperado e SFW, sem registro de
      custodia e sem artefato de explicabilidade.

  poetry run python -m modulo_integracao.cenarios_simulacao.executar_c1_real --validar-ramo-nsfw
      Valida o ramo de conteudo sinalizado (registro de custodia) com um
      classificador FORCADO a NSFW, porque reproduzir conteudo explicito
      real seria eticamente inadequado. O log e o laudo dessa execucao
      declaram explicitamente o forcamento (classificador_forcado: true),
      e o resultado nao e uma classificacao do modelo.

Gera log em modulo_integracao/logs/ e o laudo pericial correspondente.
"""
import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from modulo_blockchain.registrar_custodia import verificar_integridade
from modulo_coleta.aws_collector import collect_from_s3, get_s3_client
from modulo_ia.visao_computacional import (
    classify_explicit_content,
    create_opennsfw2_batch_fn,
    create_opennsfw2_predict_fn,
)
from modulo_integracao.cenarios_simulacao.cenario_c1 import executar_cenario_c1
from modulo_integracao.cenarios_simulacao.custodia_real import criar_custody_register_fn, id_evidencia
from modulo_integracao.explicabilidade_imagem import gerar_explicabilidade_imagem

BUCKET = "ccf-evidence-bucket"
KEY = "evidencia-c1-real.jpg"
LOGS = Path(__file__).parent.parent / "logs"


def _classifier_fn_real(conteudo: bytes) -> dict:
    """Adapta o classify_explicit_content (que espera PIL.Image) para
    a assinatura esperada pelo orquestrador (que passa bytes brutos)."""
    from PIL import Image

    imagem = Image.open(io.BytesIO(conteudo))
    predict_fn = create_opennsfw2_predict_fn()
    return classify_explicit_content(imagem, predict_fn)


def _classifier_fn_forcado_nsfw(conteudo: bytes) -> dict:
    """Classifica de verdade e entao FORCA o rotulo NSFW, marcando o
    resultado como forcado (validacao do ramo de custodia)."""
    resultado = _classifier_fn_real(conteudo)
    resultado["flag_original"] = resultado["flag"]
    resultado["flag"] = "NSFW"
    resultado["classificador_forcado"] = True
    return resultado


def main(validar_ramo_nsfw: bool = False, xai_amostras: int = 200,
         xai_segmentos: int | None = None, xai_espaco: str = "probabilidade"):
    client = get_s3_client()
    conteudo = client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read()

    resultado = executar_cenario_c1(
        bucket=BUCKET,
        key=KEY,
        conteudo=conteudo,
        collector_fn=collect_from_s3,
        classifier_fn=_classifier_fn_forcado_nsfw if validar_ramo_nsfw else _classifier_fn_real,
        custody_register_fn=criar_custody_register_fn("c1"),
    )

    registro = resultado.get("registro_custodia")
    if registro and registro.get("status") == "success":
        # Recoleta a evidencia e confere o hash recalculado com o do ledger.
        recoleta = collect_from_s3(BUCKET, KEY)
        eid = id_evidencia("c1", resultado["coleta"], resultado["coleta"]["hashes"]["sha256"])
        resultado["verificacao_integridade"] = verificar_integridade(
            eid, recoleta["hashes"]["sha256"]
        )

    classificacao = resultado.get("classificacao") or {}
    if classificacao.get("flag") == "NSFW":
        # Explica a probabilidade REAL do modelo (mesmo no ramo forcado).
        nome_mapa = "mapa_xai_c1_forcado.png" if validar_ramo_nsfw else "mapa_xai_c1.png"
        resultado["explicabilidade"] = gerar_explicabilidade_imagem(
            conteudo, create_opennsfw2_predict_fn(), LOGS, nome_mapa,
            num_samples=xai_amostras, n_segmentos=xai_segmentos, espaco=xai_espaco,
            predict_lote_fn=create_opennsfw2_batch_fn())

    log_entry = {
        "cenario": "C1",
        "modo": "ramo_nsfw_forcado" if validar_ramo_nsfw else "classificacao_real",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "resultado": resultado,
    }
    nome = "cenario_c1_ramo_nsfw_forcado.json" if validar_ramo_nsfw else "cenario_c1_execucao.json"
    log_path = LOGS / nome
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, indent=2, default=str, ensure_ascii=False)

    print(json.dumps(log_entry, indent=2, default=str, ensure_ascii=False))
    print(f"\nLog salvo em: {log_path}")

    from modulo_integracao.cenarios_simulacao.gerar_laudos_c1_c3 import gerar_laudo_c1
    saida = LOGS / ("laudo_c1_ramo_nsfw_forcado.pdf" if validar_ramo_nsfw else "laudo_c1.pdf")
    gerar_laudo_c1(log_path, saida)
    print(f"Laudo salvo em: {saida}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o cenario C1 com componentes reais.")
    parser.add_argument("--validar-ramo-nsfw", action="store_true",
                        help="forca o rotulo NSFW para validar o registro de custodia (declarado no laudo)")
    parser.add_argument("--xai-amostras", type=int, default=200,
                        help="perturbacoes do LIME (mais amostras tendem a estabilizar a explicacao)")
    parser.add_argument("--xai-segmentos", type=int, default=None,
                        help="usa SLIC com ~N segmentos (padrao: quickshift do LIME)")
    parser.add_argument("--xai-espaco", choices=("probabilidade", "logit"), default="probabilidade",
                        help="espaco da saida explicada pelo LIME")
    a = parser.parse_args()
    main(a.validar_ramo_nsfw, a.xai_amostras, a.xai_segmentos, a.xai_espaco)
