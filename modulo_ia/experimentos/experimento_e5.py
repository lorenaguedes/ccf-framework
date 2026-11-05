"""
Experimento de avaliacao do Estagio E5 (Isolation Forest, RF07) - secao 4.4.5 do PGT.

Protocolo: treino e teste sao gerados com sementes distintas (sem vazamento);
o modelo e treinado sem rotulos (nao supervisionado) e os rotulos sinteticos
so sao usados para medir o desempenho. Repete-se com 30 sementes e varia-se a
severidade das anomalias (1,0 = perfil do modulo; menores = anomalias mais
proximas do normal), para mostrar ate onde a deteccao se sustenta.

Uso:  poetry run python -m modulo_ia.experimentos.experimento_e5
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from modulo_ia.deteccao_anomalias import detect_anomalies, fit_isolation_forest

FEATURES = ["volume_transferencia_mb", "frequencia_acesso_hora", "tamanho_medio_arquivo_mb"]
NORMAL = {"volume_transferencia_mb": (50, 10), "frequencia_acesso_hora": (5, 2), "tamanho_medio_arquivo_mb": (3, 1)}
ANOMALO = {"volume_transferencia_mb": (500, 100), "frequencia_acesso_hora": (50, 10), "tamanho_medio_arquivo_mb": (3, 1)}
SEVERIDADES = [1.0, 0.5, 0.25, 0.10]
CONTAMINACOES = ["auto", 0.1]
SEMENTES = list(range(30))
N_NORMAL, N_ANOM = 1000, 100  # prevalencia de anomalias ~9,1%


def gerar(n_normal, n_anom, severidade, seed):
    """Mesmo gerador do modulo, com a severidade interpolando media e desvio
    entre o perfil normal (0) e o anomalo (1). Com severidade 1,0 reproduz os
    mesmos parametros de generate_synthetic_logs (diferindo apenas no piso dos
    valores, 0,1 em todas as features)."""
    rng = np.random.default_rng(seed)
    def amostra(n, perfil, rotulo):
        d = {}
        for col in FEATURES:
            m0, s0 = NORMAL[col]; m1, s1 = ANOMALO[col]
            m = m0 + severidade * (m1 - m0); s = s0 + severidade * (s1 - s0)
            d[col] = rng.normal(m if perfil == "a" else m0, s if perfil == "a" else s0, n).clip(min=0.1)
        d["e_anomalo_sintetico"] = rotulo
        return pd.DataFrame(d)
    df = pd.concat([amostra(n_normal, "n", False), amostra(n_anom, "a", True)], ignore_index=True)
    return df.sample(frac=1, random_state=seed).reset_index(drop=True)


def metricas(df_res):
    y = df_res["e_anomalo_sintetico"].to_numpy()
    p = (df_res["flag"] == "ANOMALO").to_numpy()
    tp, fp = int((y & p).sum()), int((~y & p).sum())
    fn, tn = int((y & ~p).sum()), int((~y & ~p).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"auc": roc_auc_score(y, -df_res["anomaly_score"]), "precisao": prec, "recall": rec,
            "f1": f1, "fpr": fp / (fp + tn)}


def main():
    linhas = []
    for sev in SEVERIDADES:
        for cont in CONTAMINACOES:
            for s in SEMENTES:
                treino = gerar(N_NORMAL, N_ANOM, sev, seed=1000 + s)
                teste = gerar(N_NORMAL, N_ANOM, sev, seed=2000 + s)
                modelo = fit_isolation_forest(treino[FEATURES], contamination=cont, random_state=s)
                linhas.append({"severidade": sev, "contamination": str(cont), "semente": s,
                               **metricas(detect_anomalies(teste, modelo, FEATURES))})
    df = pd.DataFrame(linhas)
    resumo = df.groupby(["severidade", "contamination"])[["auc", "precisao", "recall", "f1", "fpr"]].agg(["mean", "std"]).round(3)
    pd.set_option("display.width", 200)
    print(resumo.to_string())
    saida = Path(__file__).with_name("resultados_e5.json")
    saida.write_text(json.dumps(df.to_dict("records"), indent=1), encoding="utf-8")
    print(f"\nResultados brutos em {saida}")


if __name__ == "__main__":
    main()
