"""
Modulo de deteccao de grooming (aliciamento) - Estagio E4 (RF06,
Tabela 12, PGT).

Classifica janelas de mensagens quanto a padroes linguisticos de
aliciamento. O modelo final e composto por embeddings de sentencas
multilingues congelados (paraphrase-multilingual-mpnet-base-v2) e um
classificador de regressao logistica, treinados no Colab sobre o
corpus de teste do PAN 2012 com rotulos por janela (ver secao 4.4.4 do
PGT e o notebook E4 no repositorio). Os parametros do classificador
(coeficientes, intercepto e limiares) sao carregados de um arquivo
JSON, de modo que a inferencia nao depende de scikit-learn.

Estrategia de design: a funcao de classificacao recebe a funcao de
predicao (predict_fn) por injecao de dependencia, permitindo testes
unitarios rapidos sem o codificador real (pesado, requer download).
O codificador tambem e injetado em criar_predict_fn (encode_fn).

USO PERICIAL: o estagio e uma TRIAGEM sujeita a revisao humana. Em
prevalencias realistas a precisao e baixa (ver secao 4.4.4.7 do PGT e
ADR 008); nunca deve ser usado como evidencia por si so.
"""
import html
import json
import math
import re
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

# Limiar calibrado na validacao (maximiza o F1; semente 42 do experimento).
# O limiar e especifico da particao de calibracao: recalibrar em cada
# implantacao e preferir o valor gravado no arquivo do modelo.
LIMIAR_PADRAO = 0.40

# Tamanho da janela de mensagens usada no treino (mensagens consecutivas).
K_MENSAGENS = 5

_RE_URL = re.compile(r"(https?://\S+|www\.\S+)", re.I)
_RE_HEX = re.compile(r"\b[0-9a-f]{32}\b")
_RE_REP = re.compile(r"(.)\1{2,}")
_CAMPOS_OBRIGATORIOS = ("encoder", "coef", "intercept", "limiar_f1max", "limiar_rec90")


