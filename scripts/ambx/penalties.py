"""
Módulo de penalização ambiental sobre a rede viária.

Fornece estruturas e funções para transformar os custos das arestas
do grafo (W_base) em custos condicionados (W_cond) a partir de
camadas ambientais carregadas pelo módulo ``environment``.

A penalização é governada por funções arbitrárias fornecidas pelo
usuário (``penalty_fn``) que mapeiam o valor de uma camada para um
fator multiplicador do custo da aresta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.sample import sample_gen
from rasterio.warp import transform as rio_transform
from shapely.geometry import LineString, Point

from ambx.environment import EnvironmentLayers, RasterLayer, VectorLayer


# ---------------------------------------------------------------------------
# Estruturas de configuração
# ---------------------------------------------------------------------------


@dataclass
class PenaltyRule:
    """Regra de penalização para uma camada ambiental.

    Define **o quê**, **como** e **sobre qual campo** uma camada
    ambiental impacta os custos da rede.

    Attributes
    ----------
    layer_name : str
        Nome da camada em ``EnvironmentLayers`` (ex.: ``"inundacao_2024"``
        para vetorial, ``"temperatura_superficie"`` para raster).
    layer_type : Literal["raster", "vector"]
        Tipo da camada.
    weight_field : str
        Nome do campo de custo nas arestas a ser multiplicado
        pelo fator de penalidade (ex.: ``"travel_time"`` ou ``"length"``).
    penalty_fn : Callable[[Any], float]
        Função que recebe o valor extraído da camada na região da
        aresta e retorna o **fator multiplicador** do custo.
        O valor pode ser ``float`` (para rasters ou colunas numéricas)
        ou ``str`` (para colunas categóricas como ``"Alta"``).
        Deve retornar ``float("inf")`` para interdição total.

        Examples
        --------
        >>> def flood_factor(depth: float) -> float:
        ...     if depth > 50: return float("inf")
        ...     if depth > 20: return 3.0
        ...     if depth > 5:  return 1.5
        ...     return 1.0
        >>> PenaltyRule("inundacao", "vector", penalty_fn=flood_factor)
        PenaltyRule(layer_name='inundacao', layer_type='vector', ...)

    sampling : Literal["midpoint", "segments"], default "midpoint"
        Estratégia de amostragem do raster (ignorado para camadas vetoriais):
        - ``"midpoint"``: ponto médio da aresta (rápido, um ponto por aresta)
        - ``"segments"``: segmenta a aresta em ``n_samples`` pontos
          equidistantes ao longo do trecho
    n_samples : int, default 4
        Número de pontos por aresta quando ``sampling="segments"``.
    aggregation : Literal["max", "mean"], default "max"
        Como combinar os fatores dos pontos/polígonos de uma aresta:
        - ``"max"``: pior caso — aplica o maior fator ao comprimento todo.
        - ``"mean"``: média ponderada pelo comprimento — cada trecho paga seu
          próprio fator (mais justo para arestas longas/heterogêneas). Em
          trechos onde 2+ polígonos se sobrepõem, aplica-se o **maior fator**
          entre eles (semântica ``max`` no trecho sobreposto).
    """

    layer_name: str
    layer_type: Literal["raster", "vector"]
    weight_field: str | None = None
    penalty_fn: Callable[[Any], float] = field(default=lambda v: 1.0)
    sampling: Literal["midpoint", "segments"] = "midpoint"
    n_samples: int = 4
    aggregation: Literal["max", "mean"] = "max"


# ---------------------------------------------------------------------------
# Penalização de camadas vetoriais
# ---------------------------------------------------------------------------


def _sum_line_lengths(geom) -> float:
    """Soma o comprimento das partes do tipo linha de uma geometria.

    A interseção entre uma ``LineString`` e um polígono pode resultar em
    ``LineString``, ``MultiLineString`` ou ``GeometryCollection``. Partes do
    tipo ``Point``/``Polygon`` (casos degenerados) têm comprimento 0 e são
    ignoradas.
    """
    if geom is None or geom.is_empty:
        return 0.0
    gtype = geom.geom_type
    if gtype == "LineString":
        return geom.length
    if gtype == "MultiLineString":
        return sum(g.length for g in geom.geoms)
    if gtype == "GeometryCollection":
        return sum(
            _sum_line_lengths(g)
            for g in geom.geoms
            if g.geom_type in ("LineString", "MultiLineString")
        )
    return 0.0


def _segment_factors(
    edge_geom,
    polygons: gpd.GeoDataFrame,
    value_column: str,
    penalty_fn,
):
    """Particiona uma aresta em trechos cobertos por polígonos.

    A aresta é subdividida nos pontos onde as bordas dos polígonos a cruzam.
    Cada sub-segmento recebe o **maior fator** entre os polígonos que o cobrem
    (semântica ``max`` no trecho sobreposto, sob o ``mean`` por comprimento).

    Retorna ``(segs, interdict)``:
    - ``segs``: lista de ``(comprimento, fator)`` dos trechos **dentro** de
      pelo menos um polígono (trechos fora ficam de fora — fator 1.0 é tratado
      pelo chamador).
    - ``interdict``: ``True`` se algum trecho tem fator ``inf``.
    """
    if polygons is None or polygons.empty:
        return [], False

    # Pontos de corte ao longo da aresta: extremos + interseções com as
    # bordas dos polígonos. Todos em parâmetro normalizado (0..1).
    cut_params = [0.0, 1.0]
    for _, row in polygons.iterrows():
        inter = edge_geom.intersection(row.geometry.boundary)
        for geom in inter.geoms if inter.geom_type == "GeometryCollection" else [inter]:
            if geom.geom_type == "Point":
                cut_params.append(edge_geom.project(geom, normalized=True))
            elif geom.geom_type in ("MultiPoint",):
                cut_params.extend(
                    edge_geom.project(g, normalized=True) for g in geom.geoms
                )
    cut_params = sorted(set(round(p, 12) for p in cut_params))

    segs = []
    interdict = False
    for i in range(len(cut_params) - 1):
        s0, s1 = cut_params[i], cut_params[i + 1]
        if s1 - s0 < 1e-12:
            continue
        mid = (s0 + s1) / 2.0
        mid_pt = edge_geom.interpolate(mid, normalized=True)
        length = (s1 - s0) * edge_geom.length

        fac = None
        for _, row in polygons.iterrows():
            if not row.geometry.covers(mid_pt):
                continue
            val = row[value_column]
            f = penalty_fn(val) if pd.notna(val) else 1.0
            if np.isinf(f):
                interdict = True
            if fac is None or f > fac:
                fac = f
        if fac is None:
            continue  # trecho fora de qualquer polígono → fator 1 (chamador)
        segs.append((length, fac))

    return segs, interdict


def apply_vector_penalty(
    edges_gdf: gpd.GeoDataFrame,
    vector_layer: VectorLayer,
    rule: PenaltyRule,
    aggregation: Literal["max", "mean"] = "max",
) -> gpd.GeoDataFrame:
    """Aplica penalidade vetorial sobre as arestas da rede.

    Para cada aresta, identifica os polígonos da camada vetorial que
    a intersectam via ``gpd.sjoin``.

    - ``aggregation="max"`` (padrão): o **maior fator** (pior caso) entre os
      polígonos intersectantes é aplicado ao campo de custo.
    - ``aggregation="mean"``: o fator da aresta é a **média ponderada pelo
      comprimento** dos trechos de interseção. Quando 2+ polígonos se
      sobrepõem num mesmo trecho, aplica-se o **maior fator** entre eles
      (mesmo critério conservador do ``max`` no trecho sobreposto).

    Arestas sem interseção permanecem com o custo original (fator 1.0).

    Parameters
    ----------
    edges_gdf : gpd.GeoDataFrame
        Arestas da rede com geometria ``LineString`` e o campo de
        custo definido em ``rule.weight_field``.
    vector_layer : VectorLayer
        Camada vetorial com polígonos de penalidade.
        Deve ter ``value_column`` definido.
    rule : PenaltyRule
        Regra de penalização com ``penalty_fn``.
    aggregation : Literal["max", "mean"], default "max"
        Estratégia de agregação dos fatores sobre a aresta.

    Returns
    -------
    gpd.GeoDataFrame
        ``edges_gdf`` com o campo ``rule.weight_field`` atualizado.

    Raises
    ------
    ValueError
        Se ``vector_layer.value_column`` não estiver definido ou
        se ``aggregation`` for inválido.
    """
    if vector_layer.value_column is None:
        raise ValueError(
            f"VectorLayer '{vector_layer.name}' não possui value_column. "
            "Defina value_column ao carregar a camada."
        )
    if aggregation not in ("max", "mean"):
        raise ValueError(f"Agregação inválida: {aggregation}")

    if vector_layer.gdf.crs != edges_gdf.crs:
        vector_layer.gdf.to_crs(edges_gdf.crs, inplace=True)

    val_col = vector_layer.value_column

    if aggregation == "max":
        # Interseção espacial: cada aresta pode se ligar a múltiplos polígonos
        joined = gpd.sjoin(
            edges_gdf,
            vector_layer.gdf[[val_col, "geometry"]],
            how="left",
            predicate="intersects",
        )

        # Fator por aresta: máximo da penalty_fn aplicada aos valores
        # dos polígonos que intersectam. Arestas sem interseção ficam 1.0.
        def _max_factor(group):
            values = group[val_col].dropna()
            if len(values) == 0:
                return 1.0
            return max(rule.penalty_fn(v) for v in values)

        factors = joined.groupby(level=0).apply(_max_factor)
        factors = factors.reindex(edges_gdf.index, fill_value=1.0)
        factor_values = factors.values
    else:
        # Média ponderada pelo comprimento dos trechos de interseção.
        # Um sjoin é usado apenas para descobrir, por aresta, quais polígonos
        # a intersectam; o particionamento real é feito por _segment_factors.
        poly_gdf = vector_layer.gdf[[val_col, "geometry"]].copy()
        poly_gdf = poly_gdf.reset_index(drop=True)
        poly_gdf["_poly_id"] = np.arange(len(poly_gdf), dtype=int)

        joined = gpd.sjoin(
            edges_gdf[["geometry"]],
            poly_gdf,
            how="left",
            predicate="intersects",
        )

        # Agrupa os ids dos polígonos intersectantes por aresta (index do joined
        # é o da aresta; polos sem interseção têm _poly_id == NaN).
        polys_by_edge: dict[int, list[int]] = {}
        for aresta_idx, row in joined.iterrows():
            pid = row["_poly_id"]
            if pd.notna(pid):
                polys_by_edge.setdefault(aresta_idx, []).append(int(pid))

        factor_values = np.ones(len(edges_gdf), dtype=float)
        for i, edge_geom in enumerate(edges_gdf.geometry):
            edge_orig_idx = edges_gdf.index[i]
            poly_idxs = polys_by_edge.get(edge_orig_idx, [])
            if not poly_idxs:
                factor_values[i] = 1.0
                continue
            polys = poly_gdf[poly_gdf["_poly_id"].isin(poly_idxs)]
            segs, interdict = _segment_factors(
                edge_geom, polys, val_col, rule.penalty_fn
            )
            if interdict:
                factor_values[i] = float("inf")
                continue
            if not segs:
                factor_values[i] = 1.0
                continue
            L_total = edge_geom.length
            inside_w = sum(L * f for L, f in segs)
            inside_l = sum(L for L, _ in segs)
            outside = L_total - inside_l
            factor_values[i] = (inside_w + outside * 1.0) / L_total

    result = edges_gdf.copy()
    result[rule.weight_field] = result[rule.weight_field] * factor_values

    return result


# ---------------------------------------------------------------------------
# Penalização de camadas raster
# ---------------------------------------------------------------------------


def apply_raster_penalty(
    edges_gdf: gpd.GeoDataFrame,
    raster_layer: RasterLayer,
    rule: PenaltyRule,
    sampling: Literal["midpoint", "segments"] = "midpoint",
    n_samples: int = 4,
    aggregation: Literal["max", "mean"] = "max",
) -> gpd.GeoDataFrame:
    """Aplica penalidade raster sobre as arestas da rede.

    Para cada aresta, amostra o valor do raster em um ponto
    representativo da aresta (padrão: ponto médio) e aplica
    ``rule.penalty_fn`` para obter o fator multiplicador.

    Arestas cujo ponto de amostragem cai em pixel nodata
    permanecem com custo original (fator 1.0) naquele ponto.

    Parameters
    ----------
    edges_gdf : gpd.GeoDataFrame
        Arestas da rede com geometria ``LineString`` e o campo de
        custo definido em ``rule.weight_field``.
    raster_layer : RasterLayer
        Camada raster carregada (com ``data``, ``transform``, ``crs``).
    rule : PenaltyRule
        Regra de penalização com ``penalty_fn``.
    sampling : Literal["midpoint", "segments"], default "midpoint"
        Estratégia de amostragem:
        - ``"midpoint"``: ponto médio da aresta (rápido, um ponto por aresta)
        - ``"segments"``: segmenta a aresta em ``n_samples`` pontos equidistantes
          (incluindo os extremos)
    n_samples : int, default 4
        Número de pontos por aresta quando ``sampling="segments"``.
    aggregation : Literal["max", "mean"], default "max"
        Como combinar os fatores ao longo da aresta:
        - ``"max"``: pior caso — usa o maior fator entre os pontos.
        - ``"mean"``: média ponderada pelo comprimento (regra do trapézio) —
          cada trecho paga seu próprio fator, mais justo para arestas longas
          que atravessam zonas heterogêneas.

    Returns
    -------
    gpd.GeoDataFrame
        ``edges_gdf`` com o campo ``rule.weight_field`` atualizado.

    Raises
    ------
    ValueError
        Se ``sampling`` ou ``aggregation`` forem inválidos.
    """
    wf = rule.weight_field or "travel_time"

    # --- Determinar pontos de amostragem ---
    # Cada aresta pode contribuir com 1 ou mais pontos (ex.: "segments"
    # amostra n_samples pontos ao longo da aresta). Mantemos uma lista
    # com o mapeamento de cada ponto de volta à sua aresta.
    if sampling == "midpoint":
        point_groups = [
            [geom.interpolate(0.5, normalized=True)]
            for geom in edges_gdf.geometry
        ]
    elif sampling == "segments":
        # Segmenta a aresta em n_samples pontos equidistantes (incluindo
        # os extremos) e agrega o fator pelo MAIOR valor (pior caso).
        n = max(n_samples, 2)  # garante ao menos os dois extremos
        point_groups = [
            [
                geom.interpolate(i / (n - 1), normalized=True)
                for i in range(n)
            ]
            for geom in edges_gdf.geometry
        ]
    else:
        raise ValueError(f"Estratégia de amostragem inválida: {sampling}")

    # Achatamento: lista única de pontos + índices de aresta de origem
    flat_points = []
    point_to_edge = []
    for edge_idx, group in enumerate(point_groups):
        for pt in group:
            flat_points.append(pt)
            point_to_edge.append(edge_idx)

    # --- Reprojetar pontos para o CRS do raster, se necessário ---
    pts_gdf = gpd.GeoDataFrame(geometry=flat_points, crs=edges_gdf.crs)
    if str(pts_gdf.crs) != raster_layer.crs:
        pts_gdf = pts_gdf.to_crs(raster_layer.crs)

    # --- Amostrar ---
    # sample_gen precisa de um dataset rasterio aberto, não do array numpy.
    # Por isso reabrimos o arquivo pelo source_path.
    if raster_layer.source_path is None:
        raise ValueError(
            f"RasterLayer '{raster_layer.name}' não tem source_path. "
            "Carregue o raster de um arquivo ou use apply_raster_penalty "
            "com um RasterLayer que tenha source_path."
        )

    coords = [(pt.x, pt.y) for pt in pts_gdf.geometry]
    with rasterio.open(raster_layer.source_path) as src:
        # Se o raster foi recortado (clip), suas dimensões podem diferir
        # do arquivo original. Precisamos transformar as coordenadas
        # do CRS do raster_layer para o CRS do arquivo original, se
        # diferirem.
        src_crs = src.crs.to_string() if src.crs else raster_layer.crs
        if src_crs != raster_layer.crs:
            # Transforma coordenadas para o CRS do arquivo
            xs, ys = zip(*coords)
            transformed = rio_transform(
                raster_layer.crs, src_crs, xs, ys
            )
            sample_coords = list(zip(transformed[0], transformed[1]))
        else:
            sample_coords = coords

        samples = list(sample_gen(src, sample_coords))
        values = np.array([
            s[0] if s[0] != src.nodata else np.nan
            for s in samples
        ], dtype=float)

    # --- Aplicar penalty_fn ---
    # Cada ponto gera um fator; a forma como os fatores dos pontos de uma
    # mesma aresta são combinados depende de ``aggregation``.
    if aggregation not in ("max", "mean"):
        raise ValueError(f"Agregação inválida: {aggregation}")

    per_point_factors = np.where(
        np.isnan(values),
        1.0,
        [rule.penalty_fn(v) for v in values],
    )

    # Agrupa os fatores de cada aresta (na ordem em que os pontos aparecem).
    edge_factors: dict[int, list[float]] = {}
    for edge_idx, factor in zip(point_to_edge, per_point_factors):
        edge_factors.setdefault(edge_idx, []).append(float(factor))

    factors = np.ones(len(edges_gdf), dtype=float)
    for edge_idx, fs in edge_factors.items():
        if aggregation == "max":
            factors[edge_idx] = max(fs)
        else:
            # Média ponderada pelo comprimento via regra do trapézio.
            # Com n pontos equidistantes (incluindo os extremos), o ponto
            # médio de cada fatia é ponderado e os extremos têm peso 0.5.
            n = len(fs)
            if n == 1:
                factors[edge_idx] = fs[0]
            else:
                total = fs[0] + fs[-1] + 2.0 * sum(fs[1:-1])
                factors[edge_idx] = total / (2.0 * (n - 1))

    result = edges_gdf.copy()
    result[wf] = result[wf] * factors

    return result


# ---------------------------------------------------------------------------
# Orquestrador de múltiplas penalidades
# ---------------------------------------------------------------------------


def compose_penalties(
    edges_gdf: gpd.GeoDataFrame,
    env: EnvironmentLayers,
    rules: list[PenaltyRule],
    weight_field: str = "travel_time",
) -> gpd.GeoDataFrame:
    """Aplica múltiplas regras de penalidade em pipeline sobre as arestas.

    As regras são aplicadas **sequencialmente** de forma **acumulativa**:
    o custo de saída de uma regra vira o custo de entrada da próxima.

    .. math::

        W_{cond} = W_{base} \\times f_1 \\times f_2 \\times \\cdots \\times f_n

    Parameters
    ----------
    edges_gdf : gpd.GeoDataFrame
        Arestas da rede com geometria ``LineString``.
    env : EnvironmentLayers
        Container com todas as camadas ambientais carregadas.
    rules : list[PenaltyRule]
        Lista de regras a aplicar, na ordem desejada.
    weight_field : str, default "travel_time"
        Campo de custo a ser penalizado.

    Returns
    -------
    gpd.GeoDataFrame
        ``edges_gdf`` com ``weight_field`` atualizado acumulativamente.

    Raises
    ------
    ValueError
        Se alguma regra referencia uma camada que não existe em ``env``.
    """
    result = edges_gdf.copy()

    for rule in rules:
        # Usa o weight_field da regra, ou o fallback da função
        wf = rule.weight_field or weight_field

        if rule.layer_type == "vector":
            matching = [v for v in env.vectors if v.name == rule.layer_name]
            if not matching:
                raise ValueError(
                    f"Camada vetorial '{rule.layer_name}' não encontrada "
                    f"em EnvironmentLayers. Disponíveis: "
                    f"{[v.name for v in env.vectors]}"
                )
            layer = matching[0]

            if layer.value_column is None:
                raise ValueError(
                    f"VectorLayer '{layer.name}' não possui value_column. "
                    "Defina value_column ao carregar a camada ou "
                    "antes de chamar compose_penalties."
                )

            # Garante que a regra use o weight_field correto
            rule.weight_field = wf
            result = apply_vector_penalty(
                result,
                layer,
                rule,
                aggregation=rule.aggregation,
            )

        elif rule.layer_type == "raster":
            matching = [r for r in env.rasters if r.name == rule.layer_name]
            if not matching:
                raise ValueError(
                    f"Camada raster '{rule.layer_name}' não encontrada "
                    f"em EnvironmentLayers. Disponíveis: "
                    f"{[r.name for r in env.rasters]}"
                )
            layer = matching[0]

            rule.weight_field = wf
            result = apply_raster_penalty(
                result,
                layer,
                rule,
                sampling=rule.sampling,
                n_samples=rule.n_samples,
                aggregation=rule.aggregation,
            )

        else:
            raise ValueError(f"Tipo de camada desconhecido: {rule.layer_type}")

    return result
