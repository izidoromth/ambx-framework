"""Gera mapas da fração de POIs que perderam acessibilidade."""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import contextily as ctx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--city", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    city_dir = args.results / args.city
    grid = gpd.read_parquet(city_dir / "prepared/grid.parquet")
    for path in sorted(city_dir.glob("comparison_*.parquet")):
        scenario = path.stem.removeprefix("comparison_")
        comparison = pd.read_parquet(path)
        loss = (~np.isfinite(comparison["delta_t"])).groupby(comparison["cell_idx"]).mean()
        data = grid.merge(loss.rename("fracao_inacessivel"), on="cell_idx", how="left")
        out = args.output / scenario
        (out / "figures").mkdir(parents=True, exist_ok=True)
        (out / "tables").mkdir(parents=True, exist_ok=True)
        data[["cell_idx", "fracao_inacessivel"]].to_parquet(out / "tables/tables_perda_acesso.parquet", index=False)
        fig, ax = plt.subplots(figsize=(10, 10))
        data = data.to_crs(3857)
        data.plot(column="fracao_inacessivel", cmap="Reds", vmin=0, vmax=1, ax=ax,
                  edgecolor="none", alpha=0.72, missing_kwds={"color": "#bdbdbd"}, legend=True)
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldStreetMap, alpha=0.75, zoom="auto")
        except Exception as error:
            print(f"basemap indisponível para {args.city}/{scenario}: {error}")
        ax.set_title(f"Perda de acesso a POIs — {args.city} — {scenario}")
        ax.set_axis_off()
        fig.savefig(out / "figures/access_loss.png", dpi=180, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()
