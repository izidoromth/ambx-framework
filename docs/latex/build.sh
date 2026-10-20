#!/bin/sh
# Compila um documento LaTeX do repositório.
#
# Uso:
#   build.sh <diretório>      # qualifying ou dissertation
#
# Espera o diretório do documento montado em /work/docs/latex/<diretório>.

set -eu

DOC="${1:-dissertation}"
DIR="/work/docs/latex/${DOC}"

if [ ! -f "${DIR}/main.tex" ]; then
    echo "erro: ${DIR}/main.tex não encontrado" >&2
    echo "monte o repositório em /work: -v \"\$PWD:/work\"" >&2
    exit 1
fi

cd "${DIR}"

# Duas passagens + bibtex resolvem citações e referências cruzadas.
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

# Remove auxiliares, preservando o PDF.
latexmk -c >/dev/null 2>&1 || true

if [ -f main.pdf ]; then
    paginas=$(pdfinfo main.pdf | awk '/^Pages:/ {print $2}')
    echo "ok: ${DIR}/main.pdf (${paginas} páginas)"
else
    echo "erro: main.pdf não foi gerado" >&2
    exit 1
fi