def normalizar_mensagem(texto: str) -> str:
    """Normaliza uma mensagem exatamente como no treino: converte
    entidades HTML, substitui identificadores de usuario, e-mails e URLs
    por marcadores, reduz repeticoes de caracteres e converte para
    minusculas. A divergencia entre esta funcao e a do treino degradaria
    o desempenho sem gerar erro."""
    t = html.unescape(html.unescape(texto or ""))
    t = t.replace("<email/>", " <email> ")
    t = _RE_HEX.sub(" <user> ", t)
    t = _RE_URL.sub(" <url> ", t)
    t = _RE_REP.sub(r"\1\1", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def preparar_janela(mensagens: Sequence[str], k: int = K_MENSAGENS) -> str:
    """Normaliza as mensagens e monta a janela de texto (as k ultimas
    mensagens nao vazias, unidas por ' / '), formato usado no treino.

    Raises:
        ValueError: se nenhuma mensagem tiver texto.
    """
    normalizadas = [normalizar_mensagem(m) for m in mensagens]
    normalizadas = [m for m in normalizadas if m]
    if not normalizadas:
        raise ValueError(
            "Nenhuma mensagem com texto: pode indicar falha na extracao "
            "da conversa, nao ausencia valida de grooming."
        )
    return " / ".join(normalizadas[-k:])


def classify_grooming(
    text: str,
    predict_fn: Callable[[str], dict],
    threshold: float = LIMIAR_PADRAO,
) -> dict:
    """Classifica uma janela de texto quanto a padroes de grooming,
    usando uma funcao de predicao externa.

    Args:
        text: janela de mensagens ja preparada (ver preparar_janela).
        predict_fn: funcao que recebe um texto e retorna um dicionario
            com "score" (float, 0.0-1.0) e "trechos_relevantes" (lista
            de trechos que mais contribuiram para o score).
        threshold: limiar de decisao. Valores >= threshold sao
            classificados como SUSPEITO (o empate vai para SUSPEITO,
            dado o contexto de protecao infantil).

    Returns:
        Dicionario com score_grooming, flag ("SUSPEITO" ou "NORMAL") e
        trechos_relevantes (explicabilidade textual, RF08).

    Raises:
        ValueError: se o texto for vazio, ou se o score retornado
            estiver fora do intervalo valido [0, 1].
    """
    if not text or not text.strip():
        raise ValueError(
            "Texto vazio nao pode ser classificado: pode indicar "
            "falha na extracao da conversa, nao ausencia valida de grooming."
        )

    resultado_predicao = predict_fn(text)
    score = resultado_predicao["score"]
    trechos = resultado_predicao.get(
        "trechos_relevantes", resultado_predicao.get("tokens_relevantes", [])
    )

    if not (0.0 <= score <= 1.0):
        raise ValueError(
            f"Score de grooming invalido: {score}. "
            "Deve estar no intervalo [0.0, 1.0]."
        )

    flag = "SUSPEITO" if score >= threshold else "NORMAL"

    return {
        "score_grooming": score,
        "flag": flag,
        "trechos_relevantes": trechos,
    }


def classificar_conversa(
    mensagens: Sequence[str],
    predict_fn: Callable[[str], dict],
    threshold: float = LIMIAR_PADRAO,
    k: int = K_MENSAGENS,
) -> dict:
    """Classifica uma conversa inteira por janelas consecutivas de k
    mensagens (passo k) e devolve o resultado da janela de maior score.

    O modelo foi treinado com janelas de 5 mensagens: conversas mais
    curtas viram uma unica janela. A conversa e SUSPEITA se qualquer
    janela atingir o limiar.

    Returns:
        O dicionario de classify_grooming para a janela mais suspeita,
        acrescido de n_janelas e indice_janela_mais_suspeita.
    """
    textos = [normalizar_mensagem(m) for m in mensagens]
    textos = [m for m in textos if m]
    if not textos:
        raise ValueError(
            "Nenhuma mensagem com texto: conversa nao pode ser classificada."
        )
    janelas = [" / ".join(textos[i:i + k]) for i in range(0, len(textos), k)]
    if len(janelas) > 1 and len(textos[(len(janelas) - 1) * k:]) < k:
        # ultima janela incompleta: refaz com as k ultimas mensagens
        janelas[-1] = " / ".join(textos[-k:])

    resultados = [classify_grooming(j, predict_fn, threshold) for j in janelas]
    melhor = max(range(len(resultados)), key=lambda i: resultados[i]["score_grooming"])
    saida = dict(resultados[melhor])
    saida["n_janelas"] = len(janelas)
    saida["indice_janela_mais_suspeita"] = melhor
    return saida


def carregar_config(caminho: str) -> dict:
    """Le o arquivo JSON do modelo (coeficientes, intercepto, limiares).

    Raises:
        ValueError: se faltar algum campo obrigatorio ou se a dimensao
            dos coeficientes for inconsistente.
    """
    with open(caminho, encoding="utf-8") as f:
        config = json.load(f)
    faltando = [c for c in _CAMPOS_OBRIGATORIOS if c not in config]
    if faltando:
        raise ValueError(f"Arquivo de modelo invalido, campos ausentes: {faltando}")
    if not config["coef"]:
        raise ValueError("Arquivo de modelo invalido: coeficientes vazios.")
    return config


def criar_predict_fn(
    config: dict,
    encode_fn: Callable[[Sequence[str]], Sequence[Sequence[float]]],
    top_k: int = 2,
) -> Callable[[str], dict]:
    """Monta a funcao de predicao a partir dos parametros do modelo e de
    uma funcao de codificacao injetada (textos -> vetores normalizados).

    O score e a probabilidade da regressao logistica. Os trechos
    relevantes sao as mensagens da janela cuja remocao mais reduz o
    score (oclusao), e nao pesos internos do modelo.
    """
    coef = np.asarray(config["coef"], dtype=float)
    intercept = float(config["intercept"])

    def _score(texto: str) -> float:
        v = np.asarray(encode_fn([texto])[0], dtype=float)
        if v.shape != coef.shape:
            raise ValueError(
                f"Dimensao do embedding ({v.shape[0]}) difere da dos "
                f"coeficientes ({coef.shape[0]}): codificador incompativel."
            )
        z = float(np.clip(coef @ v + intercept, -500.0, 500.0))
        return 1.0 / (1.0 + math.exp(-z))

    def predict_fn(text: str) -> dict:
        score = _score(text)
        partes = [p for p in text.split(" / ") if p.strip()]
        trechos = []
        if len(partes) > 1:
            influencia = []
            for i, parte in enumerate(partes):
                sem_parte = " / ".join(partes[:i] + partes[i + 1:])
                influencia.append((score - _score(sem_parte), parte))
            influencia.sort(key=lambda par: -par[0])
            trechos = [parte for delta, parte in influencia[:top_k] if delta > 0]
        return {"score": score, "trechos_relevantes": trechos}

    return predict_fn


def create_embedding_predict_fn(model_path: str) -> Callable[[str], dict]:  # pragma: no cover
    """Cria a funcao de predicao real: carrega o codificador
    multilingue (download de ~1 GB no primeiro uso) e os parametros do
    classificador gravados em model_path (JSON exportado do notebook).

    Excluida da cobertura de testes unitarios propositalmente: depende
    do modelo real e do download dos pesos, e e validada por execucao
    direta, nao por mock. A logica de decisao, a normalizacao e a
    montagem do score sao cobertas por testes com codificador injetado.

    Args:
        model_path: caminho do JSON do modelo (ex.:
            modulo_ia/models/modelo_e4_embeddings.json).
    """
    from sentence_transformers import SentenceTransformer

    config = carregar_config(model_path)
    codificador = SentenceTransformer(config["encoder"])
    codificador.max_seq_length = 128

    def encode_fn(textos):
        return codificador.encode(
            list(textos), normalize_embeddings=True, show_progress_bar=False
        )

    return criar_predict_fn(config, encode_fn)
