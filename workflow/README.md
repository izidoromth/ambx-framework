# Execução dos estudos de caso

O workflow usa um único `Snakefile` para todas as cidades e cenários. A cidade e seus cenários são definidos pelo arquivo YAML passado com `--configfile`.

Atualmente existem:

```text
workflow/config/curitiba.yaml
workflow/config/porto_alegre.yaml
```

Cada YAML reúne todos os cenários da respectiva cidade. Não é necessário criar um YAML separado para cada cenário.

## Cenários disponíveis

Curitiba:

```text
typical     referência sem penalização
lst         penalização associada à temperatura da superfície
lst_green   LST com atenuação associada à presença de área verde
```

Porto Alegre:

```text
typical          referência sem penalização
inundacao        penalização por inundação
movimento_massa  penalização por movimento de massa
combinado        inundação e movimento de massa
```

O cenário `typical` é sempre calculado como referência. Os demais cenários são comparados a ele.

## Preparar o ambiente

Execute os comandos a partir da raiz do repositório:

```bash
cd ~/Documentos/mestrado/ambx-framework
source .venv/bin/activate
snakemake --version
```

O arquivo `workflow/config/base.yaml` é uma configuração vazia usada internamente pelo `Snakefile`. O arquivo da cidade deve ser informado explicitamente com `--configfile`.

Antes de executar Curitiba com `lst_green`, confirme que existe:

```text
data/processed/curitiba/area_verde_2019.geoparquet
```

### Gerar o dado de área verde

O arquivo é produzido pela ETL a partir da camada de Área Verde 2019 disponibilizada pelo IPPUC. A partir da raiz do repositório, execute:

```bash
source .venv/bin/activate
python scripts/etl/download_area_verde_curitiba.py
```

O script baixa o ZIP original, extrai o Shapefile e salva o produto processado em:

```text
data/processed/curitiba/area_verde_2019.geoparquet
```

Também é gerado um arquivo de metadados:

```text
data/processed/curitiba/area_verde_2019.json
```

O ZIP baixado e os arquivos extraídos ficam no cache local `scripts/etl/cache_area_verde/`. Esse cache pode ser reutilizado em execuções posteriores. Depois da geração, o cenário `lst_green` pode ser executado normalmente.

## Verificar uma execução

Use `--dry-run` para verificar as regras sem gerar resultados:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/curitiba.yaml \
  --cores 8 \
  --dry-run
```

Para Porto Alegre, substitua `curitiba.yaml` por `porto_alegre.yaml`.

## Executar todos os cenários de uma cidade

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/curitiba.yaml \
  --cores 8
```

Para Porto Alegre:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/porto_alegre.yaml \
  --cores 8
```

O Snakemake calcula apenas os produtos ausentes ou desatualizados. Por isso, uma segunda execução normalmente é mais rápida.

## Executar apenas um cenário

É possível solicitar diretamente um produto final. Por exemplo, para o cenário combinado de Porto Alegre:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/porto_alegre.yaml \
  --cores 8 \
  results/porto_alegre/matrices/matrix_combinado.parquet
```

O workflow executará automaticamente as etapas necessárias, incluindo a matriz típica usada como referência.

## Estrutura das configurações

O cenário típico não possui penalizações:

```yaml
scenarios:
  typical: {}
```

Cada cenário não típico pode declarar uma ou mais regras:

```yaml
scenarios:
  lst:
    penalties:
      - name: lst
        function: curitiba_lst
        input: data/raw/curitiba/LST_Anual_2026_221077_Mediana.tif
        input_type: raster
```

As funções específicas ficam em `workflow/rules/`. A ordem das regras no YAML é a ordem em que as penalizações são aplicadas.

## Produtos gerados

Os resultados são gravados no diretório definido por `output_dir` no YAML:

```text
results/<cidade>/
├── prepared/                         dados preparados e rede
├── matrices/matrix_typical.parquet   matriz de referência
├── matrices/matrix_<cenario>.parquet  matriz penalizada
├── indicators_<cenario>.json
├── comparison_<cenario>.parquet
└── figures/
    ├── map_typical.png
    ├── comparison_<cenario>.png
    └── delta_time_<cenario>_histogram.png
```

Os nomes `<cidade>` e `<cenario>` são substituídos pelos valores definidos no YAML.

## Ver a DAG do workflow

Em texto:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/porto_alegre.yaml \
  --cores 8 \
  --dag
```

Como imagem, com Graphviz instalado:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/porto_alegre.yaml \
  --cores 8 \
  --dag | dot -Tpng > workflow/dag.png
```

## Retomar ou forçar uma execução

Após uma falha:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/<config>.yaml \
  --cores 8 \
  --rerun-incomplete
```

Para forçar uma regra:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/<config>.yaml \
  --cores 8 \
  --forcerun <regra>
```

Substitua `<config>` por `curitiba` ou `porto_alegre`.

## Limpeza e logs

O Snakemake não remove automaticamente arquivos antigos que deixaram de ser declarados. Se um cenário for removido ou renomeado, confira e remova manualmente os produtos antigos em `results/`.

Não remova `.snakemake/`: essa pasta contém o estado e os logs usados pelo workflow.

Os logs ficam em:

```text
.snakemake/log/
```
