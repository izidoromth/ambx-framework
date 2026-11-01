"""Consolida PTh, F15 e Gini de todos os cenários em uma tabela única.

Até aqui esses indicadores só existiam como texto no terminal: cada script
recalculava a mediana por célula do zero e ninguém gravava o agregado. Este
script lê as matrizes OD de cada cenário, calcula os indicadores e grava um
arquivo por cidade com uma linha por (cenário, categoria).

Saídas, em ``results/<city>/analysis/indicators/``:

    indicators.csv      uma linha por combinação de cenário e categoria
    indicators.json     os mesmos valores, em estrutura aninhada
    pth_by_cell.parquet PTh por célula e categoria, para auditoria

Uso:
    python scripts/analysis/summarize_indicators.py
    python scripts/analysis/summarize_indicators.py --city curitiba --k 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ambx.indicators import compute_all_indicators  # noqa: E402

# Nome do arquivo de matriz → nome do cenário no texto da dissertação.
SCENARIOS = {
    "matrix_typical": "typical",
    "matrix_lst": "thermal",
    "matrix_lst_green_composite": "thermal_vegetation",
    # k = 0,05, cerca de 7x a calibração: existe para mostrar a resposta da lib
    # a um gradiente severo. Não é resultado.
    "matrix_lst_demo_k05": "thermal_demo_k05",
    "matrix_lst_green_composite_demo_k05": "thermal_vegetation_demo_k05",
    "matrix_inundacao": "flood",
    "matrix_movimento_massa": "landsliding",
    "matrix_combinado": "flood_landsliding",
}


def load_population(results: Path, city: str) -> pd.Series | None:
    """População por célula, para ponderar F15 e Gini."""
    path = results / city / "prepared" / "ids.parquet"
    if not path.exists():
        return None
    ids = pd.read_parquet(path)
    if "populacao" not in ids.columns:
        return None
    return ids.set_index("cell_idx")["populacao"]


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Mediana ponderada: valor onde a massa acumulada cruza 50%."""
    order = np.argsort(values)
    values, weights = values[order], weights[order]
    cumulative = np.cumsum(weights)
    if cumulative[-1] <= 0:
        return float("nan")
    return float(values[np.searchsorted(cumulative, 0.5 * cumulative[-1])])


