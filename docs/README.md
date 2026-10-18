# Textos — build LaTeX

Dois documentos:

| Pasta | Conteúdo |
|---|---|
| `qualifying/` | qualificação, aprovada — **congelada** |
| `dissertation/` | texto da dissertação, em andamento |

Cada um compila de forma independente (`main.tex` → `main.pdf`) e usa os mesmos
arquivos auxiliares: `refs.bib`, `sbc.bst`, `sbc-template.sty`, `caption2.sty`.

## Com Docker (recomendado)

Não exige TeX Live na máquina. A imagem é construída uma vez.

```bash
# a partir da raiz do repositório
docker build -t ambx-latex docs/
```

Compilar:

```bash
docker run --rm -v "$PWD:/work" ambx-latex dissertation
docker run --rm -v "$PWD:/work" ambx-latex qualifying
```

O PDF sai em `docs/<documento>/main.pdf`.

O volume monta o repositório inteiro em `/work` — não apenas a pasta do
documento. Isso é necessário porque `main.tex` referencia `figs/`, `files/`,
`refs.bib` e `sbc.bst` por caminho relativo.

## Sem Docker

Com TeX Live instalado:

```bash
cd docs/dissertation
latexmk -pdf main.tex
```

O `sbc.bst` vem do repositório, não do sistema: não troque por um estilo
instalado no TeX Live.

Se faltar algum pacote, os nomes estão listados no `Dockerfile`.

## O que a imagem contém

| Pacote | Necessário para |
|---|---|
| `texlive-latex-extra` | `acro`, `booktabs`, `tabularx`, `float`, `xcolor`, `pdfpages`, `svg` |
| `texlive-lang-portuguese` | `babel` com opção `brazil` |
| `texlive-science` | `amsmath`, `amssymb` |
| `latexmk` | múltiplas passagens (bibtex e referências cruzadas) |
| `poppler-utils` | `pdfinfo`, para conferir o número de páginas |

## Limpeza

O `build.sh` remove os auxiliares (`.aux`, `.log`, `.out`) e preserva o PDF.
Para limpar tudo manualmente:

```bash
cd docs/dissertation
latexmk -C
```
