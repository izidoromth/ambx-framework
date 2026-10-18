# Build dos textos (qualificação e dissertação) em qualquer máquina.
#
# Uso:
#   docker build -t ambx-latex .
#   docker run --rm -v "$PWD/docs:/work/docs" ambx-latex dissertation
#
# O argumento é o nome da pasta dentro de docs/ (qualifying ou dissertation).
# O PDF sai em docs/<pasta>/main.pdf.

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# texlive-latex-extra: pacotes usados no documento (acro, booktabs, tabularx,
#   float, xcolor, pdfpages, svg).
# texlive-lang-portuguese: babel com opção brazil.
# texlive-bibtex-extra: estilos adicionais; sbc.bst vem do repositório.
# latexmk: resolve as múltiplas passagens (citações, referências cruzadas).
# poppler-utils: pdfinfo, usado para conferir a saída.
# make: atalho para builds repetidos.
RUN apt-get update && apt-get install -y --no-install-recommends \
        latexmk \
        make \
        poppler-utils \
        texlive-fonts-recommended \
        texlive-lang-portuguese \
        texlive-latex-extra \
        texlive-latex-recommended \
        texlive-science \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# Script de entrada: recebe o nome do diretório do documento.
COPY build.sh /usr/local/bin/build.sh
RUN chmod +x /usr/local/bin/build.sh

ENTRYPOINT ["/usr/local/bin/build.sh"]
CMD ["dissertation"]
