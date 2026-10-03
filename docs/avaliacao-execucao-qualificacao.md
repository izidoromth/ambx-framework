# Avaliação do Repositório — Estado Atual e Lacunas para Execução da Proposta de Qualificação

> Documento de diagnóstico. Base de referência: `docs/proposta_qualificacao.pdf`
> (proposta da qualificação).
>
> **Revisão 3 — 03/10/2026.** Consolida o diagnóstico e a agenda de execução.
> Absorveu e substituiu os antigos `plano-implementacao-use-cases.md` e
> `proximos-passos.md` (removidos).
>
> **Revisão 2 — 03/10/2026.** Atualizado após o `git pull` (commit `a7844c8`) e após a
> conclusão de: ETL do Censo 2022, ETL da Área Verde de Curitiba, regras de penalização
> **compostas**, suíte de testes e padronização das dependências.

---

## 1. Entendimento do Projeto

O **ambx** (*Ambient Access*) é um framework para avaliar a **acessibilidade urbana
de curta distância sob perturbações climáticas/ambientais**. A cidade é modelada
como um sistema espacial discreto (malha territorial + POIs + rede viária em grafo)
e acessibilidade é medida comparando-se dois cenários:

1. **Cenário Típico** — custo de cada aresta = comprimento do trecho (tempo de
   caminhada a velocidade constante).
2. **Cenário Condicionado** — custos penalizados por camadas ambientais
   (rasters contínuos ou polígonos vetoriais) via função de penalização
   `W_cond = f(W_base, C)`.

A comparação entre os indicadores (**PTh**, **Índice G**, **F15**) dos dois cenários
revela *onde*, *quanto* e *para quem* a acessibilidade é perdida, e é cruzada com
dados socioeconômicos (renda, escolaridade, densidade) para análise de desigualdade.

**Estudos de caso previstos:**
- **Curitiba (PR)** — variável **contínua**: raster de temperatura de superfície (LST).
- **Porto Alegre (RS)** — variável **discreta**: polígonos de risco geológico/geotécnico (CPRM/GeoPOA).

O cronograma da proposta prevê 5 etapas (junho–outubro): Preparação de Dados →
Implementação Computacional → Aplicação Experimental → Análise Socioespacial →
Redação e Revisão.

---

## 2. Estado Atual — O que já existe

### 2.1 Biblioteca `ambx` (`scripts/ambx/`)

Todos os 9 módulos implementados: `grid`, `utils`, `network`, `pois`, `routing`,
`environment`, `penalties`, `demographics`, `indicators`.

Destaques para quem retomar o código:

- **`penalties`** — suporta regras **simples** (`layer_type="raster"` ou `"vector"`) e
  **compostas** (`layer_type="composite"` + `layers=[...]`), em que a `penalty_fn`
  recebe um dicionário nomeado com todas as camadas do ponto.
- **`routing`** — A\* com heurística euclidiana admissível e paralelismo via
  `multiprocessing.Pool`.
- **`indicators`** — `compute_pth`, `compute_pth_wide`, `compute_gini`, `compute_f15`,
  `compute_all_indicators`. O F15 **exige** `population`; sem ela o resultado sai vazio.

**Testes:** `tests/` contém 9 testes (`test_composite_penalty`, `test_cost_modifier_smoke`,
`test_geoparquet_penalty`) — **todos passando**.

> ⚠️ A **penalização composta** existe na lib e está testada, mas **ainda não é
> utilizada pelo workflow** (ver Seção 5, item 1).
>
> ⚠️ Por decisão de design, `comparison` e `inequality` **foram retirados do escopo
> da lib** (ver `README.md`). Isso cria a principal lacuna: as Etapas 3 (validação
> estatística/mapeamento) e 4 (regressão/clusterização) da proposta **não possuem
> implementação correspondente**.

### 2.2 Workflow (Snakemake)

- Um único `workflow/Snakefile` atende todas as cidades/cenários; a cidade é escolhida
  via `snakemake --configfile workflow/config/<cidade>.yaml`.
- Configurações existentes:
  - `workflow/config/curitiba.yaml` — cenários `typical`, `lst`, `lst_green`,
    `lst_green_composite`
  - `workflow/config/porto_alegre.yaml` — cenários `typical`, `inundacao`,
    `movimento_massa`, `combinado`
