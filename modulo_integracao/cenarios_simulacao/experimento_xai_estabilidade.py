"""
Experimento: estabilidade da explicacao LIME (indice de Jaccard) em funcao do
numero de perturbacoes, sobre imagens fornecidas (uso com imagens NEUTRAS ou
legais; nunca conteudo ilicito).

Uso:
  poetry run python -m modulo_integracao.cenarios_simulacao.experimento_xai_estabilidade \
      imagem1.jpg [imagem2.jpg ...] [--amostras 500 1000] [--pares 3]

Para cada imagem e cada valor de amostras, compara pares de execucoes com
sementes distintas e reporta media e desvio-padrao do Jaccard, alem do escore
real do modelo (explicar um escore ~0 e explicar ruido: o escore e informado
para que a leitura da estabilidade seja honesta). Saida em
modulo_integracao/logs/experimento_xai_estabilidade.json.
"""
import argparse
import io
import json
import statistics
from pathlib import Path

import numpy as np

from modulo_ia.xai import criar_predict_lote, generate_lime_explanation, jaccard_regioes, segmentador_slic

LOGS = Path(__file__).parent.parent / "logs"


def medir_estabilidade(imagem: np.ndarray, predict_lote, amostras: int, pares: int, base: int = 100,
                       n_segmentos: int | None = None) -> dict:
    """Jaccard entre explicacoes de pares de sementes (base+2i, base+2i+1)."""
    seg = segmentador_slic(n_segmentos) if n_segmentos else None
    valores = []
    for i in range(pares):
        a = generate_lime_explanation(imagem, predict_lote, num_samples=amostras,
                                      random_state=base + 2 * i, segmentation_fn=seg)
        b = generate_lime_explanation(imagem, predict_lote, num_samples=amostras,
                                      random_state=base + 2 * i + 1, segmentation_fn=seg)
        j = jaccard_regioes(a, b)
        if j is not None:
            valores.append(j)
    return {
        "num_samples": amostras, "n_segmentos": n_segmentos, "pares": pares, "pares_com_sinal": len(valores),
        "jaccard_medio": round(statistics.mean(valores), 4) if valores else None,
        "jaccard_desvio": round(statistics.pstdev(valores), 4) if len(valores) > 1 else None,
    }


# Configuracoes comparadas: (rotulo, n_segmentos, espaco). A primeira e a configuracao
# original (quickshift, probabilidade), mantida como referencia.
CONFIGURACOES = [
    ("quickshift/probabilidade", None, "probabilidade"),
    ("quickshift/logit", None, "logit"),
    ("slic16/probabilidade", 16, "probabilidade"),
    ("slic16/logit", 16, "logit"),
]


def main(caminhos, amostras, pares):  # pragma: no cover - depende do modelo real
    from PIL import Image

    from modulo_ia.visao_computacional import create_opennsfw2_batch_fn, create_opennsfw2_predict_fn
    predict_fn = create_opennsfw2_predict_fn()
    lote_fn = create_opennsfw2_batch_fn()
    saida = []
    for c in caminhos:
        img = Image.open(c).convert("RGB").resize((128, 128))
        escore = float(predict_fn(img))
        linhas = []
        for rotulo, nseg, espaco in CONFIGURACOES:
            pl = criar_predict_lote(predict_fn, espaco, lote_fn)
            for n in amostras:
                r = medir_estabilidade(np.array(img), pl, n, pares, n_segmentos=nseg)
                r.update({"configuracao": rotulo, "espaco": espaco})
                linhas.append(r)
                print(Path(c).name, round(escore, 4), rotulo, n, r["jaccard_medio"], flush=True)
        saida.append({"imagem": Path(c).name, "escore_modelo": round(escore, 4), "estabilidade": linhas})
    (LOGS / "experimento_xai_estabilidade.json").write_text(
        json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument("imagens", nargs="+")
    p.add_argument("--amostras", type=int, nargs="+", default=[500, 1000])
    p.add_argument("--pares", type=int, default=3)
    a = p.parse_args()
    main(a.imagens, a.amostras, a.pares)
