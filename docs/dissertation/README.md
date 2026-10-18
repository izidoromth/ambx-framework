# Texto da dissertação

Versão 1 em construção. A qualificação aprovada está em `../qualifying/` e
serve de base — não a edite.

## Estrutura das seções

| # | Arquivo | Seção | O que deve trazer |
|---|---|---|---|
| 1 | `1.introduction.tex` | Introdução | Mobilidade ativa e cidade de 15 min; acessibilidade não uniforme; lacuna (perturbações climáticas); objetivo, contribuições e estrutura. |
| 2 | `2.fundamentals.tex` | Fundamentação | Acessibilidade (Hansen, Geurs \& van Wee); PTh, Gini, F15; 15-minute city; desigualdade socioespacial; clima e velocidade de caminhada. |
| 3 | `3.architecture.tex` | Arquitetura do Framework | Malha (`grid`), POIs (`pois`), rede (`network`), roteamento (`routing`), indicadores (`indicators`), dados socioeconômicos (`demographics`). Conceito primeiro, módulo entre parênteses. |
| 4 | `4.penalization.tex` | O Mecanismo de Penalização e Atenuação | Composição `W_cond = W_base × Πf_i`; contínuo vs. discreto; interdição por `inf`; leitura no mesmo ponto; agregação; recálculo do grafo. **Sem os valores calibrados.** |
| 5 | `5.case_studies.tex` | Estudos de Caso | Por que Curitiba e PoA; fontes de dados; **e a calibração de cada caso**, com a fonte de cada valor. |
| 6 | `6.results.tex` | Resultados | Cenários de Curitiba e PoA, comparações, mapas e indicadores. Números reais. |
| 7 | `7.discussion.tex` | Discussão e Limitações | LST ≠ T_ar; calibração em câmara; premissa de manutenção do deslocamento a pé; indicadores medem potencial. |
| 8 | `8.conclusion.tex` | Conclusão | Retomada do objetivo, contribuições e trabalhos futuros. |

## Situação

| Arquivo | Situação |
|---|---|
| `1.introduction.tex` | herdado; revisar tempo verbal |
| `2.fundamentals.tex` | herdado |
| `3.architecture.tex` | herdado; descrever a lib em conceito |
| `4.penalization.tex` | herdado; substituir o texto genérico pelo mecanismo |
| `5.case_studies.tex` | herdado; converter futuro em presente e incluir a calibração |
| `6.results.tex` | herdado; remover "Resultados Esperados" |
| `7.discussion.tex` | placeholder com tópicos |
| `8.conclusion.tex` | placeholder |

O artigo do SBBd **não entra** nos resultados — será apêndice, a decidir.

## Compilação

Ver `../README.md`.

## Dados e resultados

Os resultados vêm de `results/<cidade>/`, gerados pelo workflow em `workflow/`
(ver `workflow/README.md`). As decisões de calibração estão em
`../decisoes.md`.
