"""Teste mínimo do uso de GeoParquet como camada de penalização."""

from pathlib import Path
import sys

import geopandas as gpd
from shapely.geometry import LineString, Polygon

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from ambx.environment import EnvironmentLayers, load_vector  # noqa: E402
from ambx.penalties import PenaltyRule, compose_penalties  # noqa: E402


def test_geoparquet_vector_penalty(tmp_path):
    layer_path = tmp_path / "risco.parquet"
    polygons = gpd.GeoDataFrame(
        {"classe": ["Alta"]},
        geometry=[Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])],
        crs="EPSG:31982",
    )
    polygons.to_parquet(layer_path)

    layer = load_vector(
        layer_path,
        name="risco",
        value_column="classe",
    )
    env = EnvironmentLayers()
    env.add_vector(layer)

    edges = gpd.GeoDataFrame(
        {"travel_time": [10.0, 10.0]},
        geometry=[
            LineString([(1, 1), (9, 1)]),
            LineString([(20, 20), (30, 20)]),
        ],
        crs="EPSG:31982",
    )
    rule = PenaltyRule(
        layer_name="risco",
        layer_type="vector",
        weight_field="travel_time",
        penalty_fn=lambda value: 2.0 if value == "Alta" else 1.0,
    )

    result = compose_penalties(edges, env, rules=[rule])

    assert result.loc[0, "travel_time"] == 20.0
    assert result.loc[1, "travel_time"] == 10.0