- As funções de penalização ficam em `workflow/rules/` e são importadas
  dinamicamente pelo YAML: `curitiba_lst`, `curitiba_green_modifier`,
  `curitiba_lst_green`, `porto_alegre_inundacao`, `porto_alegre_movimento_massa`.
- **Regras compostas** (`input_type: composite`) são declaradas com `layers` +
  `inputs` no YAML e montadas por `_build_rule` no `ambx_stage.py`.
- Regras: `prepare`, `route_typical`, `route_conditioned` (wildcard de cenário),
  `indicators`, `comparison`, `figures`, `figures_typical`, `all`.
- Produtos por cenário: `matrix_<cenario>.parquet`, `indicators_<cenario>.json`,
  `comparison_<cenario>.parquet`, figuras.
- **A pipeline de Porto Alegre (penalização vetorial) já está contemplada** no mesmo
  Snakefile/config.
- `results/` **não existe** → o workflow ainda **não foi executado**.

### 2.3 Dados disponíveis

| Camada | Arquivo | Estágio | Observações |
|--------|---------|---------|-------------|
| Censo 2022 | `data/processed/censo_2022/censo_2022.geoparquet` + `metadados.json` | ✅ Baixado/gerado | Pronto para `ambx.demographics` |
| Área Verde Curitiba | `data/processed/curitiba/area_verde_2019.geoparquet` + `.json` | ✅ Gerado | Insumo do cenário `lst_green` |
| LST (raster) | `data/raw/curitiba/LST_Anual_2026_221077_Mediana.tif` | ✅ | Proveniência/produto ainda não documentados |
| Movimento de massa / risco geológico | `data/raw/porto_alegre/movimento_massa_cprm.geojson` | ✅ | CPRM — **é** a camada de "risco geológico" citada na proposta |
| Inundação | `data/raw/porto_alegre/inundacao_cprm.geojson` | ✅ | CPRM — **não citada na proposta** |

### 2.4 Documentos e dependências

- `docs/proposta_qualificacao.pdf` — proposta completa (com apêndice do artigo SBBD).
- `docs/qualifying/` — versão LaTeX em andamento da dissertação (`main.tex` + `sections/`).
- `README.md` (raiz) — visão geral da lib e escopo.
- `workflow/README.md` — **guia de execução** do workflow por cidade/cenário.
- `data/raw/README.md`, `data/processed/README.md` — proveniência dos dados.
- `requirements.txt` — **enxuto e pinado** (núcleo geoespacial + `pytest`, `ruff`,
  `snakemake`).
- `notebooks/ambx_tests_porto_alegre.ipynb` — experimentos exploratórios de POA.
- `notebooks/qualifying/` — notebooks de geração de cenários simulados.

---

## 3. Mapeamento Proposta × Estado Atual

| Etapa da proposta | Prazo | Estado | Principais pendências |
|-------------------|-------|:------:|----------------------|
| 1. Preparação de Dados | Junho | 🟢 Quase completa | Censo, área verde e camadas de POA OK; falta a documentação da origem do LST |
| 2. Implementação Computacional | Julho | 🟢 Quase completa | Calibrar a função de penalização e rodar análise de sensibilidade |
| 3. Aplicação Experimental | Agosto | 🔴 Incompleta | Workflow nunca executado (`results/` vazio); F15 sem população |
| 4. Análise Socioespacial | Setembro | 🔴 Ausente | Regressão, testes estatísticos, clusterização/mapas de manchas, integração do censo às células |
| 5. Redação e Revisão | Outubro | 🟡 Parcial | Resultados reais ainda não incorporados; coletânea de artigos |

---

## 4. O que está faltando (lacunas)

### 4.1 Etapa 1 — Preparação de Dados

1. ~~**Censo Demográfico 2022.**~~ ✅ **Resolvido**: `data/processed/censo_2022/censo_2022.geoparquet`
   (+ `metadados.json`) já foi gerado pelo ETL. **Falta conectá-lo ao workflow**:
   - Filtrar os municípios (Curitiba `4106902`, Porto Alegre `4314902`).
   - Aplicar `demographics.interpolate_to_grid` para obter **população/renda/escolaridade
     por célula** (insumo do F15 e da regressão).

2. **POIs de Curitiba: apenas OSM (decisão, não lacuna).** A proposta previa
   complementar/validar os POIs com a base de alvarás da Prefeitura de Curitiba;
   **decidido usar exclusivamente os POIs do OSM** (`pois.get_pois`). Ao redigir a
   dissertação, registrar essa escolha e a limitação associada (cobertura e
   atualidade do OSM), já que se afasta da proposta original.

