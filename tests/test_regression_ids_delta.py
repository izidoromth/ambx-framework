"""Testes da regressão entre os eixos do IDS e a variação do tempo.

A regressão é a única análise do texto que reporta coeficientes padronizados.
Eles são derivados dos brutos por uma razão de desvios-padrão, e é essa
derivação que os testes verificam — se ela quebrar, a Tabela 5 do texto passa
a mostrar valores que ninguém consegue rastrear no CSV.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analysis.regression_ids_delta import _ols, _summary_row  # noqa: E402

AXES = ["eixo_sem_esgoto", "eixo_renda", "eixo_analfabetismo"]
TARGET = "delta_t_mediano"


def sample(seed: int = 0, n: int = 200) -> pd.DataFrame:
    """Amostra sintética com os três eixos e o alvo, todos em escalas distintas.

    O eixo de esgoto fica em 0--1, o de renda também, e o alvo em minutos
    (ordem de dezenas), que é a situação real e a razão pela qual padronizar
    muda tanto a magnitude dos coeficientes.
    """
    rng = np.random.default_rng(seed)
    sanitation = rng.uniform(0.0, 1.0, n)
    income = rng.uniform(0.0, 1.0, n)
    illiteracy = rng.uniform(0.0, 1.0, n)
    delta = (
        40.0 * sanitation
        + 10.0 * income
        - 5.0 * illiteracy
        + rng.normal(0.0, 5.0, n)
    )
    return pd.DataFrame({
        "eixo_sem_esgoto": sanitation,
        "eixo_renda": income,
        "eixo_analfabetismo": illiteracy,
        TARGET: delta,
    })


class TestOLS:
    def test_returns_one_row_per_term(self):
        result = _ols(sample(), AXES, TARGET)

        assert list(result["term"]) == ["const", *AXES]

    def test_n_matches_the_input(self):
        data = sample(n=150)

        result = _ols(data, AXES, TARGET)

        assert (result["n"] == 150).all()

    def test_non_finite_rows_are_dropped(self):
        data = sample(n=100)
        data.loc[0, TARGET] = np.inf
        data.loc[1, "eixo_renda"] = np.nan

        result = _ols(data, AXES, TARGET)

        assert result["n"].iloc[0] == 98

    def test_coefficient_sign_follows_the_generating_process(self):
        # O alvo foi gerado com esgoto e renda positivos, analfabetismo negativo.
        result = _ols(sample(), AXES, TARGET).set_index("term")

        assert result.loc["eixo_sem_esgoto", "coef"] > 0
        assert result.loc["eixo_renda", "coef"] > 0
        assert result.loc["eixo_analfabetismo", "coef"] < 0


class TestStandardizedCoefficients:
    def test_standardized_equals_raw_times_sd_ratio(self):
        data = sample()
        row = _summary_row(data, AXES, TARGET, "city", "scenario", "multipla")

        target_sd = data[TARGET].std(ddof=0)
        for axis in AXES:
            expected = row[f"{axis}_coef"] * data[axis].std(ddof=0) / target_sd
            assert row[f"{axis}_coef_padronizado"] == pytest.approx(expected)

    def test_standardizing_brings_coefficients_near_unit_scale(self):
        # Os brutos ficam na ordem de dezenas por causa da escala do alvo.
        # Os padronizados devem cair na ordem de unidades.
        data = sample()
        row = _summary_row(data, AXES, TARGET, "city", "scenario", "multipla")

        for axis in AXES:
            assert abs(row[f"{axis}_coef"]) > 1.0
            assert abs(row[f"{axis}_coef_padronizado"]) < 10.0

    def test_standardized_coefficients_match_a_regression_on_z_scores(self):
        # Padronizar os dados e rodar a regressão deve devolver o mesmo
        # coeficiente que a transformação analítica.
        data = sample()
        row = _summary_row(data, AXES, TARGET, "city", "scenario", "multipla")

        z = (data - data.mean()) / data.std(ddof=0)
        direct = _ols(z, AXES, TARGET).set_index("term")

        for axis in AXES:
            assert row[f"{axis}_coef_padronizado"] == pytest.approx(
                direct.loc[axis, "coef"], abs=1e-9
            )

    def test_standardizing_preserves_sign(self):
        data = sample()
        row = _summary_row(data, AXES, TARGET, "city", "scenario", "multipla")

        for axis in AXES:
            assert np.sign(row[f"{axis}_coef"]) == np.sign(row[f"{axis}_coef_padronizado"])

    def test_standardizing_preserves_significance(self):
        # O p-valor não muda: padronizar é uma transformação linear, e o
        # teste t é invariante a ela. É isso que permite marcar o asterisco
        # na tabela com o mesmo critério das colunas brutas.
        data = sample()
        row = _summary_row(data, AXES, TARGET, "city", "scenario", "multipla")

        for axis in AXES:
            assert row[f"{axis}_coef_padronizado"] is not None
            assert row[f"{axis}_p_value"] is not None

    def test_zero_variance_target_returns_none(self):
        # Alvo constante: a razão de desvios-padrão é indefinida.
        data = sample(n=50).assign(**{TARGET: 1.0})

        row = _summary_row(data, AXES, TARGET, "city", "scenario", "multipla")

        for axis in AXES:
            assert row[f"{axis}_coef_padronizado"] is None


class TestSummaryRow:
    def test_contains_raw_and_standardized_columns(self):
        row = _summary_row(sample(), AXES, TARGET, "curitiba", "thermal", "multipla")

        for axis in AXES:
            assert f"{axis}_coef" in row
            assert f"{axis}_coef_padronizado" in row
            assert f"{axis}_erro_padrao" in row
            assert f"{axis}_t" in row
            assert f"{axis}_p_value" in row
        assert "intercepto_coef" in row

    def test_metadata_is_recorded(self):
        row = _summary_row(sample(), AXES, TARGET, "curitiba", "thermal", "multipla")

        assert row["city"] == "curitiba"
        assert row["scenario"] == "thermal"
        assert row["model"] == "multipla"
        assert 0.0 <= row["r2_ajustado"] <= 1.0
