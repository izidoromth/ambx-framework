"""
pipeline_curitiba_lst.py
=======================
Pipeline completa do framework ambx para Curitiba/PR com penalização
por raster LST (Land Surface Temperature - Temperatura da Superfície).

Etapas:
  1a. Malha Territorial (hexágonos 200m)
  1b. POIs categorizados (OSM)
  1c. Rede Viária (grafo OSM + travel_time)
  1d. Snapping malha ↔ rede
  2.  Roteamento A* — Cenário Típico (sem penalidades)
  3.  Carregamento do raster LST + Penalização via ``PenaltyRule`` + ``compose_penalties``
  4.  Roteamento A* — Cenário Condicionado (com penalidade LST)
  5.  Comparação Típico vs Condicionado
  6.  Visualização espacial dos impactos

Uso:
    python notebooks/pipeline_curitiba_lst.py
"""

import sys, time, warnings, os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import folium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ambx.grid import generate_grid, GridFormat
from ambx.network import (
    add_travel_time, get_network, get_graph_edges,
    project_network, snap_grid_to_network,
)
from ambx.pois import get_pois
from ambx.routing import snap_pois_to_network, routing_matrix
from ambx.environment import load_raster, build_environment
from ambx.penalties import PenaltyRule, compose_penalties
from ambx.indicators import compute_pth, compute_pth_wide, compute_gini, compute_f15, compute_all_indicators

warnings.filterwarnings("ignore")
np.random.seed(42)

# ===================================================================
# PARÂMETROS
# ===================================================================
LOCATION = "Curitiba, Parana, Brazil"
GRID_FORMAT = GridFormat.HEXAGON
CELL_SIZE = 200           # m (raio do hexágono)
POI_BUFFER = 2000         # m
NETWORK_TYPE = "walk"
WALK_SPEED_KPH = 5.0
MAX_SNAP_DIST = 1000      # m
K_NEAREST = 3
N_JOBS = 8

LST_RASTER_PATH = "data/raw/curitiba/LST_Anual_2026_221077_Mediana.tif"

def lst_penalty(t):
    """Função de penalidade por temperatura superficial."""
    if t <= 25:   return 1.0
    if t <= 27:   return 1.2
    if t <= 30:   return 1.5
    return 2.0

print(f"{'='*60}")
print(f"  ambx — Pipeline Curitiba com Penalização LST")
print(f"{'='*60}")
print(f"  Malha: {GRID_FORMAT.value}, {CELL_SIZE}m")
print(f"  Rede: {NETWORK_TYPE} ({WALK_SPEED_KPH} km/h)")
print(f"  K vizinhos: {K_NEAREST}  |  Workers: {N_JOBS}")
print(f"  Penalidade LST: 20°C→{lst_penalty(20)}  28°C→{lst_penalty(28)}  "
      f"32°C→{lst_penalty(32)}  37°C→{lst_penalty(37)}")
print()

# ===================================================================
# 1a — MALHA TERRITORIAL
# ===================================================================
print("[1a] Malha Territorial...", end=" ", flush=True)
t0 = time.time()
grid = generate_grid(LOCATION, grid_format=GRID_FORMAT, cell_size=CELL_SIZE)
print(f"{len(grid)} células  ({time.time()-t0:.1f}s)")

# ===================================================================
# 1b — POIs
# ===================================================================
print("[1b] Pontos de Interesse...", end=" ", flush=True)
t0 = time.time()
pois = get_pois(LOCATION, buffer=POI_BUFFER)
cats = pois["category"].value_counts()
print(f"{len(pois)} POIs  ({time.time()-t0:.1f}s)")
for cat, n in cats.items():
    print(f"       {cat}: {n}")

