"""
Experimento: estabilidade da explicacao LIME (indice de Jaccard) em funcao do
numero de perturbacoes, sobre imagens fornecidas (uso com imagens NEUTRAS ou
legais; nunca conteudo ilicito).

Uso:
  poetry run python -m modulo_integracao.cenarios_simulacao.experimento_xai_estabilidade \
      [imagem1.jpg ...] [--sinteticas] [--amostras 500 1000] [--pares 3]

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


def imagens_sinteticas() -> list:
    """Imagens sinteticas LEGAIS e sem pessoas, de complexidade crescente.

    - solida_c1: a imagem do C1 (cor solida). Caso degenerado para o LIME: nao ha
      estrutura visual para os segmentos distinguirem.
    - formas: fundo em degrade com retangulos e circulos de cores distintas.
    - degrade_quente_ruido: degrade de tons quentes com ruido gaussiano.
    """
    from PIL import Image, ImageDraw

    solida = Image.new("RGB", (224, 224), (100, 150, 200))
    formas = Image.new("RGB", (224, 224))
    px = np.zeros((224, 224, 3), dtype="uint8")
    px[..., 0] = np.linspace(40, 200, 224)[None, :]
    px[..., 2] = np.linspace(200, 60, 224)[:, None]
    px[..., 1] = 90
    formas = Image.fromarray(px)
    d = ImageDraw.Draw(formas)
    d.rectangle([20, 20, 100, 90], fill=(220, 40, 40))
    d.ellipse([120, 110, 200, 190], fill=(240, 220, 60))
    d.rectangle([30, 140, 90, 200], fill=(30, 160, 80))
    rng = np.random.default_rng(7)
    q = np.zeros((224, 224, 3), dtype=float)
    q[..., 0] = np.linspace(180, 240, 224)[None, :]
    q[..., 1] = np.linspace(120, 170, 224)[:, None]
    q[..., 2] = 110
    quente = Image.fromarray((q + rng.normal(0, 12, q.shape)).clip(0, 255).astype("uint8"))
    return [("solida_c1", solida), ("formas", formas), ("degrade_quente_ruido", quente)]


def main(caminhos, amostras, pares, sinteticas=False):  # pragma: no cover - depende do modelo real
    from PIL import Image

    from modulo_ia.visao_computacional import create_opennsfw2_batch_fn, create_opennsfw2_predict_fn
    predict_fn = create_opennsfw2_predict_fn()
    lote_fn = create_opennsfw2_batch_fn()
    saida = []
    fontes = [(Path(c).name, Image.open(c)) for c in caminhos]
    if sinteticas:
        fontes += imagens_sinteticas()
    for nome, bruta in fontes:
        img = bruta.convert("RGB").resize((128, 128))
        escore = float(predict_fn(img))
        linhas = []
        for rotulo, nseg, espaco in CONFIGURACOES:
            pl = criar_predict_lote(predict_fn, espaco, lote_fn)
            for n in amostras:
                r = medir_estabilidade(np.array(img), pl, n, pares, n_segmentos=nseg)
                r.update({"configuracao": rotulo, "espaco": espaco})
                linhas.append(r)
                print(nome, round(escore, 4), rotulo, n, r["jaccard_medio"], flush=True)
        saida.append({"imagem": nome, "escore_modelo": round(escore, 4), "estabilidade": linhas})
    (LOGS / "experimento_xai_estabilidade.json").write_text(
        json.dumps(saida, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument("imagens", nargs="*", help="caminhos de imagens neutras/legais (opcional)")
    p.add_argument("--sinteticas", action="store_true", help="inclui 3 imagens sinteticas legais")
    p.add_argument("--amostras", type=int, nargs="+", default=[500, 1000])
    p.add_argument("--pares", type=int, default=3)
    a = p.parse_args()
    if not a.imagens and not a.sinteticas:
        p.error("informe imagens ou --sinteticas")
    main(a.imagens, a.amostras, a.pares, a.sinteticas)
