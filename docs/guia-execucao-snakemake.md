# Guia de execução do Snakemake

Este documento descreve como executar o workflow de Curitiba/LST definido em `workflow/Snakefile`.

## 1. Ir para a raiz do projeto

Os comandos devem ser executados na raiz do repositório:

```bash
cd ~/Documentos/mestrado/ambx-framework
```

Não execute usando `workflow/Snakefile` depois de entrar na pasta `workflow/`, pois o caminho passará a ser interpretado como `workflow/workflow/Snakefile`.

## 2. Ativar o ambiente virtual

```bash
source .venv/bin/activate
```

Verifique a instalação:

```bash
which snakemake
snakemake --version
```

## 3. Conferir o plano sem executar

```bash
snakemake -s workflow/Snakefile --cores 8 --dry-run
```

O `--dry-run` apenas constrói o grafo de dependências. Ele mostra as regras que seriam executadas, mas não baixa dados, não faz roteamento e não cria resultados.

## 4. Executar o workflow completo

```bash
snakemake -s workflow/Snakefile --cores 8
```

O workflow produz resultados em `results/curitiba_lst/`:

```text
results/curitiba_lst/
├── prepared/
├── matrices/
│   ├── matrix_typical.parquet
│   └── matrix_conditioned.parquet
├── indicators.json
├── comparison.parquet
└── figures/
    └── delta_time_histogram.png
```

O número de núcleos pode ser alterado:

```bash
snakemake -s workflow/Snakefile --cores 4
```

## 5. Executar apenas uma etapa

Para gerar somente a matriz típica e suas dependências:

```bash
snakemake -s workflow/Snakefile --cores 8 \
  results/curitiba_lst/matrices/matrix_typical.parquet
```

Para executar até uma regra específica:

```bash
snakemake -s workflow/Snakefile --cores 8 --until route_typical
```

## 6. Retomar uma execução interrompida

Após resolver o problema que causou a falha, execute novamente:

```bash
snakemake -s workflow/Snakefile --cores 8 --rerun-incomplete
```

O Snakemake reutiliza os arquivos de saída válidos e refaz apenas as etapas necessárias.

## 7. Forçar uma etapa

Para refazer uma regra mesmo quando seus arquivos de saída existem:

```bash
snakemake -s workflow/Snakefile --cores 8 --forcerun prepare
```

Essa opção refaz a preparação da malha, POIs, rede e snapping.

## 8. Configuração

Os parâmetros estão em:

```text
workflow/config/curitiba_lst.yaml
```

Entre os parâmetros configuráveis estão:

- localidade;
- formato e tamanho da malha;
- buffer dos POIs;
- tipo de rede;
- velocidade de caminhada;
- distância máxima de snapping;
- número de POIs vizinhos;
- número de processos;
- caminho do raster LST;
- diretório de resultados.

## 9. Logs

Os logs ficam em:

```text
.snakemake/log/
```

Em caso de falha, o caminho do log correspondente é exibido no terminal.

## 10. Grafo do workflow

Com Graphviz instalado, o grafo pode ser exportado assim:

```bash
snakemake -s workflow/Snakefile --dag | dot -Tpng > workflow/dag.png
```

O comando `dot` faz parte do pacote Graphviz. Em Ubuntu/Debian, instale-o com:

```bash
sudo apt update
sudo apt install graphviz
```

Confirme a instalação:

```bash
dot -V
```

Depois, estando na raiz do repositório, gere a imagem:

```bash
snakemake -s workflow/Snakefile --dag | dot -Tpng > workflow/dag.png
```

O PNG será salvo em:

```text
workflow/dag.png
```

Para abrir no Linux:

```bash
xdg-open workflow/dag.png
```

Sem Graphviz, é possível consultar a DAG em formato textual:

```bash
snakemake -s workflow/Snakefile --dag
```

Execute os comandos a partir da raiz do projeto. Dentro da pasta `workflow/`, o caminho `workflow/Snakefile` apontaria incorretamente para `workflow/workflow/Snakefile`.

O fluxo atual é:

```text
prepare
 ├── route_typical ───────┐
 └── route_conditioned ──┤
                          ├── indicators
                          └── comparison ── figures
```

## 11. Execução com Docker

Docker ainda não é necessário para a execução local atual. Quando uma imagem for configurada, a execução deverá especificar a imagem e sua versão para preservar a reprodutibilidade do ambiente.
