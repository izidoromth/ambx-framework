"""
demographics — Interpolação areal de dados censitários para a malha de análise

Carrega um GeoParquet de setores censitários (qualquer fonte) e
compatibiliza os dados com a malha regular (hexagonal/quadrada) do
módulo ``ambx.grid`` via interpolação areal.

O GeoParquet de entrada deve conter:
- Geometria dos setores censitários (polígonos)
- Uma coluna de identificação do setor
- Demais colunas com variáveis censitárias (população, renda, etc.)

Uso típico
----------
    from ambx.demographics import load_tracts, interpolate_to_grid

    tracts = load_tracts("data/raw/censo_2022/censo_2022.gpkg",
                         city_codes=["4106902"])

    grid["populacao"] = interpolate_to_grid(
        values=tracts["V01006"],
        tracts_gdf=tracts,
        grid_gdf=grid,
    )
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import area as shapely_area


def load_tracts(
    path: str | Path,
    columns: list[str] | None = None,
    city_codes: list[str] | None = None,
    tract_id_col: str = "CD_SETOR",
) -> gpd.GeoDataFrame:
    """
    Carrega um GeoParquet de setores censitários e opcionalmente filtra
    por município(s).

    Parameters
    ----------
    path : str | Path
        Caminho para o arquivo ``.gpkg`` (GeoParquet).
    columns : list[str] | None
        Colunas a carregar (além da geometria). ``None`` carrega todas.
    city_codes : list[str] | None
        Códigos do(s) município(s) para filtrar (ex.: ``["4106902"]``).
        Filtra pelos primeiros 7 dígitos do ``tract_id_col``.
    tract_id_col : str
        Nome da coluna de identificação do setor.

    Returns
    -------
    gpd.GeoDataFrame
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    gdf = gpd.read_parquet(path)
    gdf = gdf.set_index(tract_id_col)

    if columns:
        keep = [c for c in columns if c in gdf.columns] + ["geometry"]
        gdf = gdf[keep]

    if city_codes:
        gdf = gdf[gdf.index.str[:7].isin(city_codes)].copy()

    return gdf


def filter_by_area(
    tracts_gdf: gpd.GeoDataFrame,
    area_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Filtra setores que intersectam uma área de interesse.

    Parameters
    ----------
    tracts_gdf : gpd.GeoDataFrame
        Setores censitários com geometria.
    area_gdf : gpd.GeoDataFrame
        Área de interesse (ex.: malha do grid).

    Returns
    -------
    gpd.GeoDataFrame
    """
    if tracts_gdf.crs != area_gdf.crs:
        tracts_gdf = tracts_gdf.to_crs(area_gdf.crs)

    union = area_gdf.union_all()
    return tracts_gdf[tracts_gdf.intersects(union)].copy()


def interpolate_to_grid(
    values: pd.Series,
    tracts_gdf: gpd.GeoDataFrame,
    grid_gdf: gpd.GeoDataFrame,
    method: str = "area_weighted",
) -> pd.Series:
    """
    Interpola dados censitários de setores (polígonos irregulares) para
    células da malha de análise (hexágonos/quadrados regulares).

    Usa ``gpd.overlay`` para computar as interseções setor–célula.

    Parameters
    ----------
    values : pd.Series
        Valores por setor, indexada pelo código do setor (índice único).
    tracts_gdf : gpd.GeoDataFrame
        Setores com geometria e mesmo índice de ``values``.
    grid_gdf : gpd.GeoDataFrame
        Malha (colunas ``cell_idx`` e ``geometry``).
    method : str
        ``"area_weighted"`` (default) ou ``"density_weighted"``.

    Returns
    -------
    pd.Series
        Indexada por ``cell_idx``.
    """
    from ambx.utils import utm_crs

    # ── 1. CRS métrico ────────────────────────────────────────────
    if tracts_gdf.crs is None or not tracts_gdf.crs.is_projected:
        epsg = utm_crs(grid_gdf.union_all())
        tracts = tracts_gdf.to_crs(crs=epsg)
        cells  = grid_gdf.to_crs(crs=epsg)
    else:
        tracts = tracts_gdf
        cells  = grid_gdf

    # ── 2. Normalizar ─────────────────────────────────────────────
    values = pd.to_numeric(values, errors="coerce")
    cell_col = "cell_idx" if "cell_idx" in cells.columns else cells.columns[0]

    # ── 3. Extrair arrays ─────────────────────────────────────────
    t_ids   = tracts.index.astype(str).tolist()
    t_geoms = tracts.geometry.values
    t_areas = np.array([g.area for g in t_geoms])
    t_vals  = values.astype(float).to_numpy()

    # ── 4. Encontrar pares via spatial index (evita bugs do sjoin) ─
    cell_idx = cells.sindex
    c_geoms = cells.geometry.values
    c_ids   = cells[cell_col].tolist()

    # Collect (i_tract, i_cell) pairs
    pair_indices: list[tuple[int, int]] = []
    for i, geom_t in enumerate(t_geoms):
        hits = cell_idx.query(geom_t, predicate="intersects")
        for j in hits:
            pair_indices.append((i, j))

    if not pair_indices:
        raise ValueError("Nenhuma interseção entre setores e malha.")

    # ── 5. Loop por par único — interseção geométrica ─────────────
    contrib: dict[int, float] = {}
    seen: set = set()
    for i, j in pair_indices:
        key = (i, j)
        if key in seen:
            continue
        seen.add(key)
        val, area_t, geom_t = t_vals[i], t_areas[i], t_geoms[i]
        geom_c = c_geoms[j]
        inter = geom_t.intersection(geom_c)
        if inter.is_empty:
            continue
        cid = c_ids[j]
        c = val * inter.area / area_t if method == "area_weighted" else (val / area_t) * inter.area
        contrib[cid] = contrib.get(cid, 0.0) + c

    result = pd.Series(contrib, name=values.name or "interpolated")
    result.index.name = cell_col
    return result
