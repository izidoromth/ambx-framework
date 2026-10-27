"""Gera mapas do delta de tempo por cenário."""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import contextily as ctx
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--city", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    city_dir = args.results / args.city
    grid = gpd.read_parquet(city_dir / "prepared/grid.parquet")
    typical = pd.read_parquet(city_dir / "matrices/matrix_typical.parquet")
    typical = typical.groupby("cell_idx")["travel_time"].mean().rename("typical")
    for path in sorted((city_dir).glob("comparison_*.parquet")):
        scenario = path.stem.removeprefix("comparison_")
        comparison = pd.read_parquet(path)
        delta = comparison.groupby("cell_idx")["delta_t"].median().rename("delta_t_mediano")
        data = grid.merge(delta, on="cell_idx", how="left")
        out = args.output / scenario
        (out / "figures").mkdir(parents=True, exist_ok=True)
        (out / "tables").mkdir(parents=True, exist_ok=True)
        data[["cell_idx", "delta_t_mediano"]].to_parquet(out / "tables/tables_delta.parquet", index=False)
        bins = [-np.inf, -2, 0, 2, 5, 10, np.inf]
        labels = ["< -2 min", "-2 a 0 min", "0 a 2 min", "2 a 5 min", "5 a 10 min", "> 10 min"]
        colors = ["#2166ac", "#67a9cf", "#f7f7f7", "#fddbc7", "#ef8a62", "#b2182b"]
        data["classe_delta"] = pd.cut(data["delta_t_mediano"], bins=bins, labels=labels)
        fig, ax = plt.subplots(figsize=(10, 10))
        data = data.to_crs(3857)
        data.plot(column="classe_delta", cmap=ListedColormap(colors), ax=ax, edgecolor="none",
                  alpha=0.72, missing_kwds={"color": "#bdbdbd"}, legend=False)
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldStreetMap, alpha=0.75, zoom="auto")
        except Exception as error:
            print(f"basemap indisponível para {args.city}/{scenario}: {error}")
        ax.legend(handles=[Patch(facecolor=color, edgecolor="#555", label=label)
                           for color, label in zip(colors, labels)]
                  + [Patch(facecolor="#bdbdbd", edgecolor="#555", label="Sem dado")],
                  loc="lower left", frameon=True, title="Delta do tempo de acesso")
        ax.set_title(f"Delta do tempo de acesso — {args.city} — {scenario}")
        ax.set_axis_off()
        fig.savefig(out / "figures/delta_t.png", dpi=180, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()
