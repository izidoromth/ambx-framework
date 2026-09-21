# Dados processados

Esta pasta contém produtos derivados dos dados brutos, gerados pelos ETLs ou
por transformações necessárias ao uso analítico do framework `ambx`.

## Estrutura atual

```text
data/processed/
├── README.md
├── censo_2022/
│   ├── censo_2022.geoparquet
│   └── metadados.json
└── curitiba/
    ├── area_verde_2019.geoparquet
    └── area_verde_2019.json
```

## Produtos

### Censo 2022

`censo_2022/censo_2022.geoparquet` é o produto consolidado do ETL do Censo,
com geometrias dos setores e variáveis dos temas selecionados.

```bash
python scripts/etl/download_censo_2022.py
```

### Área Verde de Curitiba — 2019

`curitiba/area_verde_2019.geoparquet` é a conversão para GeoParquet da camada
`AREA_VERDE_2019_SIRGAS` disponibilizada pelo IPPUC. A camada já corresponde
ao município de Curitiba e não recebe recorte adicional no ETL.

```bash
python scripts/etl/download_area_verde_curitiba.py
```

Os arquivos brutos ficam em `data/raw/`, os caches em `scripts/etl/cache_*` e
as saídas do Snakemake em `results/`.
