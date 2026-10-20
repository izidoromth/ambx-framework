# Análises socioespaciais

## Índices de Desigualdades Socioespaciais

O script `compute_ids.py` calcula os índices por célula e a população
interpolada do Censo 2022. Ele gera:

- `ids`: renda, alfabetização e desigualdade racial territorial;
- `populacao`: população interpolada para cada célula, para uso no F15.

### Execução

A partir da raiz do repositório:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/analysis/compute_ids.py \
  --city curitiba \
  --grid results/curitiba/prepared/grid.parquet \
  --output results/curitiba/prepared/ids.parquet
```

Por padrão, a saída é uma tabela Parquet sem geometria. Para gerar uma camada
espacial compatível com o QGIS, acrescente `--format geoparquet`:

```bash
python scripts/analysis/compute_ids.py \
  --city curitiba \
  --grid results/curitiba/prepared/grid.parquet \
  --output results/curitiba/prepared/ids_geoparquet.parquet \
  --format geoparquet
```

Para Porto Alegre:

```bash
PYTHONPATH=scripts .venv/bin/python scripts/analysis/compute_ids.py \
  --city porto_alegre \
  --grid results/porto_alegre/prepared/grid.parquet \
  --output results/porto_alegre/prepared/ids.parquet
```

O resultado é um GeoParquet com a geometria das células, pronto para abrir no
QGIS. O arquivo de entrada do Censo é
`data/processed/censo_2022/censo_2022.geoparquet`; ele pode ser substituído
com `--census` quando necessário.
