"""
Experimento E1 - hash perceptual (PDQ): precisao, revocacao e taxa de falsos
positivos sobre um corpus SINTETICO, com transformacoes de imagem.

Objetivo (Tabela 15 do PGT): P >= 0,95, R >= 0,99, FP < 1%.

Desenho (sem qualquer conteudo real ou ilicito):
  - Base de referencia: N_REF imagens sinteticas deterministicas (sementes fixas),
    de 3 familias (degrade com formas; blobs de baixa frequencia; textura).
  - Positivos: cada referencia submetida a transformacoes (recompressao JPEG,
    redimensionamento, recorte, brilho, desfoque, marca-d'agua). Um positivo e
    ACERTO se a menor distancia de Hamming a base for <= limiar E apontar para a
    referencia correta.
  - Negativos: N_NEG imagens sinteticas INDEPENDENTES (sementes distintas); sao
    falso positivo se algum hash da base estiver a <= limiar.
  - Transformacoes "no limite declarado" (espelhamento, rotacao de 90 graus,
    recorte de 30%) sao reportadas a parte: o PDQ nao e invariante a elas sem
    comparar variantes diedricas.
  - Hashes com qualidade PDQ < 50 sao reportados (Meta recomenda descartar).

Limitacao: corpus sintetico nao reproduz a distribuicao de imagens reais; os
valores sao de VIABILIDADE e de comportamento por transformacao, nao uma
estimativa de desempenho em producao.

Uso: poetry run python -m modulo_ia.experimentos.experimento_e1
Saida: modulo_ia/experimentos/resultados_e1.json
"""
import io
import json
import math
from pathlib import Path

import numpy as np
import pdqhash
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

N_REF = 200
N_NEG = 2000
LADO = 256
LIMIARES = (10, 16, 31)  # 10 = padrao do modulo; 31 = limiar de correspondencia sugerido pela Meta [CONFERIR]
LIMIAR_PRINCIPAL = 31
SEMENTE_REF = 1000
SEMENTE_NEG = 900_000
SAIDA = Path(__file__).parent / "resultados_e1.json"


# ---------------------------------------------------------------- corpus ----
def gerar_imagem(semente: int) -> Image.Image:
    """Imagem sintetica deterministica; a familia depende da semente."""
    rng = np.random.default_rng(semente)
    familia = semente % 3
    if familia == 0:  # degrade + formas
        base = np.zeros((LADO, LADO, 3), dtype=np.float64)
        for c in range(3):
            a, b = rng.uniform(20, 235, 2)
            eixo = rng.integers(0, 2)
            grad = np.linspace(a, b, LADO)
            base[..., c] = grad[None, :] if eixo else grad[:, None]
        img = Image.fromarray(base.clip(0, 255).astype("uint8"))
    elif familia == 1:  # blobs de baixa frequencia
        pequeno = rng.uniform(0, 255, (6, 6, 3))
        img = Image.fromarray(pequeno.astype("uint8")).resize((LADO, LADO), Image.BICUBIC)
    else:  # textura de media frequencia
        pequeno = rng.uniform(0, 255, (24, 24, 3))
        img = Image.fromarray(pequeno.astype("uint8")).resize((LADO, LADO), Image.BILINEAR)
    d = ImageDraw.Draw(img)
    for _ in range(int(rng.integers(3, 7))):
        x0, y0 = rng.integers(0, LADO - 40, 2)
        x1, y1 = x0 + rng.integers(20, 90), y0 + rng.integers(20, 90)
        cor = tuple(int(v) for v in rng.integers(0, 256, 3))
        (d.ellipse if rng.integers(0, 2) else d.rectangle)([x0, y0, x1, y1], fill=cor)
    return img


# --------------------------------------------------------- transformacoes ---
def _jpeg(q):
    def f(im):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q)
        return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    return f


def _escala(s):
    return lambda im: im.resize((max(8, int(im.width * s)), max(8, int(im.height * s))), Image.BILINEAR)


def _recorte(frac):
    def f(im):
        m = int(im.width * frac / 2)
        return im.crop((m, m, im.width - m, im.height - m))
    return f


def _marca(im):
    im = im.copy()
    ImageDraw.Draw(im).rectangle([im.width - 70, im.height - 24, im.width - 8, im.height - 8], fill=(255, 255, 255))
    return im


LEVES = {
    "jpeg_q90": _jpeg(90), "jpeg_q70": _jpeg(70), "jpeg_q50": _jpeg(50),
    "reduz_75": _escala(0.75), "reduz_50": _escala(0.5),
    "recorte_5": _recorte(0.05), "recorte_10": _recorte(0.10),
    "brilho_+15": lambda im: ImageEnhance.Brightness(im).enhance(1.15),
    "brilho_-15": lambda im: ImageEnhance.Brightness(im).enhance(0.85),
    "desfoque_r1": lambda im: im.filter(ImageFilter.GaussianBlur(1)),
    "marca_dagua": _marca,
}
LIMITE = {
    "jpeg_q30": _jpeg(30), "reduz_25": _escala(0.25), "recorte_30": _recorte(0.30),
    "espelho_horizontal": lambda im: im.transpose(Image.FLIP_LEFT_RIGHT),
    "rotacao_90": lambda im: im.transpose(Image.ROTATE_90),
}


# ---------------------------------------------------------------- metricas --
def calcular_pdq(img: Image.Image):
    h, q = pdqhash.compute(np.array(img.convert("RGB")))
    return h.astype(np.uint8), int(q)


def distancias(hashes: np.ndarray, base: np.ndarray) -> np.ndarray:
    """Matriz de distancias de Hamming (n x m) entre dois conjuntos de hashes de 256 bits."""
    a, b = np.packbits(hashes, axis=1), np.packbits(base, axis=1)
    tabela = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint16)
    out = np.empty((len(a), len(b)), dtype=np.uint16)
    for i in range(0, len(a), 256):
        out[i:i + 256] = tabela[a[i:i + 256, None, :] ^ b[None, :, :]].sum(axis=2)
    return out