3. **"Áreas de Risco Geológico" de POA = movimento de massa (esclarecido).** A proposta
   cita duas camadas (*movimentos de massa* e *risco geológico*); na prática é **a mesma
   camada** — `data/raw/porto_alegre/movimento_massa_cprm.geojson` (CPRM; o
   `data/raw/README.md` já a descreve como "penalização por risco geológico"). Não há
   camada faltando. A `inundacao_cprm.geojson` é uma **camada adicional**, não prevista
   na proposta (usada no cenário `inundacao` e no `combinado`).

4. **Documentação/proveniência do raster LST.**
   A proposta cita Landsat 8/9 (ST_TRAD, Earth Explorer). O arquivo é
   `LST_Anual_2026_221077_Mediana.tif`. Falta documentar produto, sensor, data e
   resolução (metadados), para garantir reprodutibilidade.

5. ~~**Área verde de Curitiba.**~~ ✅ **Resolvido**:
   `data/processed/curitiba/area_verde_2019.geoparquet` (+ `.json`) já foi gerado pelo
   ETL (`download_area_verde_curitiba.py`).

### 4.2 Etapa 2 — Implementação Computacional

6. ~~**Ligar a penalização composta ao workflow.**~~ ✅ **Resolvido (03/10/2026):**
   o YAML aceita `input_type: composite` (com `layers` + `inputs`) e o
   `ambx_stage.py` monta a `PenaltyRule` correspondente. Cenário
   `lst_green_composite` adicionado ao lado de `lst_green`. Ver Seção 5, item 1,
   para o resultado medido da comparação entre as duas semânticas.

7. **Calibração/parametrização da função de penalização.**
   As funções agora vivem em `workflow/rules/` (`curitiba_lst`, `curitiba_green_modifier`,
   `porto_alegre_*`), mas os valores são **hardcoded** (ex.: LST com limiares
   25/27/30 °C → 1.0/1.2/1.5/2.0). A proposta exige calibrar a forma funcional
   (linear/exponencial/limiar) com base na literatura (Liang et al. 2020; Obuchi et al.
   2021) e/ou análise de sensibilidade. Falta:
   - Parametrizar as funções pela configuração (yaml) em vez de valores fixos no código.
   - Rodar análise de sensibilidade dos parâmetros.

8. **Cobertura de testes.** A suíte atual tem 9 testes (composite, smoke de modificador
   de custo, geoparquet). Faltam testes para `indicators`, `demographics` e `routing`
   (módulos críticos).

### 4.3 Etapa 3 — Aplicação Experimental

9. **Executar o workflow de ponta a ponta.** `results/` está vazio. É necessário rodar
   o Snakemake para Curitiba (todos os cenários) e Porto Alegre, e versionar/registrar
   os artefatos (matrizes, indicadores, figuras).

10. **F15 nos indicadores do workflow.**
    A regra `indicators` chama `compute_all_indicators(...)` **sem população**.
    Consequência: `f15_typ`/`f15_cond` saem vazios. Falta:
    - Passar `population` (interpolação do censo) para a regra.
    - ✅ O `k` já vem do config (`k_nearest`), corrigido em 03/10/2026.

### 4.4 Etapa 4 — Análise Socioespacial (maior lacuna)

A proposta define explicitamente:

- **Análise Comparativa (§3.3):** variação relativa (Δ absoluto e percentual) ✅
  (parcialmente feito), **validação estatística** ❌ e **mapeamento espacial**
  (associação local/clusterização das manchas de degradação) ❌.
- **Análise de Desigualdade (§3.4):** **regressão linear** (PTh e ΔPTh vs renda,
  escolaridade, densidade) ❌ e **agrupamento socioespacial** (clusters contíguos e
  homogêneos) ❌.

Faltam, portanto:

11. **Testes de significância** das mudanças de tempo entre cenários
    (ex.: teste de hipóteses pareado/permutação) — não implementado em lugar algum.

12. **Mapas de manchas de degradação** via associação local/clusterização espacial
    (LISA/PySAL). As dependências `esda`/`libpysal`/`splot` **não estão instaladas**.

13. **Regressão linear** (PTh e ΔPTh como variáveis dependentes). A dependência
    `statsmodels` **não está instalada**. Pode ser implementada como notebooks/scripts
    de análise (fora da lib), mas **precisa existir**.

