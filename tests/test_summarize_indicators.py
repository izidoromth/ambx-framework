"""Testes da sumarização de indicadores e das linhas `overall`.

A sumarização é a camada que produz as tabelas da dissertação, então os
testes verificam tanto os valores por categoria quanto as agregações
ponderadas, que não são exercitadas pelos testes de `ambx.indicators`.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analysis.summarize_indicators import (  # noqa: E402
    load_population,
    summarize_city,
    weighted_median,
)


class TestWeightedMedian:
    def test_weights_do_not_move_a_symmetric_distribution(self):
        assert weighted_median(np.array([10.0, 20.0, 30.0]), np.ones(3)) == pytest.approx(20.0)

    def test_weight_concentrated_on_one_value(self):
        # 90% da massa em 10: a mediana ponderada é 10, mesmo com 30 presente.
        values = np.array([10.0, 30.0])
        weights = np.array([90.0, 10.0])

        assert weighted_median(values, weights) == pytest.approx(10.0)

    def test_exactly_half(self):
        # Massa acumulada cruza 50% exatamente no primeiro valor (50 de 100),
        # então a mediana ponderada fica nele.
        values = np.array([10.0, 20.0])
        weights = np.array([50.0, 50.0])

        assert weighted_median(values, weights) == pytest.approx(10.0)

    def test_zero_total_weight_is_nan(self):
        assert math.isnan(weighted_median(np.array([1.0, 2.0]), np.array([0.0, 0.0])))

    def test_unsorted_input_is_ordered_first(self):
        values = np.array([30.0, 10.0, 20.0])
        weights = np.array([1.0, 1.0, 1.0])

        assert weighted_median(values, weights) == pytest.approx(20.0)


def write_city(root: Path, matrices: dict[str, pd.DataFrame], population: dict[int, float]) -> Path:
    """Cria a estrutura mínima que `summarize_city` espera."""
    city_dir = root / "curitiba"
    (city_dir / "matrices").mkdir(parents=True, exist_ok=True)
    (city_dir / "prepared").mkdir(parents=True, exist_ok=True)

    for filename, matrix in matrices.items():
        matrix.to_parquet(city_dir / "matrices" / f"{filename}.parquet", index=False)

    pd.DataFrame({
        "cell_idx": list(population),
        "populacao": list(population.values()),
    }).to_parquet(city_dir / "prepared" / "ids.parquet", index=False)

    return root


class TestSummarizeCity:
    def test_rows_per_category_plus_one_overall(self, tmp_path):
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (0, "education", 20.0),
            (1, "health", 30.0),
            (1, "education", 40.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 50.0, 1: 50.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)

        assert sorted(table["category"]) == ["education", "health", "overall"]
        assert (table["scenario"] == "typical").all()

    def test_overall_is_the_mean_of_the_categories(self, tmp_path):
        # health: (10 + 30) / 2 = 20 por célula, média entre células = 20
        # education: (20 + 40) / 2 = 30 por célula, média entre células = 30
        # overall = (20 + 30) / 2 = 25
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (0, "education", 20.0),
            (1, "health", 30.0),
            (1, "education", 40.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 50.0, 1: 50.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)
        overall = table[table["category"] == "overall"].iloc[0]

        assert overall["pth_mean_cell"] == pytest.approx(25.0)
        assert overall["pth_mean_pop_weighted"] == pytest.approx(25.0)

    def test_population_weighting_uses_the_weights(self, tmp_path):
        # health por célula: 0 -> 10, 1 -> 30. População toda na célula 0.
        # Média simples = 20; média ponderada = 10.
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (1, "health", 30.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 100.0, 1: 0.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)
        health = table[table["category"] == "health"].iloc[0]

        assert health["pth_mean_cell"] == pytest.approx(20.0)
        assert health["pth_mean_pop_weighted"] == pytest.approx(10.0)

    def test_overall_takes_the_mean_of_weighted_values(self, tmp_path):
        # Duas categorias com o mesmo PTh por célula: o overall tem de ser
        # igual a elas, com ou sem peso.
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (0, "education", 10.0),
            (1, "health", 30.0),
            (1, "education", 30.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 100.0, 1: 0.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)
        overall = table[table["category"] == "overall"].iloc[0]

        assert overall["pth_mean_pop_weighted"] == pytest.approx(10.0)
        assert overall["pth_median_pop_weighted"] == pytest.approx(10.0)

    def test_unreachable_cells_are_counted(self, tmp_path):
        # Célula 1 só tem POI inalcançável em health.
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (1, "health", np.inf),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 50.0, 1: 50.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)
        health = table[table["category"] == "health"].iloc[0]

        assert health["n_cells"] == 2
        assert health["n_reachable"] == 1
        assert health["n_unreachable"] == 1
        assert health["pct_unreachable"] == pytest.approx(50.0)

    def test_f15_uses_the_population(self, tmp_path):
        # health: célula 0 com 10 min e célula 1 com 30 min, população igual.
        # F15 = 50%.
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (1, "health", 30.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 50.0, 1: 50.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)
        health = table[table["category"] == "health"].iloc[0]

        assert health["f15_pop_weighted"] == pytest.approx(0.5)

    def test_k_and_threshold_are_recorded(self, tmp_path):
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (0, "health", 20.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 50.0})

        table, _ = summarize_city(root, "curitiba", k=2, threshold=12.0)

        assert (table["k"] == 2).all()
        assert (table["threshold_min"] == 12.0).all()

    def test_overall_counts_cells_without_any_reachable_category(self, tmp_path):
        # Célula 0 alcança saúde, célula 1 só tem POI inalcançável.
        # A célula 1 não alcança nenhuma categoria, então entra em
        # n_unreachable do geral — perder um serviço não é perder acesso.
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (1, "health", np.inf),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 50.0, 1: 50.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)
        overall = table[table["category"] == "overall"].iloc[0]

        assert overall["n_cells"] == 2
        assert overall["n_unreachable"] == 1
        assert overall["pct_unreachable"] == pytest.approx(50.0)

    def test_overall_is_reachable_when_at_least_one_category_is(self, tmp_path):
        # Célula 1 alcança educação mas não saúde: não conta como sem acesso.
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (0, "education", 10.0),
            (1, "health", np.inf),
            (1, "education", 12.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(tmp_path, {"matrix_typical": matrix}, {0: 50.0, 1: 50.0})

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)
        overall = table[table["category"] == "overall"].iloc[0]
        health = table[table["category"] == "health"].iloc[0]

        assert health["n_unreachable"] == 1
        assert overall["n_unreachable"] == 0

    def test_scenario_names_come_from_the_mapping(self, tmp_path):
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (0, "education", 10.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        root = write_city(
            tmp_path,
            {"matrix_typical": matrix, "matrix_lst": matrix, "matrix_lst_demo_k05": matrix},
            {0: 50.0},
        )

        table, _ = summarize_city(root, "curitiba", k=1, threshold=15.0)

        # Os nomes internos dos arquivos não vazam para a tabela.
        assert set(table["scenario"]) == {"typical", "thermal", "thermal_demo_k05"}

    def test_missing_population_falls_back_to_unweighted(self, tmp_path):
        matrix = pd.DataFrame([
            (0, "health", 10.0),
            (1, "health", 30.0),
        ], columns=["cell_idx", "poi_category", "travel_time"])
        city_dir = tmp_path / "curitiba"
        (city_dir / "matrices").mkdir(parents=True, exist_ok=True)
        matrix.to_parquet(city_dir / "matrices" / "matrix_typical.parquet", index=False)

        table, _ = summarize_city(tmp_path, "curitiba", k=1, threshold=15.0)
        health = table[table["category"] == "health"].iloc[0]

        assert health["pth_mean_pop_weighted"] == pytest.approx(20.0)
        assert health["f15_pop_weighted"] is None


class TestLoadPopulation:
    def test_reads_population_indexed_by_cell(self, tmp_path):
        city_dir = tmp_path / "curitiba" / "prepared"
        city_dir.mkdir(parents=True)
        pd.DataFrame({"cell_idx": [0, 1], "populacao": [10.0, 20.0]}).to_parquet(
            city_dir / "ids.parquet", index=False
        )

        population = load_population(tmp_path, "curitiba")

        assert population is not None
        assert population.loc[1] == pytest.approx(20.0)

    def test_returns_none_when_file_is_missing(self, tmp_path):
        assert load_population(tmp_path, "curitiba") is None

    def test_returns_none_without_population_column(self, tmp_path):
        city_dir = tmp_path / "curitiba" / "prepared"
        city_dir.mkdir(parents=True)
        pd.DataFrame({"cell_idx": [0], "ids": [0.5]}).to_parquet(
            city_dir / "ids.parquet", index=False
        )

        assert load_population(tmp_path, "curitiba") is None
