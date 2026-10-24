#!/usr/bin/env python3
"""Calcula índices de desigualdades socioespaciais por célula.

Os índices são calculados primeiro nos setores censitários e só depois
interpolados para a malha. Cada eixo é normalizado por min--max dentro do
município:

    IDS = (renda invertida + taxa de analfabetismo
           + desigualdade racial territorial) / 3

Além dos índices, a saída contém a população interpolada por célula, que pode ser
passada ao ``compute_all_indicators(..., population=...)`` para calcular o F15.

Exemplo:
    .venv/bin/python scripts/analysis/compute_ivs.py \
        --city curitiba \
        --grid results/curitiba/prepared/grid.parquet \
        --output results/curitiba/prepared/ids.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

# Permite executar o arquivo diretamente a partir da raiz do repositório,
# sem exigir que ``scripts`` esteja instalado ou exportado em PYTHONPATH.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ambx.demographics import interpolate_to_grid, load_tracts
from ambx.utils import utm_crs


CITY_CODES = {
    "curitiba": "4106902",
    "porto_alegre": "4314902",
}


def _num(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Soma colunas censitárias, tratando valores ausentes como zero."""
    return frame[columns].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)


def _minmax(series: pd.Series, *, invert: bool = False) -> pd.Series:
    """Normaliza uma variável para [0, 1], com opção de inverter a direção.

    Os limites vêm dos percentis 2 e 98, não dos extremos. Um único setor
    atípico define o máximo e comprime todo o resto da distribuição numa faixa
    estreita de valores, e a interpolação espalha esse extremo por células que
    não têm nada a ver com ele. Saturar nos percentis preserva a resolução onde
    está a massa dos dados; valores fora da faixa ficam em 0 ou 1.

    Esta normalização não resolve distribuições muito assimétricas — nesse
    caso, transforme a variável antes de chamar (ver ``_log_escala``).
    """
    values = pd.to_numeric(series, errors="coerce")
    validos = values.dropna()
    if validos.empty:
        return pd.Series(np.nan, index=series.index)
    low = validos.quantile(0.02)
    high = validos.quantile(0.98)
    if pd.isna(low) or pd.isna(high) or high == low:
        return pd.Series(0.0, index=series.index)
    result = ((values - low) / (high - low)).clip(0.0, 1.0)
    return 1.0 - result if invert else result


def _log_escala(series: pd.Series, escala: float = 1000.0) -> pd.Series:
    """Comprime a cauda alta de uma proporção antes da normalização.

    A taxa de analfabetismo é extremamente assimétrica: metade da população de
    Curitiba vive em setores com menos de 1% de analfabetos, e os bolsões
    chegam a 18%. Normalizada direto, 62% das células caem nos extremos da
    escala e o mapa satura em preto.

    O log abre o miolo e reserva o topo da escala para os bolsões reais. O fator
    de escala (1000) converte a proporção em "por mil", faixa em que o log tem
    resolução útil — sem ele, ``log1p(0,0097) ≈ 0,0097`` e a transformação não
    faz nada.
    """
    values = pd.to_numeric(series, errors="coerce")
    return np.log1p(values * escala)


def compute_sector_ids(tracts: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calcula os eixos e os dois IDS nos setores censitários."""
    required = {
        "V01006", "V01318", "V01320", "V06004", "V00900", "V00901",
    }
    missing = sorted(required.difference(tracts.columns))
    if missing:
        raise ValueError(f"Colunas censitárias ausentes: {', '.join(missing)}")

    population = pd.to_numeric(tracts["V01006"], errors="coerce")
    tracts = tracts.copy()
    tracts["populacao"] = population
    tracts["frac_preta_parda"] = (
        _num(tracts, ["V01318", "V01320"]) / population.replace(0, np.nan)
    )
    tracts["renda"] = np.log1p(pd.to_numeric(tracts["V06004"], errors="coerce"))

    sabe = pd.to_numeric(tracts["V00900"], errors="coerce")
    nao_sabe = pd.to_numeric(tracts["V00901"], errors="coerce").fillna(0.0)
    total_15mais = (sabe + nao_sabe).replace(0, np.nan)
    tracts["taxa_analf"] = (nao_sabe / total_15mais).where(sabe.notna())

    tracts["eixo_preta_parda"] = _minmax(tracts["frac_preta_parda"])
    tracts["eixo_renda"] = _minmax(tracts["renda"], invert=True)
    tracts["eixo_analfabetismo"] = _minmax(_log_escala(tracts["taxa_analf"]))
    axes = ["eixo_preta_parda", "eixo_renda", "eixo_analfabetismo"]
    tracts["ids"] = tracts[axes].mean(axis=1)
    return tracts


def compute_grid_ids(
    tracts: gpd.GeoDataFrame, grid: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """Interpola IDS, eixos e população dos setores para a malha."""
    sector = compute_sector_ids(tracts)
    result = pd.DataFrame(index=pd.Index(grid["cell_idx"], name="cell_idx"))
    columns = ["ids", "eixo_preta_parda", "eixo_renda", "eixo_analfabetismo"]
    for column in columns:
        result[column] = _area_mean_to_grid(sector, grid, column)

    result["populacao"] = interpolate_to_grid(sector["populacao"], sector, grid)
    attributes = result.reset_index()
    return grid[["cell_idx", "geometry"]].merge(
        attributes, on="cell_idx", how="left"
    ).set_crs(grid.crs)


def _area_mean_to_grid(
    tracts: gpd.GeoDataFrame, grid: gpd.GeoDataFrame, column: str
) -> pd.Series:
    """Calcula a média espacial de um atributo setorial em cada célula.

    O denominador é a área dos setores que TÊM valor, não a área total da
    célula. Setores com valor suprimido pelo IBGE entram na interseção mas não
    contribuem para a média; se a área deles fosse somada ao denominador, o
    valor da célula seria diluído pela fração sem dado — uma célula em que só
    0,7% da área tem informação acabaria com média 135 vezes menor que o valor
    real do setor vizinho.
    """
    epsg = utm_crs(grid.union_all())
    tracts_m = tracts[[column, "geometry"]].to_crs(epsg)
    grid_m = grid[["cell_idx", "geometry"]].to_crs(epsg)
    pieces = gpd.overlay(tracts_m, grid_m, how="intersection")
    pieces["area"] = pieces.geometry.area

    com_dado = pieces[pieces[column].notna()].copy()
    com_dado["weighted"] = com_dado[column] * com_dado["area"]
    sums = com_dado.groupby("cell_idx")["weighted"].sum()
    areas = com_dado.groupby("cell_idx")["area"].sum()
    result = sums.div(areas).reindex(grid["cell_idx"])
    result.index = pd.Index(grid["cell_idx"], name="cell_idx")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", choices=sorted(CITY_CODES), required=True)
    parser.add_argument("--census", type=Path, default=Path("data/processed/censo_2022/censo_2022.geoparquet"))
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--format",
        choices=["table", "geoparquet"],
        default="table",
        help="Formato da saída (padrão: tabela sem geometria).",
    )
    args = parser.parse_args()

    tracts = load_tracts(args.census, city_codes=[CITY_CODES[args.city]])
    grid = gpd.read_parquet(args.grid)
    result = compute_grid_ids(tracts, grid)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "geoparquet":
        result.to_parquet(args.output, index=False)
    else:
        result.drop(columns="geometry").to_parquet(args.output, index=False)
    print(f"ok: {args.output} ({len(result)} células; {result['populacao'].sum():.0f} pessoas interpoladas)")


if __name__ == "__main__":
    main()
