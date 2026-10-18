# Avaliação do Repositório — Estado Atual e Lacunas

> Diagnóstico. Base: `docs/qualifying/proposta_qualificacao.pdf`.
> Agenda, decisões e convenções: `proximos-passos.md`.

**14/10/2026.**

---

## 1. O projeto

**ambx** (*Ambient Access*): acessibilidade urbana de curta distância sob perturbações
ambientais. Cidade = malha + POIs + grafo viário. Acessibilidade medida por **PTh**,
**Gini** e **F15**, comparando cenário **típico** (custo = comprimento) e **condicionado**
(custo penalizado por camadas ambientais, `W_cond = f(W_base, C)`).

Caso de uso: cruzar a perda de acessibilidade com dados socioeconômicos — *onde*,
*quanto* e *para quem*.

- **Curitiba** — variável contínua (raster LST).
- **Porto Alegre** — variável discreta (polígonos de risco geológico, CPRM).

---

## 2. Etapas: estado e pendências

| # | Etapa | Estado | Pendências |
|---|---|:--:|---|
| 1 | Preparação de Dados | 🟢 | Documentar proveniência do raster LST (produto, sensor, data, resolução) |
| 2 | Implementação Computacional | 🟢 | Testes de `indicators`, `demographics`, `routing` |
| 3 | Aplicação Experimental | 🟡 | F15 sem população; `run_config` das execuções |
| 4 | Análise Socioespacial | 🔴 | Tudo: significância, regressão, LISA, agrupamento, IVS |
| 5 | Redação e Revisão | 🟡 | Preencher `sections/5.results.tex`; coletânea de artigos |

---

## 3. O que existe

**Lib `ambx`** — 9 módulos: `grid`, `utils`, `network`, `pois`, `routing`, `environment`,
`penalties`, `demographics`, `indicators`.

- `penalties` — regras simples (raster/vector) e compostas (`layers=[...]`).
- `routing` — A\* com heurística euclidiana admissível, paralelizado.
- `indicators` — PTh, Gini, F15. F15 **exige** `population`, senão sai vazio.
- `demographics` — `load_tracts`, `interpolate_to_grid` (setor → célula).

**Workflow** — um `Snakefile` para todas as cidades; `--configfile
workflow/config/<cidade>.yaml`. Penalizações em `workflow/rules/`, importadas pelo YAML.

- Curitiba: `typical`, `lst`, `lst_green_composite`, `lst_demo_k05`,
  `lst_green_composite_demo_k05` → ✅ executado (17/10).
- Porto Alegre: `typical`, `inundacao`, `movimento_massa`, `combinado` → ✅ executado
  (17/10).

**Testes** — 9, todos passando (`test_composite_penalty`, `test_cost_modifier_smoke`,
`test_geoparquet_penalty`).

**Dados** — Censo 2022 (`censo_2022.geoparquet`), área verde de Curitiba, LST
(`LST_Anual_2026_221077_Mediana.tif`), camadas de POA (CPRM). Todos presentes.

---

## 4. Lacunas

**Censo → célula (#1).** O arquivo existe, mas não chega às células. Filtrar municípios
(`4106902`, `4314902`), interpolar para a malha. Pré-requisito do F15 e da Etapa 4.

**F15 vazio (#8).** A regra `indicators` chama `compute_all_indicators` sem `population`.
Depende do item acima.

**Porto Alegre (#7).** `results/porto_alegre/` não existe.

**Penalizações hardcoded (#5).** Limiares fixos no código (ex.: LST 25/27/30 °C →
1.0/1.2/1.5/2.0). Parametrizar no YAML e documentar a calibração.

**Etapa 4 ausente (#9–13).** Significância, LISA (`esda`/`libpysal`/`splot`),
regressão, agrupamento. Nada implementado. `comparison`/`inequality` saíram do escopo
da lib por decisão de arquitetura — implementar como scripts/notebooks de análise.

**Redação (#14–15).** Resultados reais não incorporados.

**Esclarecimentos** (não são lacunas): POIs vêm **só do OSM** por decisão, não da base
de alvarás da Prefeitura; "risco geológico" de POA **é** `movimento_massa_cprm.geojson`
(a mesma camada, dois nomes); `inundacao_cprm.geojson` é camada extra, não prevista.

---

## 5. Riscos técnicos abertos

1. **`comparison` não reporta pares perdidos** — o merge inner preserva
   `travel_time=NaN`, mas a regra não conta esses pares.
2. **`routing.py` sem guard `__main__`** e com `print`s → stdout poluído no Snakemake;
   risco em `spawn` (macOS/Windows).
3. **Aresta colinear à borda do polígono** — em `_segment_factors`, a interseção vira
   `LineString` (não `Point`), nenhum corte é gerado, e a agregação `mean` superatenua
   (0,75 em vez de 0,875). Raro nos dados atuais; revisitar se aparecer.
