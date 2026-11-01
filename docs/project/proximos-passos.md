# Próximos Passos — ambx

> **Foco atual: fechamento do artigo final.** Todas as seções estão redigidas em
> inglês. O que resta é revisão de texto, pendências de figura e a dívida técnica
> parada. Tudo abaixo da seção "Dívida técnica (adiada)" fica parado até a
> submissão.

## Redação do artigo final

Tradução para o inglês, seção por seção, com aprovação a cada etapa. Ordem de trabalho:

- [x] `1.introduction`
- [x] `2.fundamentals`
- [x] `3.methodology` (abertura)
- [x] `3.1.architecture`
- [x] `3.2.penalization`
- [x] `3.3.applicability`
- [x] `4.case_studies`
- [x] `5.results` (6 subseções em `sections/5.subsections/`)
- [x] `6.discussion`
- [x] `7.conclusion`

Ao traduzir cada seção, resolver de passagem os itens de conteúdo já mapeados:

- [ ] **Enquadramento em computação aplicada / ciência de dados** — em toda seção, demonstrar o caráter computacional (modelo de dados, algoritmo, pipeline reprodutível, quantificação) sem declarar isso explicitamente. Ver `diretrizes-redacao.md`.
- [x] `5.results`: reescrita com os cenários de Curitiba e Porto Alegre. O SBBd não entra na seção — será apêndice.
- [x] `5.results`: distribuição do delta apresentada, não só os agregados.
- [x] `6.discussion`: LST ≠ T_ar; velocidade calibrada em câmara; premissa de manutenção do deslocamento a pé.
- [x] `6.discussion`: classe de risco do SGB-CPRM declarada como hipótese de aplicabilidade.
- [x] `6/7`: deslizamento interrompe apenas Alta e Média; classe Baixa livre por decisão conservadora.

Pendências de texto (revisão do artigo):

- [ ] Títulos de figuras e tabelas ainda em português; traduzir junto com os
      scripts que os geram (`workflow/scripts/ambx_stage.py`,
      `scripts/analysis/*`), para que a regeneração não reintroduza o português.
- [ ] `1.introduction`: confirmar os números do primeiro parágrafo (70\%, 1\%,
      62\%) contra `BRAND2021102764`.
- [ ] `6.discussion`: decidir se a regressão passa a controlar por densidade
      populacional. Hoje não controla — apontado em revisão externa.
- [ ] `6.discussion`: explicar a direção esperada do viés ao aplicar o
      coeficiente de Horiuchi (adultos jovens saudáveis) à população geral.
- [ ] `6.discussion`: justificar o recorte de evento único no cenário de
      deslizamento.
- [ ] `5.6.lisa`: os painéis de Curitiba mostram apenas `thermal` e
      `thermal+green`; decidir se os cenários `demo` entram como apêndice.

Revisão pendente:

- [ ] `3.3.applicability`: o desenho de aplicabilidade ainda não foi validado
      pelo orientador.
- [ ] `3.3.applicability`: a representação mista (raster + vetor) é suportada
      mas não exercitada por nenhum cenário. Rodar um cenário que combine as
      duas, se houver tempo.
- [ ] Renomear os cenários no YAML e no Snakefile para coincidir com o texto
      (`inundacao` → `flood`, `movimento_massa` → `landslide`, `combinado` →
      `flood_landslide`, `lst*` → `thermal*`) e reprocessar os resultados.
      Hoje o texto usa os nomes em inglês e os artefatos em português, o que
      exige tradução manual em toda tabela.
- [ ] Permitir que a lib receba POIs de camadas GIS independentes, para corrigir
      a assimetria de cobertura do OpenStreetMap entre as cidades.
- [ ] `scripts/analysis/summarize_indicators.py`: `comparison_basis` e as
      colunas `_shared` de `deltas.csv` foram criadas para comparar cenários
      de Porto Alegre com universos de células diferentes. Revisar se a
      nomenclatura comunica isso sem consultar o código.

Comentários da banca a endereçar antes da submissão:

- [x] Formalizar os requisitos para aplicar o framework em outras cidades (Seção 3.3).
- [x] Justificar os parâmetros das funções de penalização, com exemplos dos
      estudos de caso (Seção 4).
- [ ] Discutir a granularidade temporal das análises (dias e horários).
- [x] Explicar a escolha e o impacto da distância de 200 m (Seções 3.1 e 3.3).
- [ ] Decidir sobre o mapa ou histograma dos eixos do SDI. A distribuição do
      eixo de analfabetismo foi citada em versão anterior da Seção 5.5 e
      removida por falta de suporte visual; o dado nunca foi apresentado.

## Dívida técnica (adiada — fazer por último)

- `except Exception` em `access_loss_maps.py`, `delta_time_maps.py`,
  `lisa_ids_delta.py` e `ambx_stage.py` (5 ocorrências, `BLE001`): captura
  ampla demais, pode engolir falhas de projeção.
- `lisa_ids_delta.py:74`: variável `fig` desempacotada e não usada (`RUF059`).
- 7 avisos `I001` (imports desordenados) em `scripts/analysis/` e
  `workflow/scripts/ambx_stage.py`: `ruff check --fix` resolve.
- Nenhum teste cobre os 5 scripts de análise adicionados ao workflow.

## Implementação (pausada)

- Definir `run_config`/metadados de cada execução.
- Registrar proveniência do raster LST (produto, sensor, data, resolução).
- Auditar riscos técnicos de `avaliacao-execucao-qualificacao.md` §5:
  `comparison` não conta pares perdidos; `routing.py` sem guard `__main__`;
  aresta colinear à borda em `_segment_factors`.