# ===================================================================
# 1c — REDE VIÁRIA
# ===================================================================
print("[1c] Rede Viária...", end=" ", flush=True)
t0 = time.time()
graph = get_network(LOCATION, network_type=NETWORK_TYPE)
graph = project_network(graph)
graph = add_travel_time(graph, speed_kph=WALK_SPEED_KPH)
edges = get_graph_edges(graph)
print(f"{graph.number_of_nodes()} nós, {graph.number_of_edges()} arestas  "
      f"({time.time()-t0:.1f}s)")

# ===================================================================
# 1d — SNAPPING
# ===================================================================
print("[1d] Snapping malha→rede...", end=" ", flush=True)
t0 = time.time()
snapped = snap_grid_to_network(grid, graph, projected=False,
                                max_distance=MAX_SNAP_DIST)
taxa = len(snapped) / len(grid) * 100
print(f"{len(snapped)}/{len(grid)} vinculadas ({taxa:.1f}%)  "
      f"({time.time()-t0:.1f}s)")

# ===================================================================
# 2 — ROTEAMENTO A* (CENÁRIO TÍPICO)
# ===================================================================
print("[2] Roteamento A* — Típico...")
pois_snapped = snap_pois_to_network(pois, graph)
print(f"     POIs snapped: {len(pois_snapped)}/{len(pois)}")

t0 = time.time()
matrix_typ = routing_matrix(snapped, pois_snapped, graph,
                            k_nearest=K_NEAREST, speed_kph=WALK_SPEED_KPH,
                            n_jobs=N_JOBS)
reach_typ = matrix_typ["travel_time"].notna().sum()
tt_typ = matrix_typ.loc[matrix_typ["travel_time"].notna(), "travel_time"]
print(f"     {len(matrix_typ)} pares em {time.time()-t0:.1f}s")
print(f"     Alcançáveis: {reach_typ}/{len(matrix_typ)} "
      f"({reach_typ/len(matrix_typ)*100:.1f}%)")
print(f"     Tempo médio: {tt_typ.mean():.1f} min  (max: {tt_typ.max():.1f})")

# ===================================================================
# 3 — CAMADA AMBIENTAL + PENALIZAÇÃO VIA API OFICIAL
# ===================================================================
print("[3] Carregando raster LST via build_environment...", end=" ", flush=True)
t0 = time.time()
env = build_environment(
    area_of_interest=grid,
    raster_paths=[LST_RASTER_PATH],
)
lst_layer = env.rasters[0]
valid = lst_layer.data[lst_layer.data != lst_layer.nodata]
print(f"shape={lst_layer.shape}  pixels válidos={len(valid)}  "
      f"média={valid.mean():.1f}°C  ({time.time()-t0:.1f}s)")

# (penalização feita dentro da etapa 3 via compose_penalties)
print("[4] Aplicando penalidade LST via compose_penalties...")
t0 = time.time()

rule = PenaltyRule(
    layer_name="LST_Anual_2026_221077_Mediana",
    layer_type="raster",
    weight_field="travel_time",
    penalty_fn=lst_penalty,
)

edges_gdf = edges.copy()
edges_penalized = compose_penalties(
    edges_gdf, env, rules=[rule], weight_field="travel_time",
)

# Grafo condicionado
graph_cond = graph.copy()
for (u, v, k), tt in zip(edges_penalized.index, edges_penalized["travel_time"]):
    if (u, v, k) in graph_cond.edges:
        graph_cond.edges[u, v, k]["travel_time"] = tt

# Estatísticas da penalização
factors = edges_penalized["travel_time"] / edges_gdf["travel_time"]
factors = factors.replace([np.inf, -np.inf], np.nan).fillna(1.0)
n_afetadas = (factors > 1.0).sum()
print(f"     Arestas com fator>1: {n_afetadas}/{len(factors)} "
      f"({n_afetadas/len(factors)*100:.1f}%)")
print(f"     Fator médio: {factors.mean():.2f}  "
      f"tempo médio: {edges_gdf['travel_time'].mean():.1f}→"
      f"{edges_penalized['travel_time'].mean():.1f} min  "
      f"({time.time()-t0:.1f}s)")

