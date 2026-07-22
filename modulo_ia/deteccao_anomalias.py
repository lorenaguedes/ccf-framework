"""
Modulo de deteccao de anomalias em logs de nuvem - Estagio E5 (RF07,
Tabela 12, PGT).

Usa Isolation Forest (Liu, Ting & Zhou, 2008) para identificar
comportamentos atipicos em metricas de uso (volume de transferencia,
frequencia de acesso, tamanho medio de arquivos), conforme Secao 2.2.3
do PGT. Os logs sao sinteticos, gerados por script de simulacao,
coerente com a Secao 1.6.2-B (componentes simulados).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def generate_synthetic_logs(
    n_normal: int,
    n_anomalous: int,
    random_state: int = 42,
) -> pd.DataFrame:
    """Gera logs sinteticos de comportamento de acesso a nuvem,
    simulando um perfil normal e um perfil deliberadamente anomalo
    (volumes de transferencia muito altos, frequencia de acesso muito
    alta, tamanhos de arquivo atipicos), conforme descrito na Secao
    2.2.3 do PGT.

    Args:
        n_normal: numero de registros de comportamento normal.
        n_anomalous: numero de registros de comportamento anomalo.
        random_state: semente para reprodutibilidade (RNF02).

    Returns:
        DataFrame com as colunas de features e uma coluna auxiliar
        'e_anomalo_sintetico' (bool), usada apenas para validacao
        experimental - nao deve ser usada como feature de treino.
    """
    rng = np.random.default_rng(random_state)

    normais = pd.DataFrame({
        "volume_transferencia_mb": rng.normal(loc=50, scale=10, size=n_normal).clip(min=0),
        "frequencia_acesso_hora": rng.normal(loc=5, scale=2, size=n_normal).clip(min=0),
        "tamanho_medio_arquivo_mb": rng.normal(loc=3, scale=1, size=n_normal).clip(min=0.1),
        "e_anomalo_sintetico": False,
    })

    anomalos = pd.DataFrame({
        "volume_transferencia_mb": rng.normal(loc=500, scale=100, size=n_anomalous).clip(min=0),
        "frequencia_acesso_hora": rng.normal(loc=50, scale=10, size=n_anomalous).clip(min=0),
        "tamanho_medio_arquivo_mb": rng.normal(loc=3, scale=1, size=n_anomalous).clip(min=0.1),
        "e_anomalo_sintetico": True,
    })

    df = pd.concat([normais, anomalos], ignore_index=True)
    return df.sample(frac=1, random_state=random_state).reset_index(drop=True)


def fit_isolation_forest(
    features_df: pd.DataFrame,
    contamination: float = "auto",
    random_state: int = 42,
) -> IsolationForest:
    """Treina um modelo Isolation Forest sobre as features fornecidas.

    Args:
        features_df: DataFrame contendo apenas as colunas numericas de
            features (sem colunas auxiliares de validacao).
        contamination: proporcao esperada de anomalias no conjunto de
            dados (0.0-0.5) ou "auto". Usado como referencia interna
            do modelo para definir o limiar de decisao.
        random_state: semente para reprodutibilidade (RNF02).

    Returns:
        Modelo IsolationForest treinado.

    Raises:
        ValueError: se contamination estiver fora do intervalo valido
            (0, 0.5].
    """
    if contamination != "auto" and not (0.0 < contamination <= 0.5):
        raise ValueError(
            f"contamination invalido: {contamination}. "
            "Deve estar no intervalo (0.0, 0.5] ou ser 'auto'."
        )

    modelo = IsolationForest(contamination=contamination, random_state=random_state)
    modelo.fit(features_df)
    return modelo


def detect_anomalies(
    df: pd.DataFrame,
    modelo: IsolationForest,
    feature_columns: list,
) -> pd.DataFrame:
    """Aplica o modelo treinado para detectar anomalias nos registros,
    retornando o score de anomalia e uma flag de classificacao.

    Args:
        df: DataFrame completo (pode conter colunas auxiliares).
        modelo: Isolation Forest ja treinado (fit_isolation_forest).
        feature_columns: lista de nomes de colunas usadas como features.

    Returns:
        Copia do DataFrame original, acrescida de:
        - anomaly_score: score bruto do modelo (quanto mais negativo,
          mais anomalo)
        - flag: "ANOMALO" ou "NORMAL"
    """
    resultado = df.copy()
    features = df[feature_columns]

    resultado["anomaly_score"] = modelo.decision_function(features)
    predicoes = modelo.predict(features)  # -1 = anomalo, 1 = normal
    resultado["flag"] = np.where(predicoes == -1, "ANOMALO", "NORMAL")

    return resultado