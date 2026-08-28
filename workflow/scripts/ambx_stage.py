"""Stages used by the first Snakemake workflow version."""
from __future__ import annotations

import argparse, json, pickle, sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from ambx.grid import generate_grid, GridFormat
from ambx.network import add_travel_time, get_graph_edges, get_network, project_network, snap_grid_to_network
from ambx.pois import get_pois
from ambx.routing import routing_matrix, snap_pois_to_network
from ambx.environment import build_environment
from ambx.penalties import PenaltyRule, compose_penalties
from ambx.indicators import compute_all_indicators


def cfg(path):
    with open(path) as f:
        return yaml.safe_load(f)


def penalty(t):
    if t <= 25: return 1.0
    if t <= 27: return 1.2
    if t <= 30: return 1.5
    return 2.0


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


def route(a):
    c = cfg(a.config)
    with open(a.graph, "rb") as f: graph = pickle.load(f)
    snapped = gpd.read_parquet(a.snapped); pois = gpd.read_parquet(a.pois)
    if a.scenario == "conditioned":
        edges = gpd.read_parquet(a.edges)
        grid = gpd.read_parquet(str(Path(a.snapped).parent / "grid.parquet"))
        env = build_environment(grid, raster_paths=[a.raster])
        rule = PenaltyRule(Path(a.raster).stem, "raster", "travel_time", penalty)
        penalized = compose_penalties(edges, env, rules=[rule], weight_field="travel_time")
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
    result = compute_all_indicators(pd.read_parquet(a.typical), pd.read_parquet(a.conditioned), k=3)
    serial = {k: (v.to_dict() if isinstance(v, pd.DataFrame) else v) for k, v in result.items()}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True); Path(a.output).write_text(json.dumps(serial, default=str))


def figures(a):
    comparison = pd.read_parquet(a.comparison)
    grid = gpd.read_parquet(a.grid)
    stats = comparison.groupby("cell_idx").agg(
        avg_time_typ=("travel_time_typ", "mean"),
        avg_time_cond=("travel_time_cond", "mean"),
        delta_avg=("delta_t", "mean"),
    ).reset_index()
    cells = grid.merge(stats, on="cell_idx", how="left")
    Path(a.comparison_figure).parent.mkdir(parents=True, exist_ok=True)

    def plot_categorico(ax, column, bins, cmap_name, title):
        labels = [f"{bins[i]:.1f}–{bins[i + 1]:.1f}" for i in range(len(bins) - 1)]
        faixa = f"{column}_faixa"
        cells[faixa] = pd.cut(cells[column], bins=bins, labels=labels,
                              include_lowest=True, right=True)
        cells.plot(column=faixa, cmap=cmap_name, legend=True, ax=ax,
                   edgecolor="white", linewidth=0.1,
                   missing_kwds={"color": "lightgrey", "label": "Sem dados"},
                   legend_kwds={"loc": "lower left", "fontsize": 7})
        ax.set_title(title)
        ax.set_axis_off()

    n_quantiles = 7
    vals_typ = cells["avg_time_typ"].dropna()
    bins_typ = sorted(set(np.quantile(vals_typ, np.linspace(0, 1, n_quantiles + 1))))
    if len(bins_typ) < 3:
        bins_typ = [vals_typ.min(), vals_typ.max()]

    delta_vals = cells["delta_avg"].dropna()
    bins_delta = sorted(set(np.quantile(delta_vals, np.linspace(0, 1, n_quantiles + 1))))
    if 0 not in bins_delta and len(bins_delta) > 2:
        bins_delta = sorted(set(list(bins_delta) + [0.0]))
    if len(bins_delta) < 3:
        bins_delta = [delta_vals.min(), delta_vals.max()]

    fig, axes = plt.subplots(1, 3, figsize=(22, 7))
    plot_categorico(axes[0], "avg_time_typ", bins_typ, "RdYlBu_r",
                    "Tempo médio — típico")
    plot_categorico(axes[1], "avg_time_cond", bins_typ, "RdYlBu_r",
                    "Tempo médio — condicionado (LST)")
    plot_categorico(axes[2], "delta_avg", bins_delta, "YlOrRd",
                    "Δ tempo (condicionado − típico)")
    plt.tight_layout()
    fig.savefig(a.comparison_figure, dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    cells["delta_avg"].dropna().plot.hist(bins=30, ax=ax,
                                           color="steelblue", edgecolor="white")
    ax.set_title("Curitiba — distribuição da variação do tempo de acesso")
    ax.set_xlabel("Delta de tempo (min)")
    ax.set_ylabel("Número de células")
    plt.tight_layout()
    fig.savefig(a.histogram, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="stage", required=True)
    q = sub.add_parser("prepare"); q.add_argument("--config"); q.add_argument("--grid"); q.add_argument("--pois"); q.add_argument("--pois-snapped"); q.add_argument("--snapped"); q.add_argument("--graph"); q.add_argument("--edges"); q.set_defaults(fn=prepare)
    q = sub.add_parser("route"); q.add_argument("--scenario"); q.add_argument("--config"); q.add_argument("--snapped"); q.add_argument("--pois"); q.add_argument("--graph"); q.add_argument("--edges"); q.add_argument("--raster"); q.add_argument("--output"); q.set_defaults(fn=route)
    q = sub.add_parser("comparison"); q.add_argument("--typical"); q.add_argument("--conditioned"); q.add_argument("--output"); q.set_defaults(fn=comparison)
    q = sub.add_parser("indicators"); q.add_argument("--typical"); q.add_argument("--conditioned"); q.add_argument("--output"); q.set_defaults(fn=indicators)
    q = sub.add_parser("figures"); q.add_argument("--comparison"); q.add_argument("--grid"); q.add_argument("--comparison-figure"); q.add_argument("--histogram"); q.set_defaults(fn=figures)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__": main()