# ===================================================================
# 4 — ROTEAMENTO A* (CENÁRIO CONDICIONADO)
# ===================================================================
print("[5] Roteamento A* — Condicionado (LST)...")
t0 = time.time()
matrix_cond = routing_matrix(snapped, pois_snapped, graph_cond,
                             k_nearest=K_NEAREST, speed_kph=WALK_SPEED_KPH,
                             n_jobs=N_JOBS)
reach_cond = matrix_cond["travel_time"].notna().sum()
tt_cond = matrix_cond.loc[matrix_cond["travel_time"].notna(), "travel_time"]
print(f"     {len(matrix_cond)} pares em {time.time()-t0:.1f}s")
print(f"     Alcançáveis: {reach_cond}/{len(matrix_cond)} "
      f"({reach_cond/len(matrix_cond)*100:.1f}%)")
print(f"     Tempo médio: {tt_cond.mean():.1f} min  (max: {tt_cond.max():.1f})")

# ===================================================================
# 5 — COMPARAÇÃO
# ===================================================================
print("\n[6] Comparação Típico vs Condicionado")

cat_col = "poi_category" if "poi_category" in matrix_cond.columns else "category"
if cat_col not in matrix_typ.columns:
    alt = "poi_category" if cat_col == "category" else "category"
    if alt in matrix_typ.columns:
        matrix_typ = matrix_typ.rename(columns={alt: cat_col})

comp = matrix_typ.merge(
    matrix_cond, on=["cell_idx", "poi_idx", cat_col],
    suffixes=("_typ", "_cond"),
)
comp["delta_t"] = comp["travel_time_cond"] - comp["travel_time_typ"]
comp["delta_pct"] = (comp["delta_t"] / comp["travel_time_typ"].replace(0, np.nan)) * 100

alv_typ = comp["travel_time_typ"].notna().sum()
alv_cond = comp["travel_time_cond"].notna().sum()
perdidos = (comp["travel_time_typ"].notna() & comp["travel_time_cond"].isna()).sum()
delta = comp["delta_t"].dropna()
delta_pos = delta[delta > 0]

print(f"  {'':25s} {'Típico':>8s} {'Condic.':>8s}")
print(f"  {'Alcançáveis':25s} {alv_typ:>8d} {alv_cond:>8d}")
print(f"  {'Perdidos':25s} {perdidos:>8d}")
print(f"  Δ médio (pares c/ aumento): {delta_pos.mean():.2f} min  "
      f"(máx: {delta_pos.max():.2f})  n={len(delta_pos)}")
pct_pos = comp.loc[delta > 0, "delta_pct"].dropna()
if len(pct_pos):
    print(f"  Aumento relativo médio: {pct_pos.mean():.1f}%  "
          f"(máx: {pct_pos.max():.1f}%)")

print(f"\n  Δ médio por categoria:")
cat_delta = comp.groupby(cat_col)["delta_t"].mean().sort_values(ascending=False)
for cat, val in cat_delta.items():
    print(f"    {cat:18s}: {val:.2f} min")

# ===================================================================
# 6 — VISUALIZAÇÃO
# ===================================================================
print("\n[7] Gerando visualizações...")

# Agregar por célula
avg_typ = matrix_typ.groupby("cell_idx")["travel_time"].mean().rename("avg_time_typ")
avg_cond = matrix_cond.groupby("cell_idx")["travel_time"].mean().rename("avg_time_cond")
cell_stats = pd.DataFrame({"avg_time_typ": avg_typ, "avg_time_cond": avg_cond})
cell_stats["delta_avg"] = cell_stats["avg_time_cond"] - cell_stats["avg_time_typ"]

cells_gdf = grid.loc[snapped.index].copy()
cells_gdf["cell_idx"] = cells_gdf.index
cells_plot = cells_gdf.merge(cell_stats, on="cell_idx", how="left")