14. **Clusterização socioespacial** (regiões adjacentes e homogêneas em atributos
    socioeconômicos + acessibilidade). `scikit-learn` **não está nas dependências** e
    não há implementação.

15. **Integração completa com o Censo** (população/renda/escolaridade por célula),
    pré-requisito dos itens 10, 13 e 14.

> **Observação de coerência:** o README declara que `comparison` e `inequality`
> "saíram do escopo da lib". Isso é razoável como arquitetura, mas **a proposta de
> qualificação os exige como entregas** (Etapas 3 e 4). Recomenda-se implementá-los
> como **scripts/notebooks de análise** sobre os outputs da lib, mantendo a lib enxuta.

### 4.5 Etapa 5 — Redação e Revisão

16. **Preencher `docs/qualifying/sections/5.results.tex`.** Hoje só há "Resultados
    Parciais" (artigo SBBD) e "Resultados Esperados". Falta a seção de **resultados
    reais** dos experimentos (Curitiba LST/verde e Porto Alegre), com tabelas, mapas,
    valores de PTh/Gini/F15 e as análises de regressão/clusterização.

17. **Coletânea de artigos para defesa.** A Etapa 5 prevê a consolidação da coletânea;
    ainda não iniciada.

---

## 5. Inconsistências técnicas e riscos detectados

### 5.1 Corrigidos (03/10/2026)

Detalhe completo das correções no `git log`. Resumo do que foi feito, para não
reabrir a investigação:

| # | Assunto | Correção |
|:-:|---------|----------|
| 1 | **Contrato do `PenaltyRule`** | Unificado em `layers: list[str]` (obrigatório, primeiro posicional). `layer_name` e o helper `layer_names()` foram removidos. Regra simples = lista de 1 elemento; `compose_penalties` valida `len(rule.layers) == 1` para tipos não-compostos. Eliminou a ambiguidade do `name` no YAML (rótulo nas simples, nome de camada nas compostas) que causava `Camadas não encontradas: ['lst', 'area_verde']`. **Quebra de API:** call sites migrados em `scripts/ambx/penalties.py`, `workflow/scripts/ambx_stage.py`, 3 arquivos de `tests/`, notebook e 2 scripts de experimento. 9/9 testes e pipeline 10/10 jobs. |
| 2 | **CRS em `_sample_composite_raster`** | Coordenadas agora são transformadas para o CRS do **arquivo de origem** (`rio_transform`). Antes, com raster reprojetado para UTM pelo `build_environment`, a amostragem lia pixels errados. Teste: `test_composite_raster_transforms_to_source_crs`. |
| 3 | **Desempenho da amostragem composta** | Amostragem **em lote**: raster aberto 1× (era N×) e vetorial via `gpd.sjoin` (era `iterrows`). Benchmark 3.000 arestas: ~6,3 s → ~0,65 s. |
| 4 | **`k` hardcoded nos indicadores** | A regra `indicators` agora recebe `--config` e lê `k_nearest`, como o `route` já fazia. |
| 5 | **`weight_field` sem guard** | As três `apply_*` resolvem o campo internamente (`rule.weight_field or weight_field or "travel_time"`). Regra com `weight_field=None` não quebra mais. |
| 6 | **`compose_penalties` mutava a regra** | Mutação removida; o fallback é propagado por parâmetro. Teste: `test_compose_penalties_does_not_mutate_rule`. |
| 7 | **Semântica mista na composição** | Convenção definida (abaixo). Testes: `test_composite_passes_nan_for_uncovered_points`, `test_composite_dict_always_contains_all_keys`. |

**Convenção de ausência em regras compostas** (importante para quem escrever
`penalty_fn`):

- o dicionário entregue à `penalty_fn` **sempre contém todas as chaves** de
  `rule.layers`; a ausência vem no **valor**, como `None` ou `NaN`
  (**convenção: ausência = `None` ou `NaN`**);
- a amostragem vetorial devolve `NaN` para ponto fora de polígono (antes `0.0`, que se
  confundia com um valor legítimo `0`);
- o curto-circuito antigo ("qualquer NaN → fator 1.0") foi removido: a `penalty_fn` é
  quem decide;
- ⚠️ **`bool(nan)` é `True` e `bool(None)` é `False`.** Nunca use o valor direto como
  booleano — teste com `pd.isna`.

