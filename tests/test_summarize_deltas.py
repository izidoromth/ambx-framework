"""Testes da tabela de variação (`deltas.csv`).

A variação é a família de números que o texto usa para afirmar quanto o tempo
de acesso subiu entre o cenário típico e cada condicionado. Os testes cobrem
as três coisas que podem dar errado: a estatística em si, o tratamento da
ausência de acesso e a base de comparação entre cenários com coberturas
diferentes.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analysis.summarize_indicators import summarize_deltas  # noqa: E402


def write_city(root: Path, typical_cells: list[int],
               comparisons: dict[str, pd.DataFrame]) -> Path:
    """Cria a estrutura mínima que `summarize_deltas` espera."""
    city_dir = root / "porto_alegre"
    (city_dir / "matrices").mkdir(parents=True, exist_ok=True)

    pd.DataFrame({
        "cell_idx": typical_cells,
        "poi_idx": [1] * len(typical_cells),
        "travel_time": [10.0] * len(typical_cells),
    }).to_parquet(city_dir / "matrices" / "matrix_typical.parquet", index=False)

    for scenario, frame in comparisons.items():
        frame.to_parquet(city_dir / f"comparison_{scenario}.parquet", index=False)

    return root


def comparison(rows: list[tuple]) -> pd.DataFrame:
    """Comparação mínima: (cell_idx, delta_t)."""
    return pd.DataFrame(rows, columns=["cell_idx", "poi_idx", "delta_t"]).assign(
        poi_idx=1
    )[["cell_idx", "poi_idx", "delta_t"]]


class TestBasicStatistics:
    def test_median_and_p90_from_per_cell_deltas(self, tmp_path):
        # Uma célula com dois pares: a mediana da célula é a média dos dois.
        frame = pd.DataFrame({
            "cell_idx": [0, 0, 1, 1, 2, 2],
            "poi_idx": [1, 2, 1, 2, 1, 2],
            "delta_t": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0],
        })
        root = write_city(tmp_path, [0, 1, 2], {"inundacao": frame})

        table = summarize_deltas(root, "porto_alegre")

        # Medianas por célula: 3, 7, 11.
        # Com três pontos, o p90 do pandas interpola entre 7 e 11 -> 10,2.
        row = table.iloc[0]
        assert row["delta_median"] == pytest.approx(7.0)
        assert row["delta_p90"] == pytest.approx(10.2, abs=0.01)

    def test_scenario_name_uses_the_mapping(self, tmp_path):
        frame = pd.DataFrame({"cell_idx": [0], "poi_idx": [1], "delta_t": [1.0]})
        root = write_city(tmp_path, [0], {"inundacao": frame, "combinado": frame})

        table = summarize_deltas(root, "porto_alegre")

        assert set(table["scenario"]) == {"flood", "flood_landsliding"}

    def test_missing_typical_returns_empty(self, tmp_path):
        assert summarize_deltas(tmp_path, "porto_alegre").empty


class TestAccessLoss:
    def test_infinite_delta_counts_as_lost_pair(self, tmp_path):
        frame = pd.DataFrame({
            "cell_idx": [0, 0, 1, 1],
            "poi_idx": [1, 2, 1, 2],
            "delta_t": [1.0, 2.0, np.inf, 3.0],
        })
        root = write_city(tmp_path, [0, 1], {"combinado": frame})

        table = summarize_deltas(root, "porto_alegre")
        row = table.iloc[0]

        assert row["n_pairs"] == 4
        assert row["n_pairs_lost"] == 1
        assert row["pct_pairs_lost"] == pytest.approx(25.0)

    def test_cell_that_loses_every_destination_is_flagged(self, tmp_path):
        frame = pd.DataFrame({
            "cell_idx": [0, 0, 1, 1],
            "poi_idx": [1, 2, 1, 2],
            "delta_t": [1.0, 2.0, np.inf, np.inf],
        })
        root = write_city(tmp_path, [0, 1], {"combinado": frame})

        table = summarize_deltas(root, "porto_alegre")
        row = table.iloc[0]

        assert row["n_cells_lost_access"] == 1
        assert row["pct_cells_lost_access"] == pytest.approx(50.0)

    def test_lost_cells_do_not_enter_the_time_statistics(self, tmp_path):
        # A célula 1 perde tudo; se entrasse como zero, a mediana cairia.
        frame = pd.DataFrame({
            "cell_idx": [0, 0, 1, 1],
            "poi_idx": [1, 2, 1, 2],
            "delta_t": [10.0, 12.0, np.inf, np.inf],
        })
        root = write_city(tmp_path, [0, 1], {"combinado": frame})

        table = summarize_deltas(root, "porto_alegre")
        row = table.iloc[0]

        assert row["delta_median"] == pytest.approx(11.0)
        assert row["n_cells_with_delta"] == 1

    def test_cell_that_keeps_one_destination_is_not_lost(self, tmp_path):
        frame = pd.DataFrame({
            "cell_idx": [0, 0],
            "poi_idx": [1, 2],
            "delta_t": [np.inf, 4.0],
        })
        root = write_city(tmp_path, [0], {"combinado": frame})

        table = summarize_deltas(root, "porto_alegre")
        row = table.iloc[0]

        assert row["n_cells_lost_access"] == 0
        assert row["delta_median"] == pytest.approx(4.0)


class TestSharedBasis:
    def test_shared_stats_restrict_both_scenarios_to_the_intersection(self, tmp_path):
        # inundacao cobre as células 0 e 1; combinado perde a célula 1.
        # A célula 1 tem delta alto na inundação, então a mediana sobre o
        # conjunto próprio difere da mediana sobre a interseção.
        flood = pd.DataFrame({
            "cell_idx": [0, 1],
            "poi_idx": [1, 1],
            "delta_t": [2.0, 100.0],
        })
        combined = pd.DataFrame({
            "cell_idx": [0, 1],
            "poi_idx": [1, 1],
            "delta_t": [4.0, np.inf],
        })
        root = write_city(tmp_path, [0, 1], {"inundacao": flood, "combinado": combined})

        table = summarize_deltas(root, "porto_alegre").set_index("scenario")

        # Base própria: a inundação usa as duas células -> mediana 51.
        assert table.loc["flood", "delta_median"] == pytest.approx(51.0)
        # Base compartilhada: só a célula 0 -> 2.0.
        assert table.loc["flood", "delta_median_shared"] == pytest.approx(2.0)
        assert table.loc["flood", "n_cells_shared"] == 1
        assert table.loc["flood", "delta_median"] != table.loc["flood", "delta_median_shared"]

    def test_shared_basis_equals_own_basis_when_coverage_is_equal(self, tmp_path):
        frame = pd.DataFrame({
            "cell_idx": [0, 1],
            "poi_idx": [1, 1],
            "delta_t": [2.0, 4.0],
        })
        root = write_city(tmp_path, [0, 1], {"inundacao": frame, "combinado": frame})

        table = summarize_deltas(root, "porto_alegre")

        for _, row in table.iterrows():
            assert row["delta_median_shared"] == pytest.approx(row["delta_median"])
            assert row["n_cells_shared"] == 2

    def test_comparison_basis_names_the_smallest_scenario(self, tmp_path):
        wide = pd.DataFrame({"cell_idx": [0, 1, 2], "poi_idx": [1, 1, 1],
                             "delta_t": [1.0, 1.0, 1.0]})
        narrow = pd.DataFrame({"cell_idx": [0, 1], "poi_idx": [1, 1],
                               "delta_t": [2.0, 2.0]})
        root = write_city(tmp_path, [0, 1, 2],
                          {"inundacao": wide, "combinado": narrow})

        table = summarize_deltas(root, "porto_alegre")

        assert set(table["comparison_basis"]) == {"flood_landsliding"}


class TestZeroDeltaDiagnostics:
    def test_counts_cells_with_no_change(self, tmp_path):
        # Duas células sem mudança, uma com mudança.
        frame = pd.DataFrame({
            "cell_idx": [0, 1, 2],
            "poi_idx": [1, 1, 1],
            "delta_t": [0.0, 0.0, 6.0],
        })
        root = write_city(tmp_path, [0, 1, 2], {"movimento_massa": frame})

        table = summarize_deltas(root, "porto_alegre")
        row = table.iloc[0]

        assert row["n_cells_zero_delta"] == 2
        assert row["pct_cells_zero_delta"] == pytest.approx(66.67, abs=0.01)
        # A mediana é zero porque a maioria não mudou, não porque o efeito
        # seja nulo — é isso que a coluna acima permite enxergar.
        assert row["delta_median"] == pytest.approx(0.0)