# --- Mapa Folium ---
centroid = grid.geometry.union_all().centroid
m = folium.Map(location=[centroid.y, centroid.x], zoom_start=12, control_scale=True)
cells_plot.explore(
    m=m, column="delta_avg", cmap="YlOrRd", legend=True,
    legend_kwds={"caption": "Δ tempo médio (min)", "color": "#212121"},
    tooltip=["cell_idx", "avg_time_typ", "avg_time_cond", "delta_avg"],
    style_kwds={"weight": 1.0, "fillOpacity": 0.75}, name="Δ Tempo",
)
colors_map = {"health":"#e31a1c","education":"#33a02c",
              "transportation":"#ff7f00","food":"#6a3d9a"}
for cat, color in colors_map.items():
    sub = pois[pois["category"] == cat]
    if not sub.empty:
        sub.explore(m=m, name=f"POI — {cat} ({len(sub)})",
                    color=color, marker_kwds={"radius": 3})
folium.LayerControl().add_to(m)
out_path = "notebooks/mapa_delta_curitiba_lst.html"
m.save(out_path)
print(f"  Mapa salvo: {out_path}")

# --- Matplotlib (faixas discretas — mesma escala p/ Típico e Condicionado) ---
def plot_categorico(ax, gdf, column, bins, cmap_name, title,
                    leg_kwds=None):
    """Plota células com faixas pré-definidas e legenda."""
    labels = [f"{bins[i]:.1f}–{bins[i+1]:.1f}" for i in range(len(bins)-1)]
    col_faixa = f"{column}_faixa"
    gdf[col_faixa] = pd.cut(gdf[column], bins=bins, labels=labels,
                            include_lowest=True, right=True)
    n_cats = len(gdf[col_faixa].cat.categories)
    cmap = plt.cm.get_cmap(cmap_name, n_cats)
    _leg_kwds = {"loc": "lower left", "fontsize": 7}
    if leg_kwds:
        _leg_kwds.update(leg_kwds)
    gdf.plot(column=col_faixa, cmap=cmap, legend=True, ax=ax,
             edgecolor="white", linewidth=0.1,
             legend_kwds=_leg_kwds,
             missing_kwds={"color": "lightgrey"})
    ax.set_title(title)

fig, axes = plt.subplots(1, 3, figsize=(22, 7))

# Calcula bins comuns pelos quantis do Típico (garante mesma escala nos 2 mapas)
vals_typ = cells_plot["avg_time_typ"].dropna()
n_quantis = 7
bins_typ = sorted(set(np.quantile(vals_typ, np.linspace(0, 1, n_quantis + 1))))
if len(bins_typ) < 3:
    bins_typ = [vals_typ.min(), vals_typ.max()]

# Típico
plot_categorico(axes[0], cells_plot, "avg_time_typ", bins_typ, "RdYlBu_r",
                "Tempo Médio — Típico")

# Condicionado — MESMOS bins e MESMA cmap
plot_categorico(axes[1], cells_plot, "avg_time_cond", bins_typ, "RdYlBu_r",
                "Tempo Médio — Condicionado (LST)")

# Delta — quantis centrados em 0
delta_vals = cells_plot["delta_avg"].dropna()
q_delta = sorted(set(np.quantile(delta_vals, np.linspace(0, 1, n_quantis + 1))))
if 0 not in q_delta and len(q_delta) > 2:
    q_delta = sorted(set(list(q_delta) + [0.0]))
if len(q_delta) < 3:
    q_delta = [delta_vals.min(), delta_vals.max()]
plot_categorico(axes[2], cells_plot, "delta_avg", q_delta, "YlOrRd",
                "Δ Tempo (Cond − Típico)")

plt.tight_layout()
plt.savefig("notebooks/comparacao_curitiba_lst.png", dpi=150, bbox_inches="tight")
print(f"  Figura salva: notebooks/comparacao_curitiba_lst.png")
plt.close()

# Histograma
fig, ax = plt.subplots(figsize=(10, 4))
bins = np.linspace(0, 60, 61)
ax.hist(tt_typ, bins=bins, alpha=0.6,
        label=f"Típico (média={tt_typ.mean():.1f})", color="steelblue")
