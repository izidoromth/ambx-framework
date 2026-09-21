# Execução dos casos de uso

O workflow é generalizado: todas as cidades e cenários usam o mesmo `Snakefile`. Para executar um caso de uso, basta escolher o YAML correspondente.

Atualmente existem:

```text
workflow/config/curitiba.yaml
workflow/config/porto_alegre.yaml
```

Cada YAML representa uma cidade e configura seus cenários `typical` e `conditioned`. O cenário típico é a referência sem penalizações. O condicionado aplica a lista de penalizações declarada no próprio YAML.

## Preparar o ambiente

Execute os comandos a partir da raiz do repositório:

```bash
cd ~/Documentos/mestrado/ambx-framework
source .venv/bin/activate
snakemake --version
```

## Verificar uma execução

Substitua `<config>` pelo arquivo da cidade desejada:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/<config> \
  --cores 8 \
  --dry-run
```

Exemplo para Curitiba:

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/curitiba.yaml \
  --cores 8 \
  --dry-run
```

O `dry-run` mostra as regras que seriam executadas, sem gerar os resultados.

## Executar um caso de uso

```bash
snakemake -s workflow/Snakefile \
  --configfile workflow/config/<config> \
  --cores 8
```

Exemplos:

```bash
snakemake -s workflow/Snakefile --configfile workflow/config/curitiba.yaml --cores 8
snakemake -s workflow/Snakefile --configfile workflow/config/porto_alegre.yaml --cores 8
```

O Snakemake identifica automaticamente as etapas necessárias a partir da configuração e dos arquivos já existentes. Se uma saída estiver atualizada, ela não será recalculada.

## Estrutura das configurações

O cenário típico não possui penalizações:

```yaml
scenarios:
  typical: {}
```

O cenário condicionado pode declarar uma ou mais regras:

```yaml
scenarios:
  conditioned:
    enabled: true
    penalties:
      - name: lst
        function: curitiba_lst
        input: data/raw/curitiba/LST_Anual_2026_221077_Mediana.tif
        input_type: raster
```

As funções específicas são implementadas em `workflow/rules/`. A ordem das regras no YAML é a ordem em que as penalizações são aplicadas.

## Produtos

Os resultados são gravados no diretório definido por `output_dir` no YAML, normalmente contendo:

```text
prepared/       dados preparados e rede
matrices/       matrizes de tempo
comparison.parquet
indicators.json
figures/        mapas e gráficos
```

## Comandos úteis

Retomar uma execução após falha:

```bash
snakemake -s workflow/Snakefile --configfile workflow/config/<config> --cores 8 --rerun-incomplete
```

Forçar a execução de uma regra:

```bash
snakemake -s workflow/Snakefile --configfile workflow/config/<config> --cores 8 --forcerun <regra>
```

Visualizar a DAG em texto:

```bash
snakemake -s workflow/Snakefile --configfile workflow/config/<config> --dag
```

Gerar a imagem da DAG, caso o Graphviz esteja instalado:

```bash
snakemake -s workflow/Snakefile --configfile workflow/config/<config> --dag | dot -Tpng > workflow/dag.png
```

Os logs ficam em:

```text
.snakemake/log/
```
