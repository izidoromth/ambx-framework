# Próximos Passos — ambx

## Implementação

- Análise socioespacial em `notebooks/analysis/`:
  - Mapas de tempo de acesso — **feito**
  - Mapa IDS por eixo — **feito**
  - mapa da degradação por inacessibilidade de POIs;
  - mapa do delta de tempo entre cenários;
  - agrupamento das células por tempo de acesso e delta;
  - regressão entre degradação e condições socioespaciais.
- Definir `run_config`/metadados de cada execução.
- Registrar proveniência do raster LST (produto, sensor, data, resolução).
- Auditar riscos técnicos de `avaliacao-execucao-qualificacao.md` §5:
  `comparison` não conta pares perdidos; `routing.py` sem guard `__main__`;
  aresta colinear à borda em `_segment_factors`.

## Escrita

- passar o texto da dissertação para inglês.
- revisar os comentários da banca.
- `3.1.archictecture`: descrever a lib como **conceito**, com o módulo entre
  parênteses. Remover o tom de "recomenda-se".
- `3.2.penalization`: descrever o **mecanismo** (composição multiplicativa,
  contínuo vs. discreto, interdição por `inf`, regras compostas, agregação),
  sem os valores calibrados — esses vão para a seção 5.
- `3.3.validation` desenvolver a subseção
- `5.case_studies`: converter o futuro em presente, justificar a escolha dos
  dois municípios e apresentar a **calibração de cada caso** com a fonte de
  cada valor (Horiuchi, Nascimento, Li, Jia — ver `decisoes.md`).
- Formalizar os requisitos para aplicar o framework em outras cidades. (Banca)
- Incorporar à dissertação a justificativa dos parâmetros das funções de penalização, com exemplos específicos dos estudos de caso. (Banca)
- Discutir a granularidade temporal das análises (dias e horários). (Banca)
- Explicar a escolha e o impacto da distância de 200 m. (Banca)
- `6.results`: remover "Resultados Esperados" e reescrever com os cenários de
  Curitiba e Porto Alegre. O SBBd **não entra** aqui — será apêndice.
- `7.discussion`: LST ≠ T_ar; velocidade calibrada em câmara; premissa de
  manutenção do deslocamento a pé.
- `8.conclusion`: a preencher.
- Revisar o tempo verbal de `1.introduction` (presente impessoal).