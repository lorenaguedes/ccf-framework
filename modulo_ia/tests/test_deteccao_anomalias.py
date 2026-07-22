"""
Testes unitarios para o modulo de deteccao de anomalias (Estagio E5,
RF07, Tabela 12 - PGT).

Diferente dos estagios anteriores (E2/E3/E4), o Isolation Forest e um
modelo leve (scikit-learn, CPU), permitindo testar diretamente com
dados sinteticos deterministicos, sem necessidade de injecao de
dependencia para um modelo pesado externo.
"""
import pandas as pd
import pytest

from modulo_ia.deteccao_anomalias import (
    detect_anomalies,
    fit_isolation_forest,
    generate_synthetic_logs,
)


def test_generate_synthetic_logs_returns_expected_columns():
    """Os logs sinteticos devem conter as features de comportamento
    descritas na Secao 2.2.3 do PGT (volume, frequencia, tamanho)."""
    df = generate_synthetic_logs(n_normal=50, n_anomalous=5, random_state=42)

    colunas_esperadas = {
        "volume_transferencia_mb",
        "frequencia_acesso_hora",
        "tamanho_medio_arquivo_mb",
    }
    assert colunas_esperadas.issubset(set(df.columns))


def test_generate_synthetic_logs_is_deterministic():
    """A mesma semente deve gerar exatamente os mesmos dados -
    reprodutibilidade (RNF02)."""
    df1 = generate_synthetic_logs(n_normal=50, n_anomalous=5, random_state=42)
    df2 = generate_synthetic_logs(n_normal=50, n_anomalous=5, random_state=42)

    pd.testing.assert_frame_equal(df1, df2)


def test_generate_synthetic_logs_returns_expected_total_count():
    """O total de registros deve ser a soma de normais e anomalos."""
    df = generate_synthetic_logs(n_normal=50, n_anomalous=5, random_state=42)
    assert len(df) == 55


def test_fit_isolation_forest_returns_fitted_model():
    """O modelo treinado deve estar apto a fazer predicoes."""
    df = generate_synthetic_logs(n_normal=100, n_anomalous=0, random_state=42)
    features = ["volume_transferencia_mb", "frequencia_acesso_hora", "tamanho_medio_arquivo_mb"]

    modelo = fit_isolation_forest(df[features], random_state=42)

    # Um modelo treinado deve conseguir gerar predicoes sem erro
    predicoes = modelo.predict(df[features])
    assert len(predicoes) == len(df)


def test_detect_anomalies_flags_synthetic_anomalies():
    """Eventos gerados deliberadamente como anomalos devem ser
    detectados com taxa de recall razoavel - o proprio motivo do
    modulo existir (RF07)."""
    df = generate_synthetic_logs(n_normal=200, n_anomalous=20, random_state=42)
    features = ["volume_transferencia_mb", "frequencia_acesso_hora", "tamanho_medio_arquivo_mb"]

    modelo = fit_isolation_forest(df[features], contamination=0.1, random_state=42)
    resultado = detect_anomalies(df, modelo, features)

    # Verifica que pelo menos a maioria dos anomalos sinteticos (marcados
    # na coluna auxiliar 'e_anomalo_sintetico') foram detectados
    anomalos_reais = resultado[resultado["e_anomalo_sintetico"]]
    taxa_deteccao = (anomalos_reais["flag"] == "ANOMALO").mean()

    assert taxa_deteccao >= 0.5  # pelo menos metade detectada - baseline razoavel


def test_detect_anomalies_returns_expected_structure():
    """O resultado deve conter score de anomalia e flag para cada
    registro."""
    df = generate_synthetic_logs(n_normal=50, n_anomalous=5, random_state=42)
    features = ["volume_transferencia_mb", "frequencia_acesso_hora", "tamanho_medio_arquivo_mb"]

    modelo = fit_isolation_forest(df[features], random_state=42)
    resultado = detect_anomalies(df, modelo, features)

    assert "anomaly_score" in resultado.columns
    assert "flag" in resultado.columns
    assert set(resultado["flag"].unique()).issubset({"NORMAL", "ANOMALO"})


def test_fit_isolation_forest_requires_valid_contamination():
    """Um valor de contamination fora do intervalo (0, 0.5] deve ser
    rejeitado - protege contra configuracao invalida do modelo."""
    df = generate_synthetic_logs(n_normal=50, n_anomalous=5, random_state=42)
    features = ["volume_transferencia_mb", "frequencia_acesso_hora", "tamanho_medio_arquivo_mb"]

    with pytest.raises(ValueError):
        fit_isolation_forest(df[features], contamination=0.9, random_state=42)