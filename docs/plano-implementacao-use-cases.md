# Plano de execução dos casos de uso

## Objetivo

Concluir e comparar os casos de uso de Curitiba e Porto Alegre, cada um com cenário típico e condicionado. A análise socioeconômica será feita somente após essa etapa.

## O que já foi feito

- biblioteca `ambx` com o mecanismo de penalização;
- workflow Snakemake inicial;
- configuração e execução do cenário típico de Porto Alegre;
- cenários típico e condicionado de Curitiba;
- cálculo de matrizes, PTh, Gini e comparações;
- ETL do Censo 2022, com saída em GeoParquet.

## Próxima sequência de trabalho

### 1. Criar e revisar as configurações YAML

Organizar uma configuração para cada cidade/caso de uso, contendo os dois cenários:

```text
curitiba.yaml
porto_alegre.yaml
```

Cada YAML deve definir as entradas comuns da cidade e configurar separadamente os cenários `typical` e `conditioned`. O cenário típico não declara penalizações; o condicionado declara sua lista ordenada:

```yaml
city: curitiba

scenarios:
  typical: {}
  conditioned:
    penalties:
  - name: lst
    function: curitiba_lst
    layer: LST_Anual_2026_221077_Mediana
    input: data/raw/curitiba/LST_Anual_2026_221077_Mediana.tif
    input_type: raster
```

Essa organização evita repetir entradas compartilhadas e mantém a comparação entre os cenários no mesmo contexto experimental. As funções específicas permanecem em Python; o YAML apenas seleciona a função e seus parâmetros.

Também deve ser definido o registro de `run_config` e dos metadados de cada execução.

### 2. Rodar os quatro cenários

Executar cada YAML pelo mesmo `Snakefile`, sem duplicar regras do workflow. O cenário condicionado de Porto Alegre será a principal implementação pendente desta fase.

### 3. Validar e comparar os resultados

Verificar se os quatro cenários produzem saídas consistentes:

- mesmo esquema de dados;
- mesmas categorias e unidades;
- matrizes e indicadores válidos;
- mapas com escalas comparáveis;
- comparação típico × condicionado por cidade;
- registro da configuração e dos dados utilizados.

Ao final desta etapa, os dois casos de uso estarão reproduzíveis e documentados.

## Etapa posterior — Análise socioeconômica

Somente depois da validação dos quatro cenários:

1. consumir o GeoParquet censitário já produzido pelo ETL;
2. transferir população e variáveis socioeconômicas para a malha;
3. calcular F15 ponderado pela população;
4. construir a tabela analítica com PTh típico, condicionado e diferença;
5. produzir estatísticas descritivas, regressões e análises espaciais;
6. gerar as tabelas, mapas e resultados finais da dissertação.

## Decisões já estabelecidas

- o Snakemake será o orquestrador do workflow;
- as penalizações específicas serão funções Python;
- um cenário poderá usar várias penalizações em sequência;
- a ordem das penalizações será declarada no YAML;
- o YAML selecionará funções, camadas e parâmetros;
- os resultados tabulares serão preferencialmente armazenados em Parquet;
- cada execução deverá preservar sua configuração e metadados.

## Critério de conclusão

O plano estará concluído quando os quatro cenários puderem ser executados pelo mesmo workflow, a partir de seus YAMLs, com resultados comparáveis e reproduzíveis. A etapa socioeconômica começa apenas depois desse marco.
