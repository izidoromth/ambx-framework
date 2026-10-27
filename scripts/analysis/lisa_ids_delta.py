"""Moran global e LISA bivariado entre IDS e delta de acesso."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import contextily as ctx
from esda.moran import Moran_BV, Moran_Local_BV
from libpysal.weights import Queen
from matplotlib.patches import Patch


AXES = ["ids"]


def prepare(results: Path, city: str) -> pd.DataFrame:
    ids = pd.read_parquet(results / city / "prepared" / "ids.parquet")
    grid = gpd.read_parquet(results / city / "prepared" / "grid.parquet")
    rows = []
    for path in sorted((results / city).glob("comparison_*.parquet")):
        scenario = path.stem.removeprefix("comparison_")
        comparison = pd.read_parquet(path)
        delta = comparison["delta_t"].replace([np.inf, -np.inf], np.nan)
        delta = delta.groupby(comparison["cell_idx"]).median().rename("delta_t_mediano")
        rows.append(ids.merge(delta, left_on="cell_idx", right_index=True).assign(scenario=scenario))
    values = pd.concat(rows, ignore_index=True)
    return grid.merge(values, on="cell_idx", how="inner")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--city", action="append", dest="cities")
    parser.add_argument("--permutations", type=int, default=999)
    args = parser.parse_args()
    cities = args.cities or ["curitiba", "porto_alegre"]
    output = args.results / "analysis" / "lisa_ids_delta"
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    globals_rows, locals_rows = [], []

    for city in cities:
        data = prepare(args.results, city)
        for scenario, scenario_data in data.groupby("scenario"):
            for axis in AXES:
                sample = scenario_data[["cell_idx", axis, "delta_t_mediano", "geometry"]].dropna().copy()
                weights = Queen.from_dataframe(sample, use_index=True)
                weights.transform = "r"
                x = sample[axis].to_numpy(float)
                y = sample["delta_t_mediano"].to_numpy(float)
                global_moran = Moran_BV(x, y, weights, permutations=args.permutations)
                local = Moran_Local_BV(x, y, weights, permutations=args.permutations)
                globals_rows.append({"city": city, "scenario": scenario, "axis": axis,
                                     "n": len(sample), "moran_bv": global_moran.I,
                                     "p_value": global_moran.p_sim})
                clusters = np.where(local.p_sim <= 0.05, local.q, 0)
                labels = {0: "Não significativo", 1: "Alto-Alto", 2: "Baixo-Alto", 3: "Baixo-Baixo", 4: "Alto-Baixo"}
                cluster_labels = pd.Series(clusters, index=sample.index).map(labels)
                for cell_idx, cluster, p_value in zip(sample["cell_idx"], cluster_labels, local.p_sim):
                    locals_rows.append({"city": city, "scenario": scenario, "axis": axis,
                                        "cell_idx": cell_idx, "cluster": cluster, "p_value": p_value})
                plot = sample.copy()
                plot["cluster"] = cluster_labels.to_numpy()
                colors = {"Não significativo": "#d9d9d9", "Alto-Alto": "#b2182b",
                          "Baixo-Alto": "#ef8a62", "Baixo-Baixo": "#2166ac",
                          "Alto-Baixo": "#67a9cf"}
                fig, ax = plt.subplots(figsize=(10, 10))
                plot = plot.to_crs(3857)
                plot.plot(color=plot["cluster"].map(colors), ax=ax, edgecolor="none", alpha=0.72)
                try:
                    ctx.add_basemap(ax, source=ctx.providers.Esri.WorldStreetMap, alpha=0.75, zoom="auto")
                except Exception as error:
                    print(f"basemap indisponível para {city}/{scenario}/{axis}: {error}")
                plt.title(f"LISA bivariado — {city} — {scenario} — {axis}")
                ax.legend(handles=[Patch(facecolor=color, label=label) for label, color in colors.items()],
                          loc="lower left", frameon=True)
                plt.axis("off")
                plt.savefig(figures / f"{city}_{scenario}_{axis}.png", dpi=180, bbox_inches="tight")
                plt.close()

    pd.DataFrame(globals_rows).to_csv(output / "moran_global.csv", index=False)
    pd.DataFrame(globals_rows).to_parquet(output / "moran_global.parquet", index=False)
    pd.DataFrame(locals_rows).to_csv(output / "lisa_local.csv", index=False)
    pd.DataFrame(locals_rows).to_parquet(output / "lisa_local.parquet", index=False)
    print(f"Moran global: {len(globals_rows)}")
    print(f"células LISA: {len(locals_rows)}")
    print(f"saída: {output}")


if __name__ == "__main__":
    main()
