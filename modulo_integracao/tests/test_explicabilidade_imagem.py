"""Testes da explicabilidade de imagem (LIME) no laudo de C1."""
import hashlib
import io

import numpy as np
import pytest
from PIL import Image

from modulo_ia.xai import jaccard_regioes, resumir_mascara
from modulo_integracao.explicabilidade_imagem import gerar_explicabilidade_imagem
from modulo_integracao.laudo_pericial import formatar_xai, montar_xai_imagem


def _png(cor=(120, 120, 120), lado=64) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (lado, lado), cor).save(buf, format="PNG")
    return buf.getvalue()


def _predict_quadrante(imagem) -> float:
    """Modelo sintetico: a probabilidade depende do brilho do quadrante superior esquerdo."""
    a = np.array(imagem.convert("L"), dtype=float)
    h, w = a.shape
    return float(a[: h // 2, : w // 2].mean() / 255.0)


def test_jaccard_identicas_e_disjuntas():
    m = np.zeros((10, 10)); m[:5, :5] = 1.0
    n = np.zeros((10, 10)); n[5:, 5:] = 1.0
    assert jaccard_regioes(m, m) == 1.0
    assert jaccard_regioes(m, n) == 0.0


def test_jaccard_sem_sinal_retorna_none():
    z = np.zeros((8, 8))
    assert jaccard_regioes(z, z) is None
    assert resumir_mascara(z)["sinal_suficiente"] is False


def test_resumo_caixa_delimitadora():
    m = np.zeros((10, 10)); m[2:4, 3:6] = 1.0
    r = resumir_mascara(m)
    assert r["caixa_delimitadora"] == [2, 3, 3, 5]
    assert r["fracao_area_alta_importancia"] == pytest.approx(0.06)


def test_gerar_explicabilidade_grava_mapa_com_hash(tmp_path):
    # imagem com gradiente para haver segmentos distintos
    arr = np.zeros((64, 64, 3), dtype="uint8"); arr[:32, :32] = 250; arr[32:, 32:] = 90
    buf = io.BytesIO(); Image.fromarray(arr).save(buf, format="PNG")
    exp = gerar_explicabilidade_imagem(buf.getvalue(), _predict_quadrante, tmp_path, "mapa.png",
                                       num_samples=60, sementes=(1, 2), tamanho=(64, 64))
    arquivo = tmp_path / "mapa.png"
    assert arquivo.exists()
    assert exp["mapa_sha256"] == hashlib.sha256(arquivo.read_bytes()).hexdigest()
    assert exp["sementes"] == [1, 2] and exp["metodo"].startswith("LIME")
    assert "mascara" not in exp


def test_montar_xai_imagem_sfw_ou_sem_explicacao_retorna_none():
    assert montar_xai_imagem({"flag": "SFW", "probabilidade_nsfw": 0.01}, {"metodo": "LIME"}) is None
    assert montar_xai_imagem({"flag": "NSFW"}, None) is None


def test_montar_xai_imagem_forcado_declara_forcamento():
    cls = {"flag": "NSFW", "probabilidade_nsfw": 0.0102, "classificador_forcado": True, "flag_original": "SFW"}
    exp = {"metodo": "LIME (segmentos de imagem)", "num_samples": 200, "sementes": [42, 43],
           "estabilidade_jaccard": 0.8, "resumo": {"fracao_area_alta_importancia": 0.1,
                                                   "caixa_delimitadora": [0, 0, 5, 5]},
           "mapa_arquivo": "m.png", "mapa_sha256": "ab" * 32}
    x = montar_xai_imagem(cls, exp)
    assert "FORCADO" in x["ressalva"] and "0.0102" in x["ressalva"]
    assert x["estabilidade_jaccard"] == 0.8 and x["escore"] == 0.0102
    texto = formatar_xai(x)
    assert "Estabilidade (Jaccard entre sementes): 0.8" in texto


def test_formatar_xai_aceita_texto_simples():
    assert formatar_xai("Nao aplicavel") == "Nao aplicavel"


def test_medir_estabilidade_modelo_deterministico_e_estavel():
    from modulo_integracao.cenarios_simulacao.experimento_xai_estabilidade import medir_estabilidade
    from modulo_ia.xai import criar_predict_lote

    arr = np.zeros((48, 48, 3), dtype="uint8"); arr[:24, :24] = 250; arr[24:, 24:] = 90
    r = medir_estabilidade(arr, criar_predict_lote(_predict_quadrante), amostras=80, pares=2)
    assert r["pares"] == 2 and r["jaccard_medio"] is not None and 0.0 <= r["jaccard_medio"] <= 1.0


def test_predict_lote_logit_e_lote_fn():
    from modulo_ia.xai import criar_predict_lote
    arr = np.full((2, 8, 8, 3), 100, dtype="uint8")
    pl = criar_predict_lote(lambda im: 0.5, "logit", predict_lote_fn=lambda ims: [0.5, 0.9])
    r = pl(arr)
    assert r[0] == pytest.approx(0.0) and r[1] == pytest.approx(np.log(9))
    with pytest.raises(ValueError):
        criar_predict_lote(lambda im: 0.5, "outro")


def test_explicacao_slic_registra_segmentacao_e_espaco(tmp_path):
    arr = np.zeros((64, 64, 3), dtype="uint8"); arr[:32, :32] = 250; arr[32:, 32:] = 90
    buf = io.BytesIO(); Image.fromarray(arr).save(buf, format="PNG")
    exp = gerar_explicabilidade_imagem(buf.getvalue(), _predict_quadrante, tmp_path, "m.png", num_samples=60,
                                       sementes=(1, 2), tamanho=(64, 64), n_segmentos=8, espaco="logit")
    assert exp["segmentacao"].startswith("SLIC") and exp["espaco_explicado"] == "logit"