def summarize_city(results: Path, city: str, k: int | None, threshold: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    population = load_population(results, city)
    if population is None:
        print(f"  aviso: sem populacao para {city}, F15 e Gini ficam sem peso")

    rows, pth_frames = [], []
    for filename, scenario in SCENARIOS.items():
        path = results / city / "matrices" / f"{filename}.parquet"
        if not path.exists():
            continue
        matrix = pd.read_parquet(path)
        result = compute_all_indicators(
            matrix, k=k, population=population, threshold=threshold,
        )

        pth_wide = result["pth_wide_typ"]
        pth_wide = pth_wide.set_index("cell_idx") if "cell_idx" in pth_wide.columns else pth_wide
        pth_frames.append(pth_wide.assign(city=city, scenario=scenario))

        # `pth_wide` só tem as células com algum POI alcançável. O denominador
        # das frações é a malha do cenário, não as células que sobraram.
        n_cells = int(matrix["cell_idx"].nunique())

        for category in pth_wide.columns:
            values = pth_wide[category].dropna()
            weights = population.reindex(values.index).fillna(0) if population is not None else None
            if weights is not None and weights.sum() > 0:
                pth_mean = float(np.average(values, weights=weights))
                pth_median = weighted_median(values.to_numpy(float), weights.to_numpy(float))
            else:
                pth_mean = float(values.mean())
                pth_median = float(values.median())

            rows.append({
                "city": city,
                "scenario": scenario,
                "category": category,
                "n_cells": n_cells,
                "n_reachable": int(len(values)),
                "n_unreachable": int(n_cells - len(values)),
                "pct_unreachable": round(100.0 * (n_cells - len(values)) / n_cells, 2),
                "pth_mean_pop_weighted": round(pth_mean, 3),
                "pth_median_pop_weighted": round(pth_median, 3),
                "pth_mean_cell": round(float(values.mean()), 3),
                "pth_p90_cell": round(float(values.quantile(0.90)), 3),
                "f15_pop_weighted": round(float(result["f15_typ"][category]), 6)
                if result["f15_typ"].get(category) is not None else None,
                "gini_pop_weighted": round(float(result["gini_typ"][category]), 6),
                "k": k if k is not None else "all",
                "threshold_min": threshold,
            })

        # PTh geral: média simples das categorias. Cada categoria entra com o
        # mesmo peso, porque a pergunta é "quanto tempo, em média, até os
        # serviços" e não "quanto tempo ponderado pelo número de POIs".
        scenario_rows = [r for r in rows
                         if r["city"] == city and r["scenario"] == scenario]
        # Uma célula só conta como inacessível no geral se não alcança
        # nenhuma categoria: perder um serviço não é perder acesso.
        reachable_any = pth_wide.dropna(how="all").shape[0]
        overall = {
            "city": city,
            "scenario": scenario,
            "category": "overall",
            "n_cells": n_cells,
            "n_reachable": int(reachable_any),
            "n_unreachable": int(n_cells - reachable_any),
            "pct_unreachable": round(100.0 * (n_cells - reachable_any) / n_cells, 2),
            "k": k if k is not None else "all",
            "threshold_min": threshold,
        }
        for column in ("pth_mean_pop_weighted", "pth_median_pop_weighted",
                       "pth_mean_cell", "pth_p90_cell", "f15_pop_weighted",
                       "gini_pop_weighted"):
            values = [r[column] for r in scenario_rows if r.get(column) is not None]
            overall[column] = round(float(np.mean(values)), 6) if values else None
        rows.append(overall)

    return pd.DataFrame(rows), pd.concat(pth_frames, ignore_index=True) if pth_frames else pd.DataFrame()


def summarize_deltas(results: Path, city: str) -> pd.DataFrame:
    """Variação do tempo de acesso entre o cenário típico e cada condicionado.

    Os indicadores descrevem o nível de acesso; esta tabela descreve quanto ele
    mudou. Cada cenário é comparado ao típico sobre as células que alcançam
    algum destino nos dois, para que os valores não misturem universos
    diferentes.
    """
    typical_path = results / city / "matrices" / "matrix_typical.parquet"
    if not typical_path.exists():
        return pd.DataFrame()

    typical = pd.read_parquet(typical_path)
    typical_cells = set(typical["cell_idx"].unique())

    rows = []
    for path in sorted((results / city).glob("comparison_*.parquet")):
        scenario = SCENARIOS.get(f"matrix_{path.stem.removeprefix('comparison_')}",
                                 path.stem.removeprefix("comparison_"))
        comparison = pd.read_parquet(path)

        delta = comparison["delta_t"].replace([np.inf, -np.inf], np.nan)
        per_cell = delta.groupby(comparison["cell_idx"]).median()

        # Pares perdidos: tempo infinito antes do descarte.
        n_pairs = len(comparison)
        n_lost = int((~np.isfinite(comparison["delta_t"])).sum())

        # Células que perdem todos os destinos não entram nas estatísticas de
        # tempo: ausência de acesso não é tempo alto.
        lost_all = ((~np.isfinite(comparison["delta_t"]))
                    .groupby(comparison["cell_idx"]).mean().eq(1))
        lost_cells = set(lost_all[lost_all].index)

        kept = per_cell.dropna()
        # Células comparáveis: têm valor no cenário e não perderam acesso.
        common = set(kept.index) & (typical_cells - lost_cells)

        rows.append({
            "city": city,
            "scenario": scenario,
            "n_cells": int(comparison["cell_idx"].nunique()),
            "n_cells_with_delta": int(len(kept)),
            "n_cells_lost_access": int(len(lost_cells)),
            "pct_cells_lost_access": round(100.0 * len(lost_cells) / comparison["cell_idx"].nunique(), 2),
            "n_pairs": n_pairs,
            "n_pairs_lost": n_lost,
            "pct_pairs_lost": round(100.0 * n_lost / n_pairs, 2) if n_pairs else 0.0,
            "n_cells_common_with_typical": int(len(common)),
            "delta_mean": round(float(kept.mean()), 3),
            "delta_median": round(float(kept.median()), 3),
            "delta_p90": round(float(kept.quantile(0.90)), 3),
            "delta_max": round(float(kept.max()), 3),
            "n_cells_zero_delta": int((kept == 0).sum()),
            "pct_cells_zero_delta": round(100.0 * (kept == 0).mean(), 2),
            # Estatísticas restritas às células comparáveis com o típico.
            "delta_mean_common": round(float(kept.loc[list(common)].mean()), 3) if common else None,
            "delta_median_common": round(float(kept.loc[list(common)].median()), 3) if common else None,
            "delta_p90_common": round(float(kept.loc[list(common)].quantile(0.90)), 3) if common else None,
        })

    table = pd.DataFrame(rows)
    if table.empty:
        return table

    # As estatísticas acima usam, cada uma, o conjunto de células do próprio
    # cenário. Para comparar dois cenários é preciso restringir ambos ao
    # conjunto que sobrevive nos dois, senão as medianas descrevem universos
    # diferentes. A coluna abaixo guarda, para cada cenário, a estatística
    # calculada sobre a interseção com o cenário de menor cobertura.
    per_cell_by_scenario = {}
    for path in sorted((results / city).glob("comparison_*.parquet")):
        scenario = SCENARIOS.get(f"matrix_{path.stem.removeprefix('comparison_')}",
                                 path.stem.removeprefix("comparison_"))
        comparison = pd.read_parquet(path)
        delta = comparison["delta_t"].replace([np.inf, -np.inf], np.nan)
        per_cell_by_scenario[scenario] = delta.groupby(comparison["cell_idx"]).median().dropna()

    if per_cell_by_scenario:
        smallest = min(per_cell_by_scenario, key=lambda s: len(per_cell_by_scenario[s]))
        shared = set.intersection(*(set(v.index) for v in per_cell_by_scenario.values()))
        for row in rows:
            values = per_cell_by_scenario.get(row["scenario"])
            if values is None or not shared:
                continue
            subset = values.loc[list(shared)]
            row["comparison_basis"] = smallest
            row["n_cells_shared"] = len(shared)
            row["delta_mean_shared"] = round(float(subset.mean()), 3)
            row["delta_median_shared"] = round(float(subset.median()), 3)
            row["delta_p90_shared"] = round(float(subset.quantile(0.90)), 3)

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--city", action="append", dest="cities")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=15.0)
    args = parser.parse_args()
    cities = args.cities or ["curitiba", "porto_alegre"]

    for city in cities:
        table, pth = summarize_city(args.results, city, args.k, args.threshold)
        if table.empty:
            print(f"{city}: nenhuma matriz encontrada")
            continue
        output = args.output or args.results / city / "analysis" / "indicators"
        output.mkdir(parents=True, exist_ok=True)
        table.to_csv(output / "indicators.csv", index=False)
        table.to_parquet(output / "indicators.parquet", index=False)
        pth.to_parquet(output / "pth_by_cell.parquet")
        with open(output / "indicators.json", "w") as handle:
            json.dump(
                [
                    {k: (str(v) if not isinstance(v, (int, float, str, bool, type(None))) else v)
                     for k, v in row.items()}
                    for row in table.to_dict(orient="records")
                ],
                handle, indent=2,
            )
        print(f"{city}: {len(table)} linhas -> {output / 'indicators.csv'}")

        deltas = summarize_deltas(args.results, city)
        if not deltas.empty:
            deltas.to_csv(output / "deltas.csv", index=False)
            deltas.to_parquet(output / "deltas.parquet", index=False)
            print(f"{city}: {len(deltas)} linhas -> {output / 'deltas.csv'}")


if __name__ == "__main__":
    main()
