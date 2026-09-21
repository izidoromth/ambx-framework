"""Smoke test da composição de penalização e atenuação."""

from pathlib import Path
import sys

import geopandas as gpd
from shapely.geometry import LineString, Polygon

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from ambx.environment import EnvironmentLayers, load_vector  # noqa: E402
from ambx.penalties import CostModifier, compose_penalties  # noqa: E402


def test_penalty_and_mitigation_are_composed(tmp_path):
    penalty_path = tmp_path / "risk.parquet"
    green_path = tmp_path / "green.parquet"

    gpd.GeoDataFrame(
        {"classe": ["Alta"]},
        geometry=[Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])],
        crs="EPSG:31982",
    ).to_parquet(penalty_path)
    gpd.GeoDataFrame(
        {"presence": [1]},
        geometry=[Polygon([(0, 0), (5, 0), (5, 10), (0, 10)])],
        crs="EPSG:31982",
    ).to_parquet(green_path)

    env = EnvironmentLayers()
    env.add_vector(load_vector(penalty_path, name="risk", value_column="classe"))
    env.add_vector(load_vector(green_path, name="green", value_column="presence"))

    edges = gpd.GeoDataFrame(
        {"travel_time": [10.0]},
        geometry=[LineString([(1, 1), (9, 1)])],
        crs="EPSG:31982",
    )
    rules = [
        CostModifier("risk", "vector", "travel_time", lambda value: 2.0),
        CostModifier(
            "green", "vector", "travel_time", lambda value: 0.5,
            aggregation="mean",
        ),
    ]

    result = compose_penalties(edges, env, rules=rules)

    # Aresta: 100% em risco, 50% em área verde.
    # 10 × 2.0 × ((50% × 0.5) + (50% × 1.0)) = 15.
    assert result.loc[0, "travel_time"] == 15.0


def test_high_risk_line_with_two_mitigation_segments(tmp_path):
    """Verifica duas áreas de mitigação sobre uma aresta contínua."""
    risk_path = tmp_path / "risk.parquet"
    green_path = tmp_path / "green.parquet"

    gpd.GeoDataFrame(
        {"classe": ["Alta"]},
        geometry=[Polygon([(-1, -1), (11, -1), (11, 1), (-1, 1)])],
        crs="EPSG:31982",
    ).to_parquet(risk_path)
    gpd.GeoDataFrame(
        {"presence": [1, 1]},
        geometry=[
            Polygon([(1, -1), (3, -1), (3, 1), (1, 1)]),
            Polygon([(4, -1), (8, -1), (8, 1), (4, 1)]),
        ],
        crs="EPSG:31982",
    ).to_parquet(green_path)

    env = EnvironmentLayers()
    env.add_vector(load_vector(risk_path, name="risk", value_column="classe"))
    env.add_vector(load_vector(green_path, name="green", value_column="presence"))

    edges = gpd.GeoDataFrame(
        {"travel_time": [10.0]},
        geometry=[LineString([(0, 0), (10, 0)])],
        crs="EPSG:31982",
    )
    rules = [
        CostModifier("risk", "vector", "travel_time", lambda value: 2.0),
        CostModifier(
            "green", "vector", "travel_time", lambda value: 0.5,
            aggregation="mean",
        ),
    ]

    result = compose_penalties(edges, env, rules=rules)

    # Mitigação cobre 6/10 da aresta: (6 × 0.5 + 4 × 1) / 10 = 0.7.
    # Custo final: 10 × 2.0 × 0.7 = 14.
    assert result.loc[0, "travel_time"] == 14.0
