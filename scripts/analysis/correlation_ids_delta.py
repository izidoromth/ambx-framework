"""Correlações de Spearman entre eixos do IDS e delta de acesso."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


AXES = ["eixo_preta_parda", "eixo_renda", "eixo_analfabetismo"]
TARGET = "delta_t_mediano"


def prepare(results: Path, city: str) -> pd.DataFrame:
    ids = pd.read_parquet(results / city / "prepared" / "ids.parquet")
    rows = []
    for path in sorted((results / city).glob("comparison_*.parquet")):
        scenario = path.stem.removeprefix("comparison_")
        comparison = pd.read_parquet(path)
        finite = comparison["delta_t"].replace([np.inf, -np.inf], np.nan)
        delta = finite.groupby(comparison["cell_idx"]).median().rename(TARGET)
        rows.append(ids.merge(delta, left_on="cell_idx", right_index=True).assign(city=city, scenario=scenario))
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--city", action="append", dest="cities")
    args = parser.parse_args()
    cities = args.cities or ["curitiba", "porto_alegre"]
    output = args.results / "analysis" / "correlation_ids_delta"
    figures = output / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    long = []
    for city in cities:
        data = prepare(args.results, city)
        for scenario, sample in data.groupby("scenario"):
            for axis in AXES:
                valid = sample[[axis, TARGET]].replace([np.inf, -np.inf], np.nan).dropna()
                rho, p_value = spearmanr(valid[axis], valid[TARGET])
                long.append({"city": city, "scenario": scenario, "variable": axis,
                             "target": TARGET, "n": len(valid), "rho": rho, "p_value": p_value})
            variables = AXES + [TARGET]
            corr = sample[variables].replace([np.inf, -np.inf], np.nan).corr(method="spearman")
            fig, ax = plt.subplots(figsize=(8, 6))
            image = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
            ax.set_xticks(range(len(variables)), variables, rotation=35, ha="right")
            ax.set_yticks(range(len(variables)), variables)
            for i in range(len(variables)):
                for j in range(len(variables)):
                    ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=11)
            ax.set_title(f"Correlação de Spearman — {city} — {scenario}")
            fig.colorbar(image, ax=ax, label="ρ de Spearman")
            fig.tight_layout()
            fig.savefig(figures / f"{city}_{scenario}.png", dpi=180, bbox_inches="tight")
            plt.close(fig)

    table = pd.DataFrame(long)
    table.to_csv(output / "correlacoes_spearman.csv", index=False)
    table.to_parquet(output / "correlacoes_spearman.parquet", index=False)
    print(f"correlações geradas: {len(table)}")
    print(f"saída: {output}")


if __name__ == "__main__":
    main()
