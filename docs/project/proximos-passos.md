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
- [x] `3.3.validation`
- [ ] `5.case_studies`
- [ ] `6.results`
- [ ] `7.discussion`
- [ ] `8.conclusion`

Ao traduzir cada seção, resolver de passagem os itens de conteúdo já mapeados:

- [ ] **Enquadramento em computação aplicada / ciência de dados** — em toda seção, demonstrar o caráter computacional (modelo de dados, algoritmo, pipeline reprodutível, quantificação) sem declarar isso explicitamente. Ver `diretrizes-redacao.md`.
- [ ] `5.case_studies`: converter o futuro em presente, justificar a escolha dos
  dois municípios e apresentar a **calibração de cada caso** com a fonte de
  cada valor (Horiuchi, Nascimento, Li, Jia — ver `decisoes.md`).
- `6.results`: remover "Resultados Esperados" e reescrever com os cenários de
  Curitiba e Porto Alegre. O SBBd **não entra** aqui — será apêndice.
- `7.discussion`: LST ≠ T_ar; velocidade calibrada em câmara; premissa de
  manutenção do deslocamento a pé.

Revisão pendente:

- [ ] `3.3.validation`: revisar o desenho de validação — o encadeamento com os
      estudos de caso ainda não foi validado pelo orientador.

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

