# Próximos Passos — ambx

> **Foco atual: redação do artigo final.** Tudo abaixo da seção "Dívida técnica
> (adiada)" fica parado até o artigo estar submetido.

## Redação do artigo final

Tradução para o inglês, seção por seção, com aprovação a cada etapa. Ordem de trabalho:

- [x] `1.introduction`
- [x] `2.fundamentals`
- [x] `3.methodology` (abertura)
- [x] `3.1.architecture`
- [x] `3.2.penalization`
- [x] `3.3.applicability`
- [x] `4.case_studies`
- [ ] `5.results`
- [ ] `6.discussion`
- [ ] `7.conclusion`

Ao traduzir cada seção, resolver de passagem os itens de conteúdo já mapeados:

- [ ] **Enquadramento em computação aplicada / ciência de dados** — em toda seção, demonstrar o caráter computacional (modelo de dados, algoritmo, pipeline reprodutível, quantificação) sem declarar isso explicitamente. Ver `diretrizes-redacao.md`.
- `5.results`: remover "Resultados Esperados" e reescrever com os cenários de
  Curitiba e Porto Alegre. O SBBd **não entra** aqui — será apêndice.
- `5.results`: o cenário térmico calibrado move o F15 de Curitiba em ~1 p.p.,
  contra ~13 p.p. do demonstrativo. A leitura correta é que a penalização
  calibrada tem efeito agregado pequeno e concentrado no espaço; mostrar a
  distribuição do delta, não só os agregados.
- `6.discussion`: LST ≠ T_ar; velocidade calibrada em câmara; premissa de
  manutenção do deslocamento a pé.
- `6.discussion`: a classe de risco do SGB-CPRM foi lida como equivalente de
  profundidade de lâmina d'água. Declarar como hipótese de aplicabilidade.
- `6/7`: o deslizamento interrompe apenas Alta e Média; a classe Baixa fica
  livre por decisão conservadora, não por ausência de ocorrência no dado.

Revisão pendente:

- [ ] `3.3.applicability`: o desenho de aplicabilidade ainda não foi validado
      pelo orientador.
- [ ] `3.3.applicability`: a representação mista (raster + vetor) é suportada
      mas não exercitada por nenhum cenário. Rodar um cenário que combine as
      duas, se houver tempo.
- [ ] Renomear os cenários no YAML e no Snakefile para coincidir com o texto
      (`inundacao` → `flood`, `movimento_massa` → `landslide`, `combinado` →
      `flood_landslide`, `lst*` → `thermal*`) e reprocessar os resultados.
- [ ] Permitir que a lib receba POIs de camadas GIS independentes, para corrigir
      a assimetria de cobertura do OpenStreetMap entre as cidades.

Comentários da banca a endereçar durante a tradução:

- [ ] Formalizar os requisitos para aplicar o framework em outras cidades.
- [ ] Justificar os parâmetros das funções de penalização, com exemplos dos
      estudos de caso.
- [ ] Discutir a granularidade temporal das análises (dias e horários).
- [ ] Explicar a escolha e o impacto da distância de 200 m.

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

