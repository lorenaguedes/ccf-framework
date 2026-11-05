"""
Testes unitarios para o modulo de deteccao de grooming (Estagio E4,
RF06, Tabela 12 - PGT).

Estrategia de teste: a funcao de classificacao recebe a funcao de
predicao (predict_fn) por injecao de dependencia, e a funcao que monta
a predicao recebe o codificador (encode_fn) tambem injetado. Assim, a
logica de decisao, a normalizacao e o calculo do score sao testados
sem o codificador real (pesado, requer download de pesos).
"""
import json
import math
from pathlib import Path

import pytest

from modulo_ia.deteccao_grooming import (
    LIMIAR_PADRAO,
    carregar_config,
    classificar_conversa,
    classify_grooming,
    criar_predict_fn,
    normalizar_mensagem,
    preparar_janela,
)


def _predict_fn_baixo_risco(texto: str) -> dict:
    """Simula o modelo retornando baixo score de grooming, sem trechos
    relevantes destacados."""
    return {"score": 0.05, "trechos_relevantes": []}


def _predict_fn_alto_risco(texto: str) -> dict:
    """Simula o modelo retornando alto score de grooming, com trechos
    suspeitos destacados."""
    return {"score": 0.91, "trechos_relevantes": ["segredo", "não conta pra ninguém"]}


def test_classify_returns_expected_structure():
    """O resultado deve conter score, flag e trechos relevantes."""
    resultado = classify_grooming("Oi, tudo bem com você?", _predict_fn_baixo_risco)

    assert "score_grooming" in resultado
    assert "flag" in resultado
    assert "trechos_relevantes" in resultado


def test_classify_low_score_returns_normal_flag():
    """Score baixo deve ser classificado como comunicacao normal."""
    resultado = classify_grooming(
        "Oi, tudo bem com você?", _predict_fn_baixo_risco, threshold=0.5
    )
    assert resultado["flag"] == "NORMAL"


def test_classify_high_score_returns_suspicious_flag():
    """Score alto deve ser sinalizado como suspeito, conforme RF06."""
    resultado = classify_grooming(
        "Isso é nosso segredo, ok?", _predict_fn_alto_risco, threshold=0.5
    )
    assert resultado["flag"] == "SUSPEITO"


def test_classify_suspicious_result_includes_relevant_excerpts():
    """Quando sinalizado como suspeito, os trechos que embasaram a
    decisao devem estar presentes - essencial para a explicabilidade
    textual exigida pelo RF08/laudo pericial."""
    resultado = classify_grooming(
        "Isso é nosso segredo, ok?", _predict_fn_alto_risco, threshold=0.5
    )
    assert len(resultado["trechos_relevantes"]) > 0
    assert "segredo" in resultado["trechos_relevantes"]


def test_classify_empty_text_raises_error():
    """Texto vazio nao deve ser processado silenciosamente - pode
    indicar falha na extracao da conversa, nao um caso valido de
    ausencia de grooming."""
    with pytest.raises(ValueError):
        classify_grooming("", _predict_fn_baixo_risco)


def test_classify_invalid_score_raises_error():
    """Uma funcao de predicao retornando score fora de [0, 1] deve
    ser rejeitada - protege contra falha silenciosa na integracao com
    o modelo real."""
    def predict_fn_invalido(texto):
        return {"score": 1.7, "trechos_relevantes": []}

    with pytest.raises(ValueError):
        classify_grooming("texto qualquer", predict_fn_invalido)


def test_classify_score_equal_to_threshold_is_suspicious():
    """O empate no limiar vai para SUSPEITO (decisao conservadora, no
    contexto de protecao infantil: prefere-se um falso alarme a uma
    omissao), e o limiar padrao e o calibrado na validacao (0,40)."""
    def predict_fn_no_limiar(texto):
        return {"score": LIMIAR_PADRAO, "trechos_relevantes": []}

    resultado = classify_grooming("texto qualquer", predict_fn_no_limiar)
    assert LIMIAR_PADRAO == 0.40
    assert resultado["flag"] == "SUSPEITO"


def test_classify_threshold_is_effective_parameter():
    """O limiar e um parametro efetivo: o mesmo score de 0,91 e
    SUSPEITO com limiar 0,5 e NORMAL com limiar 0,95."""
    suspeito = classify_grooming("x", _predict_fn_alto_risco, threshold=0.5)
    normal = classify_grooming("x", _predict_fn_alto_risco, threshold=0.95)
    assert suspeito["flag"] == "SUSPEITO"
    assert normal["flag"] == "NORMAL"


def test_normalizar_mensagem_replica_o_preprocessamento_do_treino():
    """Entidades HTML, URLs e identificadores de usuario viram
    marcadores, repeticoes sao reduzidas e o texto vai a minusculas."""
    texto = "Don&amp;apos;t   TELL!!!!! https://exemplo.com/x " + "a" * 5
    resultado = normalizar_mensagem(texto)
    assert resultado == "don't tell!! <url> aa"
    id_usuario = "0123456789abcdef0123456789abcdef"
    assert normalizar_mensagem(f"oi {id_usuario}") == "oi <user>"


def test_preparar_janela_usa_as_k_ultimas_mensagens_nao_vazias():
    """A janela une as mensagens por ' / ', ignora vazias e mantem
    apenas as k ultimas, formato usado no treino."""
    mensagens = ["um", "", "dois", "tres", "quatro", "cinco", "seis"]
    assert preparar_janela(mensagens, k=5) == "dois / tres / quatro / cinco / seis"


def test_preparar_janela_sem_texto_gera_erro():
    """Janela sem nenhuma mensagem com texto indica falha de extracao
    e nao deve ser tratada como conversa normal."""
    with pytest.raises(ValueError):
        preparar_janela(["", "   "])


def _config_sintetica():
    # score = sigmoid(2*v0 - 1) para vetores de 2 dimensoes
    return {"encoder": "fake", "coef": [2.0, 0.0], "intercept": -1.0,
            "limiar_f1max": 0.40, "limiar_rec90": 0.20}


def _encode_sintetico(textos):
    # v0 = 1 se o texto contem "segredo", senao 0
    return [[1.0 if "segredo" in t else 0.0, 0.0] for t in textos]


def test_criar_predict_fn_calcula_probabilidade_logistica():
    """O score deve ser a sigmoide de coef.v + intercepto, calculada
    sem scikit-learn, e ficar em [0, 1]."""
    predict_fn = criar_predict_fn(_config_sintetica(), _encode_sintetico)
    com_segredo = predict_fn("isso e um segredo")["score"]
    sem_segredo = predict_fn("bom dia")["score"]
    assert com_segredo == pytest.approx(1 / (1 + math.exp(-1.0)))
    assert sem_segredo == pytest.approx(1 / (1 + math.exp(1.0)))
    assert 0.0 <= sem_segredo < com_segredo <= 1.0


def test_criar_predict_fn_rejeita_codificador_de_dimensao_incompativel():
    """Codificador com dimensao diferente da dos coeficientes deve
    gerar erro, e nao um score silenciosamente errado."""
    predict_fn = criar_predict_fn(_config_sintetica(), lambda textos: [[1.0, 0.0, 0.0] for _ in textos])
    with pytest.raises(ValueError):
        predict_fn("qualquer texto")


def test_explicacao_por_oclusao_aponta_a_mensagem_mais_influente():
    """O trecho relevante e a mensagem cuja remocao mais reduz o score."""
    predict_fn = criar_predict_fn(_config_sintetica(), _encode_sintetico)
    saida = predict_fn("oi tudo bem / isso e um segredo / ate mais")
    assert saida["trechos_relevantes"] == ["isso e um segredo"]


def test_classificar_conversa_usa_a_janela_de_maior_score():
    """Conversa longa e dividida em janelas de k mensagens, e o
    resultado e o da janela mais suspeita."""
    def predict_fn(texto):
        return {"score": 0.9 if "segredo" in texto else 0.1, "trechos_relevantes": []}

    mensagens = [f"mensagem {i}" for i in range(10)]
    mensagens[7] = "isso e um segredo"
    resultado = classificar_conversa(mensagens, predict_fn, threshold=0.4, k=5)
    assert resultado["flag"] == "SUSPEITO"
    assert resultado["n_janelas"] == 2
    assert resultado["indice_janela_mais_suspeita"] == 1


def test_carregar_config_valida_campos_obrigatorios(tmp_path):
    """Arquivo de modelo sem campos obrigatorios deve ser rejeitado."""
    valido = tmp_path / "modelo.json"
    valido.write_text(json.dumps(_config_sintetica()), encoding="utf-8")
    assert carregar_config(str(valido))["encoder"] == "fake"

    incompleto = tmp_path / "incompleto.json"
    incompleto.write_text(json.dumps({"encoder": "fake"}), encoding="utf-8")
    with pytest.raises(ValueError):
        carregar_config(str(incompleto))


_MODELO_REAL = Path(__file__).resolve().parents[1] / "models" / "modelo_e4_embeddings.json"


@pytest.mark.skipif(not _MODELO_REAL.exists(), reason="modelo exportado do notebook ausente")
def test_modelo_real_exportado_e_consistente():
    """O JSON versionado do modelo final deve ser carregavel, com
    coeficientes de dimensao igual a do codificador (768, mpnet) e
    limiares validos, com o de recall >= 90% abaixo do de F1 maximo."""
    config = carregar_config(str(_MODELO_REAL))
    assert len(config["coef"]) == 768
    assert "mpnet" in config["encoder"]
    assert 0.0 < config["limiar_rec90"] < config["limiar_f1max"] < 1.0
