# Decisões — ambx

Arquitetura, convenções e a calibração das penalizações, com a justificativa de
cada escolha.

## Arquitetura

- Snakemake é o orquestrador; **um** `Snakefile` para todas as cidades.
- Penalizações são funções Python em `workflow/rules/`; o YAML seleciona função,
  camadas e parâmetros.
- Um cenário pode usar várias penalizações, aplicadas **na ordem** declarada no YAML.
- Resultados tabulares em **Parquet**; cada execução preserva sua configuração.
- `comparison`/`inequality` e os **IDS** ficam **fora da lib**. A lib expõe só
  `demographics.interpolate_to_grid` (setor → célula). Não haverá `socioeconomic.py`.
- POIs vêm **exclusivamente do OSM**.

## IDS

Formado **no setor, antes de interpolar** (razão de agregados não comuta com
ponderação por área). Cada eixo é normalizado por município (percentis 2–98, com
clip) e recebe o mesmo peso:

| Eixo | Fórmula | Orientação |
|---|---|---|
| `frac_sem_esgoto` | `1 − (V00309 + V00310) / Σ(V00309…V00316)` | direto |
| `renda` | `log1p(V06004)` | invertido |
| `taxa_analf` | `log1p(1000 · V00901 / (V00900 + V00901))` | direto |

**Esgotamento adequado** = rede geral ou pluvial (`V00309`) + fossa séptica ligada
à rede (`V00310`). Fora: fossa séptica não ligada, fossa rudimentar, vala,
rio/lago/mar, outra, sem banheiro.

**Escolaridade não entra:** o Censo 2022 não a divulga em nível de setor.

O `log1p` no eixo de analfabetismo é necessário: a taxa é assimétrica (mediana de
0,9% em Curitiba, com bolsões acima de 10%) e, sem ele, o mapa satura em preto.

**`V00901` ausente significa zero**, não supressão — um setor sem analfabetos
recebe célula vazia em vez de `0`.

## Penalização térmica (Curitiba)

Função linear: `f(T) = max(1 + k·(T − t0), 1)`.

**Justificativa em três saltos** (cada um declarado na dissertação):

1. **LST → T_ar** (Nascimento et al., 2022, São Paulo): r = 0,81/0,82; MAE 1,2–1,9 °C.
   Sustenta LST como *proxy ordinal* de calor, não conversão.
2. **T_ar → velocidade** (Horiuchi et al., 2018): −7% em "economical speed" de
   23 → 33 °C ⇒ **k = 0,0070/°C**.
3. **Salto assumido:** aplicar `k` de T_ar diretamente sobre LST (equivale a `b = 1`
   na relação LST–T_ar).

**Parâmetros:** `k = 0,0070` (Horiuchi 2018); `t0 = 23 °C` (referência termoneutra de
Horiuchi 2018). O piso 1 impede "bônus" por frio: Horiuchi mede perda no calor, não
ganho no frio. Não há teto — a LST de Curitiba vai de 12,9 a 38,2 °C, faixa em que o
fator chega no máximo a 1,11.

**Curva calibrada:** 25 °C → 1,014 | 30 → 1,049 | 35 → 1,084 | 40 → 1,119.

**Formulação de uso:** a penalização é **índice ordinal de exposição térmica**,
calibrada pela sensibilidade de Horiuchi (2018); a magnitude é indicativa, não
preditiva.

**Limitações a declarar:**
- Nenhum estudo regride velocidade diretamente sobre LST (Qin et al., 2024 usa LST
  para *ciclismo*, não caminhada).
- Nascimento não publica slope, apenas r e MAE; ΔLST construído–rural = 5,8–11,5 °C no
  verão, ou seja, o viés é **espacialmente sistemático** e maior onde o calor importa.
- Horiuchi é população jovem saudável, em câmara; não pedestres reais.

## Área verde (Curitiba)

**Efeito:** o fator final é o **térmico multiplicado por
`FATOR_VERDE = 69/72 = 0,958`** onde há vegetação; sem vegetação (ou pixel `NaN`),
só o fator térmico.

**Derivação:** Jia et al. (2023, Hong Kong, 337 pedestres em campo) mediram que
árvores de rua reduzem o tempo de viagem percebido em até **3 s/100 m**. A 5 km/h,
100 m levam 72 s; com 3 s a menos, 69 s. Logo `69/72 = 0,958`.

