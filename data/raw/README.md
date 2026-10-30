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

Ambos os arquivos vêm do GeoPOA, o portal de dados geográficos da Prefeitura de
Porto Alegre, pelo **Catálogo de Downloads**:

1. https://gis-smamus.portoalegre.rs.gov.br/portal/apps/experiencebuilder/experience/?page=CAT%C3%81LOGO-DE-DOWNLOAD
2. Buscar por "inundações" ou "movimento de massa"
3. Exportar como GeoJSON

O produtor dos dados é o Serviço Geológico do Brasil (SGB-CPRM), que os publica
como *Setorização de áreas de risco geológico: Porto Alegre, Rio Grande do Sul*
(BELLETTINI et al., 2022, `https://rigeo.sgb.gov.br/handle/doc/23505`). O campo
`fonte` de cada feição confirma a origem: modelagem da CPRM validada em campo
entre 2012 e 2014.

Os arquivos são de **risco geológico**, não de suscetibilidade: o SGB classifica
o grau de risco, que incorpora exposição e vulnerabilidade, e não apenas a
propensão do terreno ao fenômeno.

### `inundacao_cprm.geojson`

| Campo | Descrição |
|-------|-----------|
| **Fonte** | SGB-CPRM, distribuído pelo GeoPOA (PMPA) |
| **Camada no catálogo** | "Áreas com Risco a Inundações - CPRM" |
| **Tema** | Risco de inundação |
| **Ano** | 2022 (publicação); campo validado 2012–2014 |
| **CRS** | EPSG:4326 (reprojetado na exportação) |
| **Feições** | 2216 polígonos |
| **Coluna relevante** | `classe` — `"Alto"`, `"Médio"`, `"Baixa"` |
| **Profundidade** | não disponível no dado |
| **Uso no ambx** | Penalização de arestas da rede por risco de inundação |

### `movimento_massa_cprm.geojson`

| Campo | Descrição |
|-------|-----------|
| **Fonte** | SGB-CPRM, distribuído pelo GeoPOA (PMPA) |
| **Camada no catálogo** | "Áreas com Risco a Movimento de Massa - CPRM" |
| **Tema** | Risco de movimento de massa (escorregamento) |
| **Ano** | 2022 (publicação); campo validado 2012–2014 |
| **CRS** | EPSG:4326 (reprojetado na exportação) |
| **Feições** | 305 polígonos |
| **Coluna relevante** | `classe` — `"Alta"`, `"Média"`, `"Baixa"` |
| **Uso no ambx** | Interdição de arestas nas classes Alta e Média |

Os scripts de aquisição e transformação ficam em `scripts/etl/`. Os caminhos
dos produtos gerados devem ser consultados em `data/processed/README.md`.
