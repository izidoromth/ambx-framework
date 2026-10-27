"""Regressões entre eixos do IDS e variação do tempo de acesso por célula."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


AXES = ["eixo_preta_parda", "eixo_renda", "eixo_analfabetismo"]


def _ols(data: pd.DataFrame, predictors: list[str], target: str) -> pd.DataFrame:
    data = data[[target, *predictors]].replace([np.inf, -np.inf], np.nan).dropna()
    model = sm.OLS(data[target], sm.add_constant(data[predictors])).fit()
    result = pd.DataFrame(
        {
            "term": model.params.index,
            "n": int(model.nobs),
            "coef": model.params.values,
            "std_err": model.bse.values,
            "t": model.tvalues.values,
            "p_value": model.pvalues.values,
            "r2": model.rsquared,
            "adj_r2": model.rsquared_adj,
        }
    )
    return result


def _summary_row(
    data: pd.DataFrame, predictors: list[str], target: str, city: str, scenario: str, model_name: str
) -> dict:
    data = data[[target, *predictors]].replace([np.inf, -np.inf], np.nan).dropna()
    model = sm.OLS(data[target], sm.add_constant(data[predictors])).fit()
    row = {
        "city": city,
        "scenario": scenario,
        "model": model_name,
        "n": int(model.nobs),
        "r2": model.rsquared,
        "r2_ajustado": model.rsquared_adj,
        "estatistica_f": model.fvalue,
        "p_value_f": model.f_pvalue,
    }
    for term in ["const", *predictors]:
        prefix = "intercepto" if term == "const" else term
        row[f"{prefix}_coef"] = model.params[term]
        row[f"{prefix}_erro_padrao"] = model.bse[term]
        row[f"{prefix}_t"] = model.tvalues[term]
        row[f"{prefix}_p_value"] = model.pvalues[term]
    return row


def _prepare_city(results_dir: Path, city: str) -> tuple[pd.DataFrame, list[str]]:
    ids = pd.read_parquet(results_dir / city / "prepared" / "ids.parquet")
    comparison_dir = results_dir / city
    comparison_files = sorted(comparison_dir.glob("comparison_*.parquet"))
    rows = []
    for path in comparison_files:
        scenario = path.stem.removeprefix("comparison_")
        comparison = pd.read_parquet(path)
        finite = comparison["delta_t"].replace([np.inf, -np.inf], np.nan)
        grouped = comparison.assign(delta_t_finite=finite).groupby("cell_idx")
        cell = grouped["delta_t_finite"].median().rename("delta_t_mediano").to_frame()
        cell["pares"] = grouped.size()
        cell["pares_inacessiveis"] = comparison.assign(
            inaccessible=~np.isfinite(comparison["delta_t"])
        ).groupby("cell_idx")["inaccessible"].sum()
        cell["fracao_inacessivel"] = cell["pares_inacessiveis"] / cell["pares"]
        cell = cell.reset_index()
        cell["city"] = city
        cell["scenario"] = scenario
        rows.append(cell.merge(ids, on="cell_idx", how="left"))
    return pd.concat(rows, ignore_index=True), [p.stem.removeprefix("comparison_") for p in comparison_files]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--city", action="append", dest="cities")
    args = parser.parse_args()
    cities = args.cities or ["curitiba", "porto_alegre"]
    output_dir = args.results / "analysis" / "regression_ids_delta"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_cells = []
    all_models = []
    summaries = []
    for city in cities:
        cells, scenarios = _prepare_city(args.results, city)
        all_cells.append(cells)
        for scenario in scenarios:
            sample = cells[cells["scenario"] == scenario]
            for axis in AXES:
                result = _ols(sample, [axis], "delta_t_mediano")
                result["city"] = city
                result["scenario"] = scenario
                result["model"] = "bivariada"
                all_models.append(result)
            result = _ols(sample, AXES, "delta_t_mediano")
            result["city"] = city
            result["scenario"] = scenario
            result["model"] = "multipla"
            all_models.append(result)
            summaries.append(_summary_row(sample, AXES, "delta_t_mediano", city, scenario, "multipla"))
            for axis in AXES:
                summaries.append(_summary_row(sample, [axis], "delta_t_mediano", city, scenario, f"bivariada_{axis}"))

    cells = pd.concat(all_cells, ignore_index=True)
    models = pd.concat(all_models, ignore_index=True)
    cells.to_parquet(output_dir / "delta_por_celula.parquet", index=False)
    cells.to_csv(output_dir / "delta_por_celula.csv", index=False)
    models.to_csv(output_dir / "modelos.csv", index=False)
    models.to_parquet(output_dir / "modelos.parquet", index=False)
    summary = pd.DataFrame(summaries)
    summary.to_csv(output_dir / "resumo_regressoes.csv", index=False)
    summary.to_parquet(output_dir / "resumo_regressoes.parquet", index=False)
    print(f"células analisadas: {len(cells)}")
    print(f"modelos gerados: {models[['city', 'scenario', 'model']].drop_duplicates().shape[0]}")
    print(f"saída: {output_dir}")


if __name__ == "__main__":
    main()