def wilson(k: int, n: int, z: float = 1.96):
    """Intervalo de Wilson de 95% para uma proporcao."""
    if n == 0:
        return (None, None)
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, centro - meia), 4), round(min(1.0, centro + meia), 4))


def avaliar(d_pos: np.ndarray, esperado: np.ndarray, d_neg: np.ndarray, limiar: int) -> dict:
    if len(d_pos) == 0:
        return {"limiar": limiar, "positivos": 0}
    """Acertos (correspondencia correta) dos positivos e falsos positivos dos negativos."""
    mais_proximo = d_pos.argmin(axis=1)
    acerto = (d_pos.min(axis=1) <= limiar) & (mais_proximo == esperado)
    fp = d_neg.min(axis=1) <= limiar
    tp, n_pos, nfp, n_neg = int(acerto.sum()), len(acerto), int(fp.sum()), len(fp)
    revocacao, fpr = tp / n_pos, nfp / n_neg
    return {
        "limiar": limiar, "acertos": tp, "positivos": n_pos, "revocacao": round(revocacao, 4),
        "revocacao_ic95": wilson(tp, n_pos), "falsos_positivos": nfp, "negativos": n_neg,
        "taxa_falsos_positivos": round(fpr, 4), "fpr_ic95": wilson(nfp, n_neg),
        "precisao_corpus_1_para_1": round(tp / (tp + nfp), 4) if (tp + nfp) else None,
        "precisao_prevalencia_1pct": round(revocacao * 0.01 / (revocacao * 0.01 + fpr * 0.99), 4)
        if (revocacao * 0.01 + fpr * 0.99) else None,
    }


def executar(n_ref: int = N_REF, n_neg: int = N_NEG) -> dict:
    refs = [gerar_imagem(SEMENTE_REF + i) for i in range(n_ref)]
    h_ref = np.array([calcular_pdq(i)[0] for i in refs])
    q_ref = [calcular_pdq(i)[1] for i in refs]
    negs = [gerar_imagem(SEMENTE_NEG + i) for i in range(n_neg)]
    h_neg_q = [calcular_pdq(i) for i in negs]
    h_neg = np.array([h for h, _ in h_neg_q])
    d_neg = distancias(h_neg, h_ref)

    def bloco(transformacoes: dict) -> dict:
        hs, esp, por_t = [], [], {}
        for nome, f in transformacoes.items():
            hh = np.array([calcular_pdq(f(im))[0] for im in refs])
            d = distancias(hh, h_ref)
            por_t[nome] = {str(t): round(float(((d.min(axis=1) <= t) & (d.argmin(axis=1) == np.arange(n_ref))).mean()), 4)
                           for t in LIMIARES}
            hs.append(hh)
            esp.append(np.arange(n_ref))
        d_all = distancias(np.vstack(hs), h_ref)
        esperado = np.concatenate(esp)
        # Subconjunto de qualidade PDQ >= 50 (recomendacao da Meta): a base descarta hashes de
        # baixa qualidade, os positivos de referencias de baixa qualidade saem e os negativos tambem.
        ok_ref = np.array([q >= 50 for q in q_ref])
        ok_neg = np.array([q >= 50 for _, q in h_neg_q])
        d_q = d_all.copy()
        d_q[:, ~ok_ref] = 999
        pos_ok = ok_ref[esperado]
        dn_q = d_neg.copy()
        dn_q[:, ~ok_ref] = 999
        return {"por_transformacao_revocacao": por_t,
                "global": {str(t): avaliar(d_all, esperado, d_neg, t) for t in LIMIARES},
                "global_qualidade_ge_50": {str(t): avaliar(d_q[pos_ok], esperado[pos_ok], dn_q[ok_neg], t)
                                           for t in LIMIARES}}

    leves, limite = bloco(LEVES), bloco(LIMITE)
    d_ref_ref = distancias(h_ref, h_ref).astype(float)
    np.fill_diagonal(d_ref_ref, np.nan)
    return {
        "configuracao": {"n_referencias": n_ref, "n_negativos": n_neg, "lado_px": LADO, "limiares": list(LIMIARES),
                         "limiar_principal": LIMIAR_PRINCIPAL, "sementes": [SEMENTE_REF, SEMENTE_NEG],
                         "transformacoes_leves": list(LEVES), "transformacoes_limite": list(LIMITE),
                         "pdqhash": getattr(pdqhash, "__version__", "n/d")},
        "qualidade_pdq": {"referencias_abaixo_de_50": int(sum(q < 50 for q in q_ref)),
                          "negativos_abaixo_de_50": int(sum(q < 50 for _, q in h_neg_q))},
        "distancia_negativo_mais_proximo": {"minima": int(d_neg.min()), "media": round(float(d_neg.min(axis=1).mean()), 2)},
        "distancia_entre_referencias": {"minima": int(np.nanmin(d_ref_ref)), "media": round(float(np.nanmean(d_ref_ref)), 2)},
        "transformacoes_leves": leves,
        "transformacoes_no_limite_declarado": limite,
        "alvos_tabela_15": {"precisao": 0.95, "revocacao": 0.99, "fp_max": 0.01},
    }


if __name__ == "__main__":
    r = executar()
    SAIDA.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    for t in LIMIARES:
        g = r["transformacoes_leves"]["global"][str(t)]
        print(f"limiar {t}: R={g['revocacao']} FPR={g['taxa_falsos_positivos']} P(1:1)={g['precisao_corpus_1_para_1']}")
    print("Salvo em", SAIDA)
