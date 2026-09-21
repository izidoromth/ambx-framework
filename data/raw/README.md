# Dados brutos (raw data)

Esta pasta contém arquivos originais ou recebidos diretamente das fontes de
dados. Ela não deve conter produtos consolidados pelos ETLs. Os produtos
derivados ficam em `data/processed/`.

## Estrutura

```
data/raw/
├── README.md              ← este arquivo
├── curitiba/
│   └── LST_Anual_2026_221077_Mediana.tif
└── porto_alegre/
    ├── inundacao_cprm.geojson
    └── movimento_massa_cprm.geojson
```

---

## Porto Alegre

### `inundacao_cprm.geojson`

| Campo | Descrição |
|-------|-----------|
| **Fonte** | CPRM — Serviço Geológico do Brasil |
| **Tema** | Suscetibilidade a inundações |
| **Ano** | — |
| **CRS** | EPSG:4674 (SIRGAS 2000) |
| **Feições** | 2216 polígonos |
| **Coluna relevante** | `classe` — `"Alto"`, `"Médio"`, `"Baixa"` |
| **Uso no ambx** | Penalização de arestas da rede por risco de inundação |

### `movimento_massa_cprm.geojson`

| Campo | Descrição |
|-------|-----------|
| **Fonte** | CPRM — Serviço Geológico do Brasil |
| **Tema** | Suscetibilidade a movimentos de massa (escorregamentos) |
| **Ano** | — |
| **CRS** | EPSG:4674 (SIRGAS 2000) |
| **Feições** | 305 polígonos |
| **Coluna relevante** | `classe` — `"Alta"`, `"Média"`, `"Baixa"` |
| **Uso no ambx** | Penalização de arestas da rede por risco geológico |

> **Nota:** Ambos os arquivos foram obtidos do portal de dados geográficos da
> Prefeitura de Porto Alegre (GEOPOA).

Os scripts de aquisição e transformação ficam em `scripts/etl/`. Os caminhos
dos produtos gerados devem ser consultados em `data/processed/README.md`.
