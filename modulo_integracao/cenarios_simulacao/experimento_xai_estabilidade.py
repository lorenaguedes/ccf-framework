"""
Experimento: estabilidade da explicacao LIME (indice de Jaccard) em funcao do
numero de perturbacoes, sobre imagens fornecidas (uso com imagens NEUTRAS ou
legais; nunca conteudo ilicito).

Uso:
  poetry run python -m modulo_integracao.cenarios_simulacao.experimento_xai_estabilidade \
      imagem1.jpg [imagem2.jpg ...] [--amostras 200 500 1000] [--pares 5]

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

from modulo_ia.xai import criar_predict_lote, generate_lime_explanation, jaccard_regioes

LOGS = Path(__file__).parent.parent / "logs"


def medir_estabilidade(imagem: np.ndarray, predict_lote, amostras: int, pares: int, base: int = 100) -> dict:
    """Jaccard entre explicacoes de pares de sementes (base+2i, base+2i+1)."""
    valores = []
    for i in range(pares):
        a = generate_lime_explanation(imagem, predict_lote, num_samples=amostras, random_state=base + 2 * i)
        b = generate_lime_explanation(imagem, predict_lote, num_samples=amostras, random_state=base + 2 * i + 1)
        j = jaccard_regioes(a, b)
        if j is not None:
            valores.append(j)
    return {
        "num_samples": amostras, "pares": pares, "pares_com_sinal": len(valores),
        "jaccard_medio": round(statistics.mean(valores), 4) if valores else None,
        "jaccard_desvio": round(statistics.pstdev(valores), 4) if len(valores) > 1 else None,
    }


def main(caminhos, amostras, pares):  # pragma: no cover - depende do modelo real
    from PIL import Image

    from modulo_ia.visao_computacional import create_opennsfw2_predict_fn
    predict_fn = create_opennsfw2_predict_fn()
    predict_lote = criar_predict_lote(predict_fn)
    saida = []
    for c in caminhos:
        img = Image.open(c).convert("RGB").resize((128, 128))
        escore = float(predict_fn(img))
        linhas = [medir_estabilidade(np.array(img), predict_lote, n, pares) for n in amostras]
        saida.append({"imagem": Path(c).name, "escore_modelo": round(escore, 4), "estabilidade": linhas})
        print(Path(c).name, round(escore, 4), [(l["num_samples"], l["jaccard_medio"]) for l in linhas])
    (LOGS / "experimento_xai_estabilidade.json").write_text(
        json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument("imagens", nargs="+")
    p.add_argument("--amostras", type=int, nargs="+", default=[200, 500, 1000])
    p.add_argument("--pares", type=int, default=5)
    a = p.parse_args()
    main(a.imagens, a.amostras, a.pares)