ax.hist(tt_cond, bins=bins, alpha=0.6,
        label=f"Condicionado (média={tt_cond.mean():.1f})", color="tomato")
ax.set_xlabel("Tempo de viagem (min)"); ax.set_ylabel("Frequência")
ax.set_title("Distribuição dos Tempos de Viagem"); ax.legend()
plt.tight_layout()
plt.savefig("notebooks/histograma_curitiba_lst.png", dpi=150, bbox_inches="tight")
print(f"  Histograma salvo: notebooks/histograma_curitiba_lst.png")
plt.close()

# ===================================================================
# 7 — INDICADORES (PTh, Gini, F15)
# ===================================================================
print("\n" + "=" * 60)
print("  [7] Indicadores de Acessibilidade")
print("=" * 60)

# PTh — Típico
print("\n  PTh (k=3) — Típico:")
pth_typ = compute_pth(matrix_typ, k=3)
print(f"    {len(pth_typ)} linhas")
print(pth_typ.groupby("poi_category")["pth"].describe().round(2).to_string())

# PTh — Condicionado
print("\n  PTh (k=3) — Condicionado:")
pth_cond = compute_pth(matrix_cond, k=3)
print(f"    {len(pth_cond)} linhas")
print(pth_cond.groupby("poi_category")["pth"].describe().round(2).to_string())

# Gini por categoria — Típico vs Condicionado
print("\n  Índice de Gini por categoria:")
pth_wide_typ = compute_pth_wide(pth_typ)
pth_wide_cond = compute_pth_wide(pth_cond)
for cat in pth_wide_typ.columns:
    g_typ = compute_gini(pth_wide_typ[cat].dropna())
    if cat in pth_wide_cond.columns:
        g_cond = compute_gini(pth_wide_cond[cat].dropna())
        print(f"    {cat:18s}:  típico G={g_typ:.4f}  |  condic. G={g_cond:.4f}  "
              f"|  Δ={g_cond - g_typ:+.4f}")

# F15 (sem dados censitários ainda — pula)
print("\n  F15:  N/A (população por célula ainda não disponível —")
print(f"         depende do módulo demographics)")

# compute_all_indicators — teste do orquestrador
print("\n  compute_all_indicators (apenas típico, sem population):")
result = compute_all_indicators(matrix_typ, k=3)
print(f"    pth_typ:      {result['pth_typ'].shape}")
print(f"    pth_wide_typ: {result['pth_wide_typ'].shape}")
print(f"    gini_typ:     {result['gini_typ']}")
print(f"    f15_typ:      {result['f15_typ']}  (vazio, sem population)")

# ===================================================================
# RESUMO FINAL
# ===================================================================
print(f"\n{'='*60}")
print(f"  RESUMO — Curitiba com Penalização LST")
print(f"{'='*60}")
print(f"  Malha:          {len(grid)} células ({GRID_FORMAT.value}, {CELL_SIZE}m)")
print(f"  POIs:           {len(pois)} ({cats.shape[0]} categorias)")
print(f"  Rede:           {graph.number_of_nodes()} nós, {graph.number_of_edges()} arestas")
print(f"  Snapping:       {len(snapped)}/{len(grid)} ({taxa:.1f}%)")
print(f"  A* Típico:      {reach_typ} pares, média {tt_typ.mean():.1f} min")
print(f"  A* Condic.:     {reach_cond} pares, média {tt_cond.mean():.1f} min")
print(f"  Δ médio:        {delta_pos.mean():.2f} min (máx: {delta_pos.max():.2f})")
print(f"  Pares perdidos: {perdidos}")
print(f"  Arestas c/ fator>1: {n_afetadas}/{len(factors)} ({n_afetadas/len(factors)*100:.1f}%)")
print(f"{'='*60}")
print("Pipeline concluída com sucesso!")