### 5.2 Abertas

1. **Duas semânticas de penalização (decisão de design, com resultado medido).**
   A lib oferece **cumulativa** (regras simples em sequência) e **composta**
   (`input_type: composite`), e a escolha fica com o usuário. O caso `lst_green`
   de Curitiba mantém **as duas** implementações para comparação:
   - `lst_green` (cumulativa) — pondera o verde pelo **comprimento exato** da
     interseção, mas **não expressa interação**: desconta verde onde não há calor
     (ex.: 20 °C + verde → fator 0,75).
   - `lst_green_composite` (composta) — vê LST e verde **no mesmo ponto** e só
     atenua onde há calor (20 °C + verde → fator 1,0). Em troca, aproxima a
     proporção de cobertura por **amostragem**.

   O experimento `scripts/experiments/composite_sampling_tradeoff.py` mede o erro
   de discretização da composta contra a cumulativa (referência exata). Com 40% da
   aresta coberta e LST 38 °C (exato = 180,00):

   | `n_samples` | valor | erro |
   |---:|---:|---:|
   | 2 | 175,00 | −2,78% |
   | 8 | 182,14 | +1,19% |
   | 32 | 179,84 | −0,09% |
   | 1024 | 179,99 | −0,01% |

   O erro **oscila** (é discretização, não ruído aleatório), mas a amplitude cai
   conforme `n_samples` cresce, convergindo para o valor da cumulativa. O custo
   adicional é proporcional ao número de pontos amostrados; **não foi medido em
   escala real** (fora do escopo do trabalho).

2. **`comparison` do workflow não reporta pares perdidos.** O merge
   `typ.merge(cond, ...)` (inner) preserva os pares com `travel_time=NaN` no
   condicionado, mas a regra não contabiliza/expõe explicitamente os "pares perdidos"
   (o script de experimento faz isso; o workflow, não).

3. **Acoplamento frágil em `route` (condicionado).** O caminho do grid é inferido de
   `Path(a.snapped).parent / "grid.parquet"`. Funciona, mas depende do layout de
   saída do `prepare`. Melhor declarar `grid` como input explícito da regra.

4. **`raster_stats_for_geometry` usa `nodata=0`** quando o raster não declara nodata
   (`environment.py`), mascarando pixels de valor `0` legítimo. A função **não é usada
   em lugar nenhum** e está marcada como não testada — inofensiva hoje, mas é uma
   armadilha latente.

5. **Docstrings com pequenas imprecisões:** `demographics.load_tracts` descreve
   entrada `.gpkg`, mas lê `read_parquet`.

6. **`routing.py` sem guard `if __name__ == "__main__"`** e com `print`s espalhados
   (poluição de stdout no Snakemake). Em Linux (fork) funciona; em Windows/macOS o
   `multiprocessing` com `spawn` pode falhar sem o guard.

7. **Partição de aresta falha quando a aresta é colinear à borda do polígono.**
    Em `_segment_factors` (`penalties.py`), os pontos de corte vêm de
    `edge_geom.intersection(polygon.boundary)` e apenas geometrias `Point`/`MultiPoint`
    são consideradas. Quando a aresta corre **sobre** um trecho da borda — comum em redes
    viárias que margeiam áreas verdes — a interseção é uma `LineString`, nenhum corte é
    gerado, a aresta vira um único segmento e o fator é decidido só pelo ponto médio.
    Reproduzido com polígono `x∈[0,5]` e aresta `(1,0)→(9,0)` (4 de 8 m cobertos):
    fator **0,75** em vez de **0,875** (superatenuação). A mesma aresta em `y=1`
    (cruzando a borda) dá 0,875 corretamente. Afeta apenas a agregação `mean`.
    **Avaliação:** considerado raro nos dados atuais e deixado de lado por decisão
    explícita; revisitar só se aparecer no experimento.

---

## 6. Agenda de execução

Esta seção consolida o plano de trabalho — incluindo o que antes estava nos docs
`plano-implementacao-use-cases.md` e `proximos-passos.md`, hoje removidos.

### 6.1 Etapas

**Etapa A — Fechar os casos de uso.** Objetivo: os quatro cenários (típico e
condicionado de Curitiba e de Porto Alegre) executáveis pelo mesmo `Snakefile`, com
resultados comparáveis e reprodutíveis.

