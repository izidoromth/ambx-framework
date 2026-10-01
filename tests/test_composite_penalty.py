"""Testes de regras compostas com raster e vetor."""

from pathlib import Path
import sys

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Polygon

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from ambx.environment import EnvironmentLayers, load_vector, load_raster  # noqa: E402
from ambx.penalties import PenaltyRule, compose_penalties  # noqa: E402


CRS = "EPSG:31982"


def _environment(tmp_path, green_end=10):
    raster_path = tmp_path / "lst.tif"
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=2,
        width=10,
        count=1,
        dtype="float32",
        crs=CRS,
        transform=from_origin(0, 1, 1, 1),
    ) as dst:
        dst.write(np.full((2, 10), 34, dtype="float32"), 1)

    green = gpd.GeoDataFrame(
        {"presence": [1]},
        geometry=[Polygon([(0, -1), (green_end, -1),
                           (green_end, 1), (0, 1)])],
        crs=CRS,
    )
    green_path = tmp_path / "green.parquet"
    green.to_parquet(green_path)

    env = EnvironmentLayers()
    env.add_raster(load_raster(raster_path, name="lst"))
    env.add_vector(load_vector(green_path, name="green", value_column="presence"))
    return env


def _rule(**kwargs):
    return PenaltyRule(
        layer_name=None,
        layer_type="composite",
        weight_field="travel_time",
        penalty_fn=lambda values: 1.2 if values["lst"] > 30 and values["green"] else 1.5,
        layers=["lst", "green"],
        **kwargs,
    )


def test_composite_midpoint_uses_raster_and_vector_at_same_point(tmp_path):
    env = _environment(tmp_path, green_end=10)
    edges = gpd.GeoDataFrame(
        {"travel_time": [100.0]},
        geometry=[LineString([(0, 0), (10, 0)])],
        crs=CRS,
    )

    result = compose_penalties(edges, env, [_rule(sampling="midpoint")])

    assert result.loc[0, "travel_time"] == 120.0


def test_composite_segments_aggregates_joint_factors(tmp_path):
    env = _environment(tmp_path, green_end=5)
    edges = gpd.GeoDataFrame(
        {"travel_time": [100.0]},
        geometry=[LineString([(0, 0), (10, 0)])],
        crs=CRS,
    )

    result = compose_penalties(
        edges,
        env,
        [_rule(sampling="segments", n_samples=5, aggregation="mean")],
    )

    # Fatores nos pontos: 1.2, 1.2, 1.2, 1.5, 1.5.
    # Regra do trapézio: (1.2 + 1.5 + 2*(1.2+1.2+1.5)) / 8 = 1.3125.
    assert result.loc[0, "travel_time"] == 131.25
