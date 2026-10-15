# Próximos Passos — ambx

## Pendências

- Refinar as funções de penalização **por cidade** e documentar a calibração.
- Conectar o Censo à malha: **IVS** por célula (4 eixos, §Decisões) e habilitar o F15
  ponderado pela população na regra `indicators`.
- Executar o workflow de Porto Alegre → `results/porto_alegre/`.
- Definir `run_config`/metadados de cada execução.
- Análise socioespacial: significância, regressão, LISA, agrupamento — como
  scripts/notebooks, não na lib.
- Preencher `sections/5.results.tex` com os resultados reais.
- Registrar proveniência do raster LST (produto, sensor, data, resolução).

## Decisões

- Snakemake é o orquestrador; **um** `Snakefile` para todas as cidades.
- Penalizações são funções Python em `workflow/rules/`; o YAML seleciona função,
  camadas e parâmetros.
- Um cenário pode usar várias penalizações, aplicadas **na ordem** declarada no YAML.
- Resultados tabulares em **Parquet**; cada execução preserva sua configuração.
- `comparison`/`inequality` e o **IVS** ficam **fora da lib**. A lib expõe só
  `demographics.interpolate_to_grid` (setor → célula). Não haverá `socioeconomic.py`.
- POIs vêm **exclusivamente do OSM**.
- **IVS — 4 eixos**, formados **no setor, antes de interpolar** (razão de agregados
  não comuta com ponderação por área):

  | Eixo | Fórmula | Orientação |
  |---|---|---|
  | `frac_preta_parda` | `(V01318 + V01320) / V01006` | maior = mais vulnerável |
  | `renda` | `log1p(V06004)` | invertido |
  | `dep_idoso` | `Σ(V00654..V00656) / Σ(V00644..V00656)` | maior = mais vulnerável |
  | `taxa_alf` | `Σ(V00748..V00760) / V01006` | invertido |

  `V01006` = pop. total; `V01318`/`V01320` = preta/parda; `V00644..V00656` = 15+
  (dos quais `V00654..V00656` = 60+); `V00748..V00760` = alfabetizados; `V06004` =
  rendimento do responsável. **Escolaridade não entra:** não existe em nível de setor.

## Convenção de ausência (regras compostas)

- O dict entregue à `penalty_fn` **sempre tem todas as chaves** de `rule.layers`; a
  ausência vem no **valor** (`None` ou `NaN`).
- Amostragem vetorial devolve `NaN` fora de polígono (não `0.0`).
- ⚠️ `bool(nan)` é `True`. Teste ausência com `pd.isna`, nunca com o valor direto.
