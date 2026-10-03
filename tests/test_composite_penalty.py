"""Testes de regras compostas com raster e vetor."""

from pathlib import Path
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, Polygon

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


def _lst_green_penalty(values):
    """1.2 se estiver quente e sobre área verde; 1.5 caso contrário.

    Ausência de dado (``None``/``NaN``) → sem atenuação.
    """
    lst = values["lst"]
    green = values["green"]
    is_hot = pd.notna(lst) and lst > 30
    is_green = pd.notna(green) and bool(green)
    return 1.2 if (is_hot and is_green) else 1.5


def _rule(**kwargs):
    return PenaltyRule(
        layer_type="composite",
        weight_field="travel_time",
        penalty_fn=_lst_green_penalty,
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


def test_composite_raster_transforms_to_source_crs(tmp_path):
    """Raster carregado com ``dst_crs`` diferente do arquivo deve ser amostrado
    corretamente (coordenadas transformadas para o CRS do arquivo de origem).

    Reproduz o cenário de ``build_environment``, que reprojeta o raster para o
    CRS UTM da análise: ``layer.crs`` passa a ser UTM enquanto o arquivo segue
    em EPSG:4326.
    """
    raster_path = tmp_path / "lst_wgs84.tif"
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        nodata=-9999.0,
        transform=from_origin(-49.28, -25.42, 0.001, 0.001),
    ) as dst:
        dst.write(np.full((10, 10), 34, dtype="float32"), 1)

    layer = load_raster(raster_path, name="lst", dst_crs=CRS)
    assert str(layer.crs) == CRS

    center = (
        gpd.GeoSeries([Point(-49.275, -25.425)], crs="EPSG:4326")
        .to_crs(CRS)
        .iloc[0]
    )
    edges = gpd.GeoDataFrame(
        {"travel_time": [100.0]},
        geometry=[
            LineString([(center.x - 20, center.y), (center.x + 20, center.y)])
        ],
        crs=CRS,
    )

    env = EnvironmentLayers()
    env.add_raster(layer)
    rule = PenaltyRule(
        layer_type="composite",
        weight_field="travel_time",
        penalty_fn=lambda values: 2.0 if values["lst"] > 30 else 1.0,
        layers=["lst"],
        sampling="midpoint",
    )

    result = compose_penalties(edges, env, [rule])

    # Se as coordenadas não fossem transformadas, a amostragem cairia fora do
    # raster (nodata) e o fator seria 1.0 → 100.0.
    assert result.loc[0, "travel_time"] == 200.0


def test_composite_passes_nan_for_uncovered_points(tmp_path):
    """Ponto fora de qualquer polígono chega como NaN à ``penalty_fn``.

    O valor não é substituído por 1.0: o fator retornado pela função é honrado.
    """
    env = _environment(tmp_path, green_end=5)
    edges = gpd.GeoDataFrame(
        {"travel_time": [100.0]},
        geometry=[LineString([(20, 0), (30, 0)])],
        crs=CRS,
    )
    seen = []

    def penalty(values):
        seen.append(values["green"])
        return 2.0

    rule = PenaltyRule(
        layer_type="composite",
        weight_field="travel_time",
        penalty_fn=penalty,
        layers=["green"],
        sampling="midpoint",
    )

    result = compose_penalties(edges, env, [rule])

    assert len(seen) == 1
    assert pd.isna(seen[0])
    assert result.loc[0, "travel_time"] == 200.0


def test_composite_dict_always_contains_all_keys(tmp_path):
    """O dict da regra composta sempre traz todas as chaves de ``layers``.

    A ausência de dado no ponto vem no **valor** (``None``/``NaN``), nunca
    como chave faltante.
    """
    env = _environment(tmp_path, green_end=5)  # verde cobre x em [0, 5]
    edges = gpd.GeoDataFrame(
        {"travel_time": [100.0]},
        # Ponto médio (7.5, 0): dentro do raster, fora do polígono verde.
        geometry=[LineString([(6, 0), (9, 0)])],
        crs=CRS,
    )
    seen = {}

    def penalty(values):
        seen.update(values)
        return 1.0

    rule = PenaltyRule(
        layer_type="composite",
        weight_field="travel_time",
        penalty_fn=penalty,
        layers=["lst", "green"],
        sampling="midpoint",
    )

    compose_penalties(edges, env, [rule])

    assert set(seen) == {"lst", "green"}  # nenhuma chave faltante
    assert not pd.isna(seen["lst"])       # raster tem dado no ponto
    assert pd.isna(seen["green"])         # fora do polígono -> sem dado


def test_compose_penalties_does_not_mutate_rule(tmp_path):
    """``compose_penalties`` não deve alterar o ``weight_field`` da regra."""
    env = _environment(tmp_path, green_end=10)
    edges = gpd.GeoDataFrame(
        {"travel_time": [100.0]},
        geometry=[LineString([(0, 0), (10, 0)])],
        crs=CRS,
    )
    rule = PenaltyRule(
        layer_type="composite",
        weight_field=None,
        penalty_fn=lambda values: 1.5,
        layers=["green"],
        sampling="midpoint",
    )

    compose_penalties(edges, env, [rule], weight_field="travel_time")

    assert rule.weight_field is None