1. ~~Ligar a penalização composta ao workflow~~ ✅ (feito — cenário `lst_green_composite`).
2. Conectar o Censo: filtrar municípios (Curitiba `4106902`, Porto Alegre `4314902`),
   interpolar população/variáveis para a malha e habilitar o **F15 ponderado pela
   população** na regra `indicators` (com `k` vindo do config).
3. Executar os cenários e validar: mesmo esquema de dados, mesmas categorias e
   unidades, matrizes e indicadores válidos, mapas com escalas comparáveis.
4. Definir o registro de `run_config` e dos metadados de cada execução (rastreabilidade).

**Critério de conclusão:** os quatro cenários executam pelo mesmo workflow a partir de
seus YAMLs, com resultados comparáveis. A etapa socioeconômica só começa depois.

**Etapa B — Análise socioespacial (Etapa 4 da proposta).**

5. Construir a tabela analítica por célula: PTh típico, condicionado, ΔPTh e atributos
   socioeconômicos (população, renda, escolaridade, densidade).
6. Aplicar as análises: testes de significância, regressão linear, agrupamento
   socioespacial e mapas de manchas (LISA).
7. Gerar tabelas, mapas e os resultados finais da dissertação.

**Etapa C — Extensões (não bloqueiam a qualificação).**

8. **Cenários de mitigação** ("Outros Casos de Uso"): usar a penalização de forma
   **inversa** — fatores < 1 para áreas favoráveis — e quantificar o ganho de
   acessibilidade. Ex.: *"plantar árvores nessas regiões reduziria o tempo de acesso
   em X%"*. O `curitiba_green_modifier` (fator 0,75) já é um caso desse tipo.

### 6.2 Decisões de arquitetura já estabelecidas

- Snakemake é o orquestrador; **um** `Snakefile` para todas as cidades.
- Penalizações são funções Python em `workflow/rules/`; o YAML seleciona função,
  camadas e parâmetros.
- Um cenário pode usar várias penalizações, aplicadas **na ordem** declarada no YAML.
- Resultados tabulares em **Parquet**; cada execução preserva sua configuração.
- `comparison`/`inequality` ficam **fora da lib**, como scripts/notebooks de análise.
- POIs vêm **exclusivamente do OSM** (`pois.get_pois`); a base de alvarás da Prefeitura
  de Curitiba, prevista na proposta, **não será usada** (ver item 2 da Seção 4.1).

### 6.3 Checklist

**Concluído:**

- [x] Baixar o Censo 2022 e gerar `censo_2022.geoparquet`.
- [x] Gerar `area_verde_2019.geoparquet` (ETL da área verde de Curitiba).
- [x] Pipeline de Porto Alegre (penalização vetorial) + configs por cidade/cenário.
- [x] Suíte de testes (9 testes) e dependências pinadas/instaladas.
- [x] Alinhar o `weight_field` das funções `apply_*` (e remover a mutação da regra).
- [x] Convenção de ausência na composição (`None`/`NaN` no valor; chaves sempre presentes).
- [x] `k` dos indicadores vindo do config (`k_nearest`), em vez de `k=3` fixo.
- [x] Penalização composta ligada ao workflow (cenário `lst_green_composite`).
- [x] Experimento de trade-off da amostragem composta.

**Bloqueadores (sem eles a proposta não fecha):**

- [ ] **Conectar população ao workflow** e habilitar **F15** nos indicadores (`k` vindo do config).
- [ ] **Executar o workflow** de Curitiba e Porto Alegre e registrar `results/`.
- [ ] **Definir `run_config`/metadados** de cada execução.

**Etapa 4 (análise socioespacial) — implementar como scripts/notebooks:**

- [ ] Testes de significância das variações de tempo (típico vs condicionado).
- [ ] Mapas de manchas de degradação (LISA/clusterização espacial — instalar
      `esda`/`libpysal`/`splot`).
- [ ] Regressão linear (PTh, ΔPTh × renda, escolaridade, densidade) — instalar
      `statsmodels`.
- [ ] Agrupamento socioespacial (contíguo e homogêneo) — instalar `scikit-learn`.

**Consolidação e reprodução:**

- [ ] Parametrizar as funções de penalização no config e documentar a calibração.
- [ ] Preencher `sections/5.results.tex` com os resultados reais.
- [ ] Ampliar a cobertura de testes (`indicators`, `demographics`, `routing`).
- [ ] Registar proveniência do raster LST (produto, sensor, data, resolução).
