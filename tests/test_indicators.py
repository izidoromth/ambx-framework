"""Testes dos indicadores de acessibilidade (PTh, F15, Gini).

Cada caso usa valores que podem ser conferidos à mão, para que a falha
indique o cálculo e não a complexidade do dado.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ambx.indicators import (  # noqa: E402
    compute_all_indicators,
    compute_f15,
    compute_gini,
    compute_pth,
    compute_pth_wide,
)


def matrix(rows: list[tuple]) -> pd.DataFrame:
    """Monta uma matriz OD a partir de (cell_idx, poi_category, travel_time)."""
    return pd.DataFrame(rows, columns=["cell_idx", "poi_category", "travel_time"])


class TestComputePth:
    def test_averages_k_nearest_of_each_category(self):
        # Célula 0: education 10, 20, 40 -> os 2 menores são 10 e 20 -> 15
        #            health    5, 7        -> os 2 menores são 5 e 7   -> 6
        data = matrix([
            (0, "education", 10.0),
            (0, "education", 20.0),
            (0, "education", 40.0),
            (0, "health", 5.0),
            (0, "health", 7.0),
        ])

        result = compute_pth(data, k=2).set_index(["cell_idx", "poi_category"])["pth"]

        assert result[(0, "education")] == pytest.approx(15.0)
        assert result[(0, "health")] == pytest.approx(6.0)

    def test_without_k_uses_all_pois(self):
        data = matrix([
            (0, "health", 10.0),
            (0, "health", 20.0),
            (0, "health", 40.0),
        ])

        result = compute_pth(data, k=None)

        assert result["pth"].iloc[0] == pytest.approx(70.0 / 3.0)

    def test_infinite_times_are_discarded(self):
        # A aresta interditada devolve `inf`; ela não pode entrar na média.
        data = matrix([
            (0, "health", 10.0),
            (0, "health", np.inf),
            (0, "health", 20.0),
        ])

        result = compute_pth(data, k=2)

        assert result["pth"].iloc[0] == pytest.approx(15.0)

    def test_cell_without_reachable_poi_is_absent(self):
        # Se todos os pares são infinitos, a célula não aparece: ausência de
        # acesso não é tempo zero.
        data = matrix([
            (0, "health", np.inf),
            (1, "health", 8.0),
        ])

        result = compute_pth(data, k=1)

        assert list(result["cell_idx"]) == [1]

    def test_k_larger_than_available_uses_available(self):
        data = matrix([
            (0, "health", 4.0),
            (0, "health", 6.0),
        ])

        result = compute_pth(data, k=5)

        assert result["pth"].iloc[0] == pytest.approx(5.0)

    def test_empty_matrix_returns_empty_frame(self):
        result = compute_pth(matrix([]), k=3)

        assert result.empty
        assert list(result.columns) == ["cell_idx", "poi_category", "pth"]


class TestComputePthWide:
    def test_one_row_per_cell_and_one_column_per_category(self):
        long = pd.DataFrame({
            "cell_idx": [1, 1, 2, 2],
            "poi_category": ["health", "education", "health", "education"],
            "pth": [10.0, 20.0, 30.0, 40.0],
        })

        wide = compute_pth_wide(long)

        assert wide.index.tolist() == [1, 2]
        assert wide.loc[1, "health"] == pytest.approx(10.0)
        assert wide.loc[2, "education"] == pytest.approx(40.0)

    def test_missing_pair_becomes_nan(self):
        long = pd.DataFrame({
            "cell_idx": [1, 2],
            "poi_category": ["health", "education"],
            "pth": [10.0, 40.0],
        })

        wide = compute_pth_wide(long)

        assert math.isnan(wide.loc[1, "education"])
        assert math.isnan(wide.loc[2, "health"])


class TestComputeGini:
    def test_perfect_equality_is_zero(self):
        assert compute_gini(pd.Series([10.0, 10.0, 10.0, 10.0])) == pytest.approx(0.0)

    def test_known_value(self):
        # Gini de [0, 10, 20, 30] = 0.4167 (conferido à mão).
        assert compute_gini(pd.Series([0.0, 10.0, 20.0, 30.0])) == pytest.approx(0.4167, abs=1e-4)

    def test_single_value_is_zero(self):
        assert compute_gini(pd.Series([7.0])) == pytest.approx(0.0)

    def test_non_finite_values_are_ignored(self):
        with_nan = compute_gini(pd.Series([10.0, np.nan, np.inf, 10.0]))
        clean = compute_gini(pd.Series([10.0, 10.0]))

        assert with_nan == pytest.approx(clean)

    def test_negative_values_raise(self):
        with pytest.raises(ValueError, match="não-negativos"):
            compute_gini(pd.Series([10.0, -5.0]))

    def test_population_weighting_changes_the_result(self):
        # Duas células com tempos 10 e 30. Sem peso, Gini = 0.25.
        values = pd.Series([10.0, 30.0], index=["a", "b"])
        assert compute_gini(values) == pytest.approx(0.25, abs=1e-9)

        # Concentrando a população na célula mais rápida, a desigualdade
        # sentida pelas pessoas cai.
        concentrated = pd.Series([90.0, 10.0], index=["a", "b"])
        assert compute_gini(values, population=concentrated) < 0.25

    def test_zero_population_weight_returns_nan(self):
        values = pd.Series([10.0, 30.0], index=["a", "b"])
        empty = pd.Series([0.0, 0.0], index=["a", "b"])

        assert math.isnan(compute_gini(values, population=empty))


class TestComputeF15:
    def test_known_value(self):
        pth = pd.Series([5.0, 12.0, 20.0, 8.0])
        pop = pd.Series([100, 200, 150, 50])

        # Servidos: 5, 12 e 8 -> 100 + 200 + 50 = 350 de 500.
        assert compute_f15(pth, pop) == pytest.approx(0.70)

    def test_threshold_is_inclusive(self):
        pth = pd.Series([15.0])
        pop = pd.Series([100.0])

        assert compute_f15(pth, pop, threshold=15.0) == pytest.approx(1.0)

    def test_cells_absent_from_pth_stay_in_denominator(self):
        # A célula "c" não tem POI alcançável: não conta como servida, mas a
        # população dela permanece no denominador.
        pth = pd.Series([5.0], index=["a"])
        pop = pd.Series([100.0, 100.0], index=["a", "c"])

        assert compute_f15(pth, pop) == pytest.approx(0.5)

    def test_custom_threshold(self):
        pth = pd.Series([5.0, 25.0, 35.0])
        pop = pd.Series([100.0, 100.0, 100.0])

        assert compute_f15(pth, pop, threshold=30.0) == pytest.approx(2 / 3)

    def test_zero_population_returns_nan(self):
        pth = pd.Series([5.0])
        pop = pd.Series([0.0])

        assert math.isnan(compute_f15(pth, pop))


class TestComputeAllIndicators:
    def test_returns_both_scenarios_with_expected_keys(self):
        typical = matrix([
            (0, "health", 10.0),
            (1, "health", 20.0),
        ])
        conditioned = matrix([
            (0, "health", 20.0),
            (1, "health", 40.0),
        ])
        population = pd.Series([50.0, 50.0], index=[0, 1])

        result = compute_all_indicators(typical, conditioned, population=population)

        for suffix in ("typ", "cond"):
            assert f"pth_{suffix}" in result
            assert f"pth_wide_{suffix}" in result
            assert f"gini_{suffix}" in result
            assert f"f15_{suffix}" in result
            assert f"perda_acesso_{suffix}" in result

    def test_f15_drops_when_times_grow(self):
        typical = matrix([(0, "health", 10.0), (1, "health", 10.0)])
        conditioned = matrix([(0, "health", 10.0), (1, "health", 40.0)])
        population = pd.Series([100.0, 100.0], index=[0, 1])

        result = compute_all_indicators(typical, conditioned, population=population)

        assert result["f15_typ"]["health"] == pytest.approx(1.0)
        assert result["f15_cond"]["health"] == pytest.approx(0.5)

    def test_unreachable_cells_are_counted_as_access_loss(self):
        typical = matrix([(0, "health", 10.0), (1, "health", 10.0)])
        conditioned = matrix([(0, "health", 10.0), (1, "health", np.inf)])
        population = pd.Series([100.0, 100.0], index=[0, 1])

        result = compute_all_indicators(typical, conditioned, population=population)

        loss = result["perda_acesso_cond"]["health"]
        assert loss["n_inacessiveis"] == 1
        assert loss["pct_inacessiveis"] == pytest.approx(50.0)

    def test_single_scenario_still_works(self):
        typical = matrix([(0, "health", 10.0)])

        result = compute_all_indicators(typical)

        assert "pth_typ" in result
        assert "pth_cond" not in result
