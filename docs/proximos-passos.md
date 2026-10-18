# Próximos Passos — ambx

## Implementação

- Rodar `lst_green_composite` de novo: o +2,68% medido usou a formulação antiga
  do verde (`FATOR_VERDE = 0,958` atua sobre o tempo total).
- Conectar o Censo à malha: **IVS** por célula e habilitar o F15 ponderado pela
  população na regra `indicators`. Ver `decisoes.md` para os 4 eixos.
- Análise socioespacial: significância, regressão, LISA, agrupamento — como
  scripts/notebooks, não na lib.
- Definir `run_config`/metadados de cada execução.
- Registrar proveniência do raster LST (produto, sensor, data, resolução).
- Auditar riscos técnicos de `avaliacao-execucao-qualificacao.md` §5:
  `comparison` não conta pares perdidos; `routing.py` sem guard `__main__`;
  aresta colinear à borda em `_segment_factors`.

## Escrita

- `3.architecture`: descrever a lib como **conceito**, com o módulo entre
  parênteses. Remover o tom de "recomenda-se".
- `4.penalization`: descrever o **mecanismo** (composição multiplicativa,
  contínuo vs. discreto, interdição por `inf`, regras compostas, agregação),
  sem os valores calibrados — esses vão para a seção 5.
- `5.case_studies`: converter o futuro em presente, justificar a escolha dos
  dois municípios e apresentar a **calibração de cada caso** com a fonte de
  cada valor (Horiuchi, Nascimento, Li, Jia — ver `decisoes.md`).
- `6.results`: remover "Resultados Esperados" e reescrever com os cenários de
  Curitiba e Porto Alegre. O SBBd **não entra** aqui — será apêndice.
- `7.discussion`: LST ≠ T_ar; velocidade calibrada em câmara; premissa de
  manutenção do deslocamento a pé.
- `8.conclusion`: a preencher.
- Revisar o tempo verbal de `1.introduction` (presente impessoal).
