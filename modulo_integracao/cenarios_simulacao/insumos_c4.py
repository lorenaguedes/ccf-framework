"""
Insumos SINTETICOS do Cenario C4 (caso multimodal): nenhuma imagem de
pessoa, nenhuma conversa real, nenhum log real.

- imagem: padrao abstrato (senoides e blocos) gerado de forma
  deterministica; nao e plana, de modo que o hash perceptual (PDQ) e
  significativo (uma imagem de cor solida tem hash degenerado);
- conversa: mensagens curtas inventadas (suspeita e de controle);
- logs: registros de acesso gerados por generate_synthetic_logs.

Tudo e funcao da semente, o que permite reproduzir a execucao.
O hash do JPEG depende da versao do Pillow/libjpeg; o que se compara
entre execucoes e o comportamento, nao o hash byte a byte.
"""
import io

import numpy as np
from PIL import Image

SEMENTE_PADRAO = 7
SEMENTE_PADRAO_CONTROLE = 99  # imagem diferente, para o caso de controle
SEMENTE_LOGS = 7

CONVERSA_SUSPEITA = (
    "hey, i really like talking to you\n"
    "you are so mature for your age\n"
    "this is our secret, dont tell your parents ok?\n"
    "delete our chat after we talk\n"
    "i can send you a gift if you keep it between us\n"
)
CONVERSA_NORMAL = (
    "hi, how was school today\n"
    "it was fine, we had a math test\n"
    "cool, good luck with the results\n"
    "thanks, my friends and i are going to the park later\n"
    "have fun, see you tomorrow\n"
)


def imagem_padrao_sintetica(semente: int = SEMENTE_PADRAO, lado: int = 224) -> Image.Image:
    """Padrao abstrato RGB deterministico (senoides com blocos de cor)."""
    rng = np.random.default_rng(semente)
    y, x = np.mgrid[0:lado, 0:lado].astype(float)
    canais = []
    for _ in range(3):
        fx, fy = rng.uniform(0.02, 0.12, size=2)
        fase = rng.uniform(0, 2 * np.pi)
        canais.append(127 + 100 * np.sin(fx * x + fy * y + fase))
    img = np.stack(canais, axis=-1)
    for _ in range(6):  # blocos de cor para dar estrutura
        x0, y0 = rng.integers(0, lado - 40, size=2)
        w, h = rng.integers(20, 60, size=2)
        img[y0:y0 + h, x0:x0 + w] = rng.integers(0, 256, size=3)
    return Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")


def jpeg_bytes(imagem: Image.Image, qualidade: int = 90) -> bytes:
    buf = io.BytesIO()
    imagem.save(buf, "JPEG", quality=qualidade)
    return buf.getvalue()


def conversa(controle: bool = False) -> str:
    return CONVERSA_NORMAL if controle else CONVERSA_SUSPEITA


def logs_csv(controle: bool = False) -> bytes:
    """Registros de acesso: 6 normais e 2 anomalos (caso) ou 8 normais (controle)."""
    from modulo_ia.deteccao_anomalias import generate_synthetic_logs

    n_anomalos = 0 if controle else 2
    df = generate_synthetic_logs(8 - n_anomalos, n_anomalos, random_state=SEMENTE_LOGS)
    df = df.drop(columns=["e_anomalo_sintetico"])  # rotulo de validacao nao e evidencia
    return df.to_csv(index=False, float_format="%.4f").encode("utf-8")
