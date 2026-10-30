"""Stages used by the first Snakemake workflow version."""
from __future__ import annotations

import argparse
import importlib
import json
import math
import pickle
import sys
from pathlib import Path

import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def _clean(obj):
    """Replace non-finite floats by None so the output is valid JSON."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj
sys.path.insert(0, str(ROOT))

from ambx.environment import build_environment
from ambx.grid import GridFormat, generate_grid
from ambx.indicators import compute_all_indicators
from ambx.network import (
    add_travel_time,
    get_graph_edges,
    get_network,
    project_network,
    snap_grid_to_network,
)
from ambx.penalties import PenaltyRule, compose_penalties
from ambx.pois import get_pois
from ambx.routing import routing_matrix, snap_pois_to_network


def cfg(path):
    with open(path) as f:
        return yaml.safe_load(f)


def resolve_penalty_function(name):
    """Resolve uma função declarada no YAML."""
    module_name = f"workflow.rules.{name}"
    module = importlib.import_module(module_name)
    try:
        return getattr(module, name)
    except AttributeError as exc:
        raise ValueError(f"Função de penalização '{name}' não encontrada em {module_name}") from exc


def prepare(a):
    c = cfg(a.config)
    grid = generate_grid(c["location"], GridFormat(c["grid_format"]), c["cell_size"])
    pois = get_pois(c["location"], buffer=c["poi_buffer"])
    graph = add_travel_time(project_network(get_network(c["location"], c["network_type"])), c["walk_speed_kph"])
    snapped = snap_grid_to_network(grid, graph, max_distance=c["max_snap_distance"], projected=False)
    pois_snapped = snap_pois_to_network(pois, graph)
    Path(a.grid).parent.mkdir(parents=True, exist_ok=True)
    grid.to_parquet(a.grid); pois.to_parquet(a.pois); snapped.to_parquet(a.snapped)
    pois_snapped.to_parquet(a.pois_snapped)
    edges = get_graph_edges(graph)
    edges = edges[["length", "travel_time", "geometry"]]
    edges.to_parquet(a.edges)
    with open(a.graph, "wb") as f: pickle.dump(graph, f)


def _scan_layer_specs(rules_cfg):
    """Achata as camadas declaradas pelas regras (simples e compostas).

    Regra simples: declara ``input``/``input_type``/``value_field`` direto.
    Regra composta: declara ``layers`` (nomes) + ``inputs`` (spec por camada).
    """
    specs = []
    for r in rules_cfg:
        if r.get("input_type") == "composite":
            specs.extend(r.get("inputs", {}).values())
        else:
            specs.append(r)
    return specs


def _composite_names(rules_cfg):
    """Mapeia ``caminho -> nome semântico`` para as camadas de regras compostas.

    Nas regras simples, o ``name`` do YAML é apenas o rótulo da penalização e a
    camada é identificada por ``layer``; renomeá-la ali quebraria a busca em
    ``compose_penalties``. Só as regras compostas nomeiam camadas.

    O caminho é resolvido para absoluto, pois ``source_path`` das camadas
    carregadas também é absoluto (o YAML costuma usar caminho relativo).
    """
    nomes = {}
    for r in rules_cfg:
        if r.get("input_type") != "composite":
            continue
        for spec in r.get("inputs", {}).values():
            if "name" in spec:
                nomes[str(Path(spec["input"]).resolve())] = spec["name"]
    return nomes


def _rename_layers(env, nomes):
    """Renomeia as camadas do ``env`` conforme o mapeamento ``caminho -> nome``.

    Usa apenas a API pública de ``EnvironmentLayers``: ``name`` e
    ``source_path`` de cada camada. O nome é usado como chave do dicionário
    entregue à ``penalty_fn`` das regras compostas.
    """
    for layer in [*env.rasters, *env.vectors]:
        nome = nomes.get(str(Path(layer.source_path).resolve()))
        if nome:
            layer.name = nome
    return env


def _build_rule(r):
    """Monta uma ``PenaltyRule`` a partir da configuração YAML.

    Suporta dois formatos:

    - **simples** (raster/vector): declara um único nome de camada em
      ``layers``;
    - **composta** (``input_type: composite``): declara ``layers`` (nomes
      semânticos) e ``inputs`` (spec de cada camada, com ``name``).
    """
    fn = resolve_penalty_function(r["function"])
    tipo = r.get("input_type", "raster")
    if tipo == "composite":
        layers = r["layers"]
        nomes = {s.get("name") for s in r.get("inputs", {}).values()}
        faltando = [nome for nome in layers if nome not in nomes]
        if faltando:
            raise ValueError(
                f"As camadas {faltando} não têm 'name' declarado em 'inputs'. "
                "O nome precisa casar com as chaves que a penalty_fn espera."
            )
        return PenaltyRule(
            layers=layers,
            layer_type="composite",
            weight_field=r.get("weight_field", "travel_time"),
            penalty_fn=fn,
            sampling=r.get("sampling", "midpoint"),
            n_samples=r.get("n_samples", 4),
            aggregation=r.get("aggregation", "max"),
        )
    return PenaltyRule(
        [r.get("layer", Path(r["input"]).stem)],
        tipo,
        r.get("weight_field", "travel_time"),
        fn,
        r.get("sampling", "midpoint"),
        r.get("n_samples", 4),
        r.get("aggregation", "max"),
    )


def route(a):
    c = cfg(a.config)
    with open(a.graph, "rb") as f: graph = pickle.load(f)
    snapped = gpd.read_parquet(a.snapped); pois = gpd.read_parquet(a.pois)
    if a.scenario != "typical":
        if not getattr(a, "grid", None):
            raise ValueError("O cenário condicionado exige --grid")
        edges = gpd.read_parquet(a.edges)
        grid = gpd.read_parquet(a.grid)
        scenario_cfg = c.get("scenarios", {}).get(a.scenario, {})
        rules_cfg = scenario_cfg.get("penalties", [])
        if not rules_cfg:
            raise ValueError(f"O cenário '{a.scenario}' precisa declarar penalizações")
        specs = _scan_layer_specs(rules_cfg)
        raster_paths = [s["input"] for s in specs if s.get("input_type", "raster") == "raster"]
        vector_paths = [s["input"] for s in specs if s.get("input_type") == "vector"]
        vector_value_columns = {
            s["input"]: s["value_field"]
            for s in specs
            if s.get("input_type") == "vector" and s.get("value_field")
        }
        env = build_environment(
            grid,
            raster_paths=raster_paths,
            vector_paths=vector_paths,
            vector_value_columns=vector_value_columns,
        )
        _rename_layers(env, _composite_names(rules_cfg))
        rules = [_build_rule(r) for r in rules_cfg]
        penalized = compose_penalties(edges, env, rules=rules, weight_field="travel_time")
        graph = graph.copy()
        for key, value in penalized["travel_time"].items():
            if key in graph.edges: graph.edges[key]["travel_time"] = value
    result = routing_matrix(snapped, pois, graph, k_nearest=c["k_nearest"], speed_kph=c["walk_speed_kph"], n_jobs=c["n_jobs"])
    Path(a.output).parent.mkdir(parents=True, exist_ok=True); result.to_parquet(a.output)


def comparison(a):
    typ = pd.read_parquet(a.typical); cond = pd.read_parquet(a.conditioned)
    key = ["cell_idx", "poi_idx", "poi_category"]
    out = typ.merge(cond, on=key, suffixes=("_typ", "_cond"))
    out["delta_t"] = out.travel_time_cond - out.travel_time_typ
    out["delta_pct"] = out.delta_t / out.travel_time_typ.replace(0, pd.NA) * 100
    Path(a.output).parent.mkdir(parents=True, exist_ok=True); out.to_parquet(a.output)


def indicators(a):
    c = cfg(a.config)
    conditioned = pd.read_parquet(a.conditioned) if getattr(a, "conditioned", None) else None
    population = pd.read_parquet(a.population).set_index("cell_idx")["populacao"]
    result = compute_all_indicators(
        pd.read_parquet(a.typical), conditioned,
        k=c["k_nearest"], population=population,
    )
    serial = {k: (v.to_dict() if isinstance(v, pd.DataFrame) else v) for k, v in result.items()}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True); Path(a.output).write_text(json.dumps(_clean(serial), default=str, allow_nan=False))


def figures(a):
    comparison = pd.read_parquet(a.comparison)
    grid = gpd.read_parquet(a.grid)
    stats = comparison.groupby("cell_idx").agg(
        avg_time_typ=("travel_time_typ", "mean"),
        avg_time_cond=("travel_time_cond", "mean"),
        delta_avg=("delta_t", "mean"),
    ).reset_index()
    cells = grid.merge(stats, on="cell_idx", how="left")
    cells = cells.to_crs(3857)
    Path(a.comparison_figure).parent.mkdir(parents=True, exist_ok=True)

    faixas_tempo = [0, 10, 15, 30, 50, np.inf]
    rotulos_tempo = ["0–10 min", "10–15 min", "15–30 min", "30–50 min", "> 50 min"]
    cores_tempo = ["#1f4e79", "#7fb3d5", "#ffe066", "#ff9f43", "#c0392b"]

    def plot_categorico(ax, column, bins, cmap_name, title, inacessivel=None, labels=None):
        labels = labels or [f"{bins[i]:.1f}–{bins[i + 1]:.1f}" for i in range(len(bins) - 1)]
        faixa = f"{column}_faixa"
        # A coluna nasce como string (não como Categorical de `pd.cut`), para
        # aceitar a categoria extra "inacessível" — `inf` não entra nos bins,
        # porque `pd.cut` exige bins monótonos e `inf` quebra o último intervalo.
        faixas = pd.cut(cells[column], bins=bins, labels=labels,
                        include_lowest=True, right=True).astype(object)
        if inacessivel is not None:
            faixas = faixas.where(~inacessivel, "inacessível")
        ordem = labels + (["inacessível"] if inacessivel is not None else [])
        cells[faixa] = pd.Categorical(faixas, categories=ordem, ordered=True)
        cmap = ListedColormap(cores_tempo) if labels == rotulos_tempo else cmap_name
        cells.plot(column=faixa, cmap=cmap, legend=True, ax=ax,
                   edgecolor="white", linewidth=0.1,
                   missing_kwds={"color": "lightgrey", "label": "Sem dados"},
                   legend_kwds={"loc": "lower left", "fontsize": 7})
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldStreetMap, alpha=0.75, zoom="auto")
        except Exception as error:
            print(f"basemap indisponível: {error}")
        ax.set_title(title)
        ax.set_axis_off()

    bins_typ = faixas_tempo

    # Células que perderam o acesso: tempo condicionado infinito.
    inacessivel = cells["avg_time_cond"].replace(-np.inf, np.nan).eq(np.inf)
    cells.loc[inacessivel, "delta_avg"] = np.nan
    cells.loc[inacessivel, "avg_time_cond"] = np.nan

    n_quantiles = 7
    delta_vals = cells["delta_avg"].dropna()
    bins_delta = sorted(set(np.quantile(delta_vals, np.linspace(0, 1, n_quantiles + 1))))
    if 0 not in bins_delta and len(bins_delta) > 2:
        bins_delta = sorted(set(list(bins_delta) + [0.0]))
    if len(bins_delta) < 3:
        bins_delta = [delta_vals.min(), delta_vals.max()]

    fig, axes = plt.subplots(1, 3, figsize=(18, 7))
    plot_categorico(axes[0], "avg_time_typ", bins_typ, "RdYlBu_r",
                    "Tempo médio — típico", labels=rotulos_tempo)
    plot_categorico(axes[1], "avg_time_cond", bins_typ, "RdYlBu_r",
                    "Tempo médio — condicionado", inacessivel=inacessivel,
                    labels=rotulos_tempo)
    plot_categorico(axes[2], "delta_avg", bins_delta, "YlOrRd",
                    "Δ tempo (condicionado − típico)", inacessivel=inacessivel)
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.02, top=0.94, wspace=0.02)
    fig.savefig(a.comparison_figure, dpi=150, bbox_inches="tight")
    plt.close(fig)


def figure_typical(a):
    matrix = pd.read_parquet(a.matrix)
    grid = gpd.read_parquet(a.grid)
    stats = matrix.groupby("cell_idx")["travel_time"].mean().rename("avg_time_typ").reset_index()
    cells = grid.merge(stats, on="cell_idx", how="left")
    cells = cells.to_crs(3857)
    bins = [0, 10, 15, 30, 50, np.inf]
    labels = ["0–10 min", "10–15 min", "15–30 min", "30–50 min", "> 50 min"]
    colors = ["#1f4e79", "#7fb3d5", "#ffe066", "#ff9f43", "#c0392b"]
    cells["tempo_faixa"] = pd.cut(cells["avg_time_typ"], bins=bins, labels=labels,
                                   include_lowest=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    cells.plot(column="tempo_faixa", cmap=ListedColormap(colors), legend=True, ax=ax,
               edgecolor="white", linewidth=0.1,
               missing_kwds={"color": "lightgrey", "label": "Sem dados"},
               legend_kwds={"loc": "lower left", "fontsize": 8})
    try:
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldStreetMap, alpha=0.75, zoom="auto")
    except Exception as error:
        print(f"basemap indisponível: {error}")
    ax.set_title("Tempo médio de acesso — Porto Alegre (cenário típico)")
    ax.set_axis_off(); plt.tight_layout()
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.output, dpi=150, bbox_inches="tight"); plt.close(fig)


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="stage", required=True)
    q = sub.add_parser("prepare"); q.add_argument("--config"); q.add_argument("--grid"); q.add_argument("--pois"); q.add_argument("--pois-snapped"); q.add_argument("--snapped"); q.add_argument("--graph"); q.add_argument("--edges"); q.set_defaults(fn=prepare)
    q = sub.add_parser("route"); q.add_argument("--scenario"); q.add_argument("--config"); q.add_argument("--snapped"); q.add_argument("--pois"); q.add_argument("--graph"); q.add_argument("--edges"); q.add_argument("--grid"); q.add_argument("--output"); q.set_defaults(fn=route)
    q = sub.add_parser("comparison"); q.add_argument("--typical"); q.add_argument("--conditioned"); q.add_argument("--output"); q.set_defaults(fn=comparison)
    q = sub.add_parser("indicators"); q.add_argument("--config"); q.add_argument("--typical"); q.add_argument("--conditioned"); q.add_argument("--population"); q.add_argument("--output"); q.set_defaults(fn=indicators)
    q = sub.add_parser("figure-typical"); q.add_argument("--matrix"); q.add_argument("--grid"); q.add_argument("--output"); q.set_defaults(fn=figure_typical)
    q = sub.add_parser("figures"); q.add_argument("--comparison"); q.add_argument("--grid"); q.add_argument("--comparison-figure"); q.set_defaults(fn=figures)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__": main()
