# Próximos Passos — ambx

## Pendências

- Conectar o Censo à malha: **IVS** por célula (4 eixos, §Decisões) e habilitar o F15
  ponderado pela população na regra `indicators`.
- Completar os autores das referências adicionadas em `refs.bib` (Huang, Sousa, Xu,
  Lin, Naserikia, Chen) — hoje estão com `author={Sobrenome, ...}`.
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
- **Penalização térmica:** linear, `f(T) = clip(1 + 0,0070·(T − 23), 1, 2)`.
  `k` e `t0` vêm ambos de Huang et al. (2018); a LST entra como proxy ordinal de T_ar.
- **Movimento de massa** é interdição (`inf`), não lentidão: é bloqueio de via.
- **Cenários demonstrativos** têm sufixo `_demo_kNN` (`lst_demo_k05`) e existem para
  evidenciar o mecanismo da lib; nunca substituem o resultado principal.
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

## Penalização térmica (LST)

Função linear: `f(T) = clip(1 + k·(T − t0), 1, fmax)`.

**Justificativa em três saltos** (cada um declarado na dissertação):

1. **LST → T_ar** (Sousa et al., 2022, São Paulo): r = 0,81/0,82; MAE 1,2–1,9 °C.
   Sustenta LST como *proxy ordinal* de calor, não conversão.
2. **T_ar → velocidade** (Huang et al., 2018): −7% em "economical speed" de
   23 → 33 °C ⇒ **k = 0,0070/°C**.
   Apoio qualitativo: Chen et al. (2023), +3 s/100 m com calor e ausência de árvore.
3. **Salto assumido:** aplicar `k` de T_ar diretamente sobre LST (equivale a `b = 1`
   na relação LST–T_ar).

**Limitações a declarar:**
- Nenhum estudo regride velocidade diretamente sobre LST (Lin et al., 2024 usa LST
  para *ciclismo*, não caminhada).
- Sousa não publica slope, apenas r e MAE; ΔLST construído–rural = 5,8–11,5 °C no
  verão, ou seja, o viés é **espacialmente sistemático** e maior onde o calor importa.
- Huang é população jovem saudável, em câmara; não pedestres reais.

**Formulação de uso:** a penalização é **índice ordinal de exposição térmica**,
calibrada pela sensibilidade de Huang (2018); a magnitude é indicativa, não preditiva.

**Parâmetros:** `k = 0,0070` (Huang 2018); `t0 = 23 °C` (referência termoneutra de
Huang 2018); `fmax = 2,0` (arbitrário — só salvaguarda contra pixel anômalo; a 50 °C
o fator é 1,19, então o teto não atua em dado realista).

**Curva calibrada:** 25 °C → 1,014 | 30 → 1,049 | 35 → 1,084 | 40 → 1,119.

**Composto com área verde:** o verde atenua **apenas o excesso sobre 1,0**
(`1 + (f − 1)·0,75`), nunca a linha de base — senão ponto quente com verde ficaria
mais barato que o típico. A atenuação de **0,75 é arbitrária** (sem fonte).

**Camada de área verde:** o produto é um **raster binário de 5 m** com dilatação de
5 m, gerado pelo ETL. A fonte vetorial (126 mil polígonos, 756 MB) não é usada: as
vias passam ao redor das praças e só 3,4% dos pontos da rede caíam em vegetação. A
dilatação modela a sombra da copa sobre a calçada e eleva a cobertura para **24,1%**.

**Efeito medido (Curitiba):** `lst` +2,80%; `lst_green_composite` **+2,68%** — o verde
reduz 0,12 p.p., coerente com 24,1% de cobertura × 25% de atenuação × 3,2% de excesso
térmico. O efeito é pequeno porque a penalização calibrada é suave, não por falta de
dado.

**Cenário demonstrativo.** `lst_demo_k05` / `lst_green_composite_demo_k05` usam
`k = 0,05` (≈7× a calibração), com `t0` e `fmax` iguais. Existem para evidenciar a
resposta da lib a um gradiente térmico severo; **não são resultado** e não têm
respaldo empírico. A 35 °C o fator vai a 1,60.

**Padrão de nomes:** cenário = `<variável>_<propósito>_<parâmetro>`, com o propósito
omitido quando é o principal. Ex.: `lst` (calibrado), `lst_demo_k05` (demonstrativo).

## Penalização de Porto Alegre

**Cenários:** `inundacao`, `movimento_massa` e `combinado` (os dois eventos
simultâneos). A composição é multiplicativa, então a interdição do deslizamento
domina a penalização de inundação na mesma aresta.

**Inundação (`porto_alegre_inundacao`): penaliza, não bloqueia.** Água na via
atrasa a caminhada, mas é transponível. A classe `Alto` recebe fator **2,0**,
calibrado por Xu et al. (2026, *Acta Polytechnica CTU*): 188 participantes, e a
0,35 m de lâmina d'água a velocidade caiu **38,6% (homens) e 44,8% (mulheres)**.
Fator = 1/(1 − 0,448) = 1,81 → arredondado para 2,0 (metade da velocidade).
`Médio` (1,5) e `Baixa` (1,1) **não têm fonte** — interpolação arbitrária.

**Movimento de massa (`porto_alegre_movimento_massa`): interdita.** Não há
estudo ligando deslizamento à redução de velocidade de caminhada; a literatura
trata o fenômeno como **bloqueio de via**. O cenário assume o evento **ocorrido**
e aplica `inf` em `Alta` e `Média`; `Baixa` fica livre (é suscetibilidade baixa,
não indicação de ocorrência).

**Impacto medido na rede de Porto Alegre** (OSMnx, 42.074 nós / 113.860 arestas):

| Classe | Área | Arestas bloqueadas |
|---|---:|---:|
| `Alta` | 8,6 km² | 952 (0,8%) |
| `Média` | 67,8 km² | 10.946 (9,6%) |
| **Alta + Média** | 76,4 km² | 11.898 (10,4%) |

Após o bloqueio restam 4.353 componentes conexas; a maior concentra 36.647 dos
42.074 nós (87%). A rede **não colapsa, mas fragmenta-se** — 13% dos nós ficam
isolados. Isso é um **resultado** (perda de acesso), não uma falha, e deve ser
apresentado junto ao cenário.

**Observação:** o volume de áreas não acompanha o peso no bloqueio. `Média` tem
8× a área de `Alta` e bloqueia 11× mais arestas, por concentrar malha viária
urbana; `Alta` fica em áreas periféricas de baixa densidade viária.

## Convenção de ausência (regras compostas)

- O dict entregue à `penalty_fn` **sempre tem todas as chaves** de `rule.layers`; a
  ausência vem no **valor** (`None` ou `NaN`).
- Amostragem vetorial devolve `NaN` fora de polígono (não `0.0`).
- ⚠️ `bool(nan)` é `True`. Teste ausência com `pd.isna`, nunca com o valor direto.