**A redução não é condicionada ao calor.** Jia mede o efeito da árvore sobre o
**tempo total**, não sobre o excesso térmico. Aplicá-la só onde há calor seria uma
leitura que o artigo não sustenta. Consequência: a 20 °C, com vegetação, o fator cai
a 0,958 (< 1).

| LST | sem verde | com verde |
|---|---|---|
| 20 °C | 1,000 | 0,958 |
| 30 °C | 1,049 | 1,005 |
| 35 °C | 1,084 | 1,039 |
| 40 °C | 1,119 | 1,072 |

**Camada de entrada:** raster binário de **5 m** com dilatação de 5 m, gerado pelo
ETL. A fonte vetorial (126 mil polígonos, 756 MB) não é usada: as vias passam ao
redor das praças e só 3,4% dos pontos da rede caíam em vegetação. A dilatação modela
a sombra da copa sobre a calçada e eleva a cobertura para **24,1%**.

**O que Jia sustenta** (*E3S Web of Conferences* 396:05013, Hong Kong):
- **Velocidade cai com o estresse térmico** — é a única fonte encontrada que mede
  pedestres reais contra desconforto térmico, não contra temperatura do ar isolada.
- **R² = 0,719** (polinomial), 0,907 (ANN), 0,931 (DNN).
- **Limite:** mede *percepção* térmica (UTCI, temperatura radiante média), não LST.
  Serve como ponte metodológica, não como coeficiente.

## Penalização de Porto Alegre

**Cenários:** `inundacao`, `movimento_massa` e `combinado`. A composição é
multiplicativa, então a interdição do deslizamento domina a penalização de inundação
na mesma aresta.

**Inundação (`porto_alegre_inundacao`): penaliza, não bloqueia.** Água na via atrasa
a caminhada, mas é transponível. A classe `Alto` recebe fator **2,0**, calibrado por
Li et al. (2026, *Acta Polytechnica CTU*): 188 participantes, e a 0,35 m de lâmina
d'água a velocidade caiu **38,6% (homens) e 44,8% (mulheres)**.
Fator = 1/(1 − 0,448) = 1,81 → arredondado para 2,0 (metade da velocidade).
`Médio` (1,5) e `Baixa` (1,1) **não têm fonte** — interpolação arbitrária.

**Movimento de massa (`porto_alegre_movimento_massa`): interdita.** Não há estudo
ligando deslizamento à redução de velocidade de caminhada; a literatura trata o
fenômeno como **bloqueio de via**. O cenário assume o evento **ocorrido** e aplica
`inf` em `Alta` e `Média`; `Baixa` fica livre (é suscetibilidade baixa, não indicação
de ocorrência).

**Impacto medido na rede** (OSMnx, 42.074 nós / 113.860 arestas):

| Classe | Área | Arestas bloqueadas |
|---|---:|---:|
| `Alta` | 8,6 km² | 952 (0,8%) |
| `Média` | 67,8 km² | 10.946 (9,6%) |
| **Alta + Média** | 76,4 km² | 11.898 (10,4%) |

Após o bloqueio restam 4.353 componentes conexas; a maior concentra 36.647 dos
42.074 nós (87%). A rede **não colapsa, mas fragmenta-se** — 13% dos nós ficam
isolados. Isso é um **resultado** (perda de acesso), não uma falha, e deve ser
apresentado junto ao cenário.

**Observação:** o volume de áreas não acompanha o peso no bloqueio. `Média` tem 8× a
área de `Alta` e bloqueia 11× mais arestas, por concentrar malha viária urbana;
`Alta` fica em áreas periféricas de baixa densidade viária.

## Convenção de ausência (regras compostas)

- O dict entregue à `penalty_fn` **sempre tem todas as chaves** de `rule.layers`; a
  ausência vem no **valor** (`None` ou `NaN`).
- Amostragem vetorial devolve `NaN` fora de polígono (não `0.0`).
- ⚠️ `bool(nan)` é `True`. Teste ausência com `pd.isna`, nunca com o valor direto.

## Cenários demonstrativos

Sufixo `_demo_kNN` (`lst_demo_k05`). Usam `k = 0,05` (≈7× a calibração) e existem
para evidenciar o mecanismo da lib; **nunca substituem o resultado principal** e não
têm respaldo empírico.

**Padrão de nomes:** cenário = `<variável>_<propósito>_<parâmetro>`, com o propósito
omitido quando é o principal. Ex.: `lst` (calibrado), `lst_demo_k05` (demonstrativo).
