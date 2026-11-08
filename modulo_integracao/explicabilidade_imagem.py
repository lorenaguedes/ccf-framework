"""
Explicabilidade da classificacao de imagem (E2) para o laudo pericial.

Orquestra a explicacao LIME (modulo_ia.xai) sobre a probabilidade NSFW real do
modelo, mede a estabilidade entre sementes (indice de Jaccard), grava o mapa de
importancia e registra o SHA-256 do arquivo, para que o artefato de
explicabilidade tenha integridade verificavel tal como a evidencia.

A funcao de predicao e injetada (OpenNSFW2 em producao; funcao sintetica nos
testes), mantendo o modulo testavel sem TensorFlow.
"""
import io
from pathlib import Path
from typing import Callable

import numpy as np

from modulo_ia.xai import criar_predict_lote, explicar_imagem_lime, salvar_mapa_importancia

TAMANHO_EXPLICACAO = (128, 128)  # reduz o custo do LIME; declarado no log


def gerar_explicabilidade_imagem(
    conteudo: bytes,
    predict_fn: Callable,
    pasta_saida: Path,
    nome_mapa: str,
    num_samples: int = 200,
    sementes: tuple = (42, 43, 44),
    limiar_decisao: float = 0.5,
    tamanho: tuple = TAMANHO_EXPLICACAO,
    n_segmentos: int | None = None,
    espaco: str = "probabilidade",
    predict_lote_fn: Callable | None = None,
) -> dict:
    """Gera a explicacao LIME de uma imagem (bytes) e grava o mapa em PNG.

    Returns:
        Dicionario registravel no log do cenario (chave `explicabilidade`),
        sem o array da mascara; inclui mapa_arquivo e mapa_sha256.
    """
    from PIL import Image

    imagem = Image.open(io.BytesIO(conteudo)).convert("RGB").resize(tamanho)
    arr = np.array(imagem)
    explicacao = explicar_imagem_lime(
        arr, criar_predict_lote(predict_fn, espaco, predict_lote_fn),
        num_samples=num_samples, sementes=sementes, n_segmentos=n_segmentos,
    )
    explicacao["espaco_explicado"] = espaco
    mascara = explicacao.pop("mascara")
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    caminho = pasta_saida / nome_mapa
    explicacao["mapa_arquivo"] = nome_mapa
    explicacao["mapa_sha256"] = salvar_mapa_importancia(arr, mascara, caminho)
    explicacao["limiar_decisao"] = limiar_decisao
    explicacao["tamanho_imagem_explicada"] = list(tamanho)
    return explicacao
