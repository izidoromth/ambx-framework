"""Experimento: erro de discretização x número de amostras (composite).

Compara as duas semânticas de penalização oferecidas pela lib:

- **cumulativa** — duas regras simples em sequência (LST depois verde). Pondera
  a área verde pelo *comprimento* real da interseção, mas **não** expressa
  interação: desconta verde mesmo onde não há calor.
- **composta** — uma regra só, que vê LST e verde **no mesmo ponto** e aplica o
  desconto apenas onde há calor. A proporção de cobertura é *aproximada* por
  amostragem, com erro que depende de ``n_samples``.

O script mede o erro da composite contra a referência exata (cumulativa) e
mostra a convergência conforme ``n_samples`` cresce.

Uso:
    python scripts/experiments/composite_sampling_tradeoff.py
"""

from __future__ import annotations

import sys
import tempfile
from math import isnan
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Polygon

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from ambx.environment import EnvironmentLayers, load_raster, load_vector
from ambx.penalties import PenaltyRule, compose_penalties

CRS = "EPSG:31982"
N_EDGES = 10          # arestas de teste
EDGE_LEN = 100.0      # metros
COVERED = 40.0        # metros cobertos por área verde (40%)
TEMP = 38.0           # °C em toda a extensão
GREEN_FACTOR = 0.75   # atenuação onde há verde


def _setup(tmp: Path) -> tuple[EnvironmentLayers, gpd.GeoDataFrame, float]:
    """Monta raster/verde sintéticos e as arestas de teste."""
    rpath = tmp / "lst.tif"
    with rasterio.open(
        rpath, "w", driver="GTiff", height=2000, width=2000, count=1,
        dtype="float32", crs=CRS, nodata=-9999.0,
        transform=from_origin(0, 2000, 1, 1),
    ) as dst:
        dst.write(np.full((2000, 2000), TEMP, dtype="float32"), 1)

    # Verde cobre os primeiros COVERED metros de cada aresta.
    # A aresta i vai de (i*200 + 20) a (i*200 + 20 + EDGE_LEN).
    polys = [
        Polygon([(i * 200 + 20, 0), (i * 200 + 20 + COVERED, 0),
                 (i * 200 + 20 + COVERED, 2000), (i * 200 + 20, 2000)])
        for i in range(N_EDGES)
    ]
    vpath = tmp / "verde.parquet"
    gpd.GeoDataFrame({"presence": [1] * len(polys)}, geometry=polys,
                     crs=CRS).to_parquet(vpath)

    env = EnvironmentLayers()
    env.add_raster(load_raster(rpath, name="lst"))
    env.add_vector(load_vector(vpath, name="verde", value_column="presence"))

    edges = gpd.GeoDataFrame(
        {"travel_time": np.full(N_EDGES, EDGE_LEN)},
        geometry=[
            LineString([(i * 200 + 20, 1000), (i * 200 + 20 + EDGE_LEN, 1000)])
            for i in range(N_EDGES)
        ],
        crs=CRS,
    )
    return env, edges, edges.geometry.iloc[0].length


def _lst_factor(t: float) -> float:
    if t <= 25:
        return 1.0
    if t <= 27:
        return 1.2
    if t <= 30:
        return 1.5
    return 2.0


def _composite_fn(values: dict) -> float:
    """Verde atenua **apenas** onde há calor."""
    lst, verde = values["lst"], values["verde"]
    if lst is None or isnan(lst):
        return 1.0
    if lst <= 25:
        return 1.0
    tem_verde = verde is not None and not isnan(verde) and verde > 0
    return _lst_factor(lst) * (GREEN_FACTOR if tem_verde else 1.0)


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    env, edges, length = _setup(tmp)

    # Referência: fator exato pela proporção de comprimento.
    coberto = edges.geometry.apply(
        lambda g: sum(g.intersection(p).length for p in env.vectors[0].gdf.geometry)
    ).mean()
    frac = coberto / length
    exato = EDGE_LEN * _lst_factor(TEMP) * (frac * GREEN_FACTOR + (1 - frac) * 1.0)

    print("=" * 72)
    print(f"TRADE-OFF DA AMOSTRAGEM COMPOSTA  ({N_EDGES} arestas de {EDGE_LEN:.0f} m)")
    print(f"verde cobre {coberto:.0f} m ({frac * 100:.0f}%)  |  LST {TEMP:.0f} C")
    print(f"referencia exata: {exato:.2f}")
    print("=" * 72)

    r_lst = PenaltyRule("lst", "raster", "travel_time", _lst_factor,
                        sampling="segments", n_samples=4, aggregation="max")
    r_green = PenaltyRule("verde", "vector", "travel_time",
                          lambda _v: GREEN_FACTOR, aggregation="mean")
    out = compose_penalties(edges, env, [r_lst, r_green])
    v_cum = out["travel_time"].mean()
    print(f"\n{'cumulativa':<16}{v_cum:>10.2f}{(v_cum - exato) / exato * 100:>10.2f}%")

    print(f"\n{'n_samples':>10}{'valor':>10}{'erro':>10}")
    for n in (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2056, 4096, 8192):
        rule = PenaltyRule(layer_name=None, layer_type="composite",
                           weight_field="travel_time", penalty_fn=_composite_fn,
                           layers=["lst", "verde"],
                           sampling="segments", n_samples=n, aggregation="mean")
        res = compose_penalties(edges, env, [rule])
        v = res["travel_time"].mean()
        print(f"{n:>10}{v:>10.2f}{(v - exato) / exato * 100:>10.2f}%")

    print("\nNota: o erro e de discretizacao (a fronteira do poligono cai entre")
    print("pontos). Nao e monotonico ponto a ponto, mas a amplitude diminui")
    print("conforme n_samples cresce, convergindo para o valor da cumulativa.")


if __name__ == "__main__":
    main()
