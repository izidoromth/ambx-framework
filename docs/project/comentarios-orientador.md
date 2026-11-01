# Comentários do orientador (Overleaf, `\ric`)

Origem: `~/Downloads/MatheusIzidoroDissertacao.zip` (versão antiga do Overleaf,
em português). Os comentários foram anotados com `\newcommand{\ric}[1]{\textcolor{magenta}{#1}}`.

**Atenção:** o zip está em estado anterior à tradução e à renumeração. A coluna
"onde se aplica hoje" indica o arquivo equivalente no repositório local (inglês).

---

## 1. `3.methodology` — falta de detalhe técnico  PENDENTE

> Achei esta seção muito descritiva, com poucos detalhes técnicos. Por exemplo,
> que tipo de dado você precisa? Quais são as fontes possíveis? Que tipo de
> pré-processamento (se houver)? Algoritmos utilizados?

- Zip: `sections/3.methodology.tex:4` (antes do primeiro parágrafo)
- Local: `sections/3.methodology.tex`
- Situação: **não endereçado.** A abertura descreve o método e delega a
  arquitetura às subseções, mas não responde o que o orientador pediu.

## 2. `3.2.penalization` — figura dos elementos de interesse  PENDENTE

> Aqui cabe uma figura mostrando os elementos de interesse: aresta, valor,
> função, camadas, composição, raster x vetorial, agregação.

- Zip: `sections/3.subsections/3.2.penalization.tex:9`
- Local: `sections/3.subsections/3.2.penalization.tex`
- Situação: **não existe figura** na 3.2 local (nem `figure`, nem `includegraphics`).
  Só a `framework.pdf` está na 3.1.

## 3. `3.2.penalization` — citação do algoritmo de menor custo  PENDENTE

> Com os custos condicionados definidos, um algoritmo de caminho de menor custo
> **[ref]** é …

- Zip: `sections/3.subsections/3.2.penalization.tex:99`
- Local: `sections/3.subsections/3.2.penalization.tex:65`
  — "With conditioned costs defined, a least-cost path algorithm runs over the
  graph…"
- Situação: o `[ref]` desapareceu na tradução. **Falta citar** (Dijkstra,
  ou o algoritmo que o OSMnx/networkx usa de fato).

## 4. `3.3` — "validação" é termo forte  RESOLVIDO POR RENOMEAÇÃO

> O que vc chama de validação? Validação é muito forte. Teste do framework?
> Verificação do framework?

- Zip: `sections/3.subsections/3.3.validation.tex:3`
- Local: `sections/3.subsections/3.3.applicability.tex`
- Situação: a subseção foi renomeada de *Validation* para *Applicability*, o que
  responde à objeção. **Confirmar se o conteúdo também deixou de usar
  "validation" internamente.**

## 5. `2.fundamentals` — `$i$?` solto na definição de PTh  RESÍDUO DE TRADUÇÃO

> … os $k$ pontos de interesse mais próximos de uma categoria de serviço **$i$?**…

- Zip: `sections/2.fundamentals.tex:39`
- Local: `sections/2.fundamentals.tex:38` — `\ric{$i$}?` ainda presente
- Situação: o texto local tem o mesmo `\ric{$i$}?`. **Remover o `?` ou integrar
  o $i$ à notação.**

## 6. `2.fundamentals` — explicar a Tabela de trabalhos relacionados  JÁ RESOLVIDO

> Precisa citar e explicar a Tabela~\ref{tab:trabalhos_relacionados} no texto.
> Por exemplo, a Tabela… resume alguns dos trabalhos relacionados segundo o tipo
> de interdição da malha viária causada pela condição ambiental. Neste caso, pode
> haver a simples interdição ou uma penalização de caminhos… Além disso, os
> trabalhos podem considerar ou não a condição econômica da população afetada.

- Zip: `sections/2.fundamentals.tex:157` (dentro de `\hide{…}`)
- Local: `sections/2.fundamentals.tex:97` — parágrafo novo que descreve a tabela
  (interdição binária × penalização contínua × análise socioeconômica)
- Situação: **endereçado** na tradução. Decidir se o `\hide{\ric{…}}` sai do
  local (hoje ainda está na linha 95).

## 7. `6.results` — "resultados esperados" já não se aplica  JÁ RESOLVIDO

> Reveja. Os resultados agora não são mais esperados; já existem.

- Zip: `sections/6.results.tex:17`
- Local: `sections/5.results.tex` + `sections/5.subsections/`
- Situação: **endereçado.** A seção foi reescrita com os resultados observados.

## 8. `1.introduction` — frase sobre equidade  PENDENTE

> Com isso, contribui para a compreensão de como garantir equidade na
> acessibilidade urbana sob cenários de perturbação ambiental.

- Zip: `sections/1.introduction.tex:9` (fim do parágrafo "Este trabalho avalia…")
- Local: `sections/1.introduction.tex`, parágrafo "This work evaluates how
  climate disruptions would alter urban accessibility…"
- Situação: a frase **não tem equivalente** na versão em inglês. Decidir se
  entra como fecho do parágrafo ou se a lista de contribuições já cobre a ideia.

## 9. `1.introduction` — quatro contribuições, não três  PENDENTE

> Acho que tem várias contribuições aqui: i) o próprio framework para
> experimentações diversas; ii) a forma de modelar a influência das condições
> ambientais no deslocamento (rede viária, camadas aditivas de efeitos);
> iii) os estudos de caso de Curitiba e POA; iv) fatores sócio-econômicos.

- Zip: `sections/1.introduction.tex:11` (comentário solto após o parágrafo)
- Local: `sections/1.introduction.tex`, lista `itemize` de contribuições
- Situação: a lista local tem **três** itens e funde (i) com (ii). O item (ii)
  — **modelagem de camadas aditivas de efeitos** — não aparece como contribuição
  própria. Decidir se vira item separado.

---

## Resumo

| # | Onde | Situação |
|---|---|---|
| 1 | 3.methodology — dados/algoritmos | pendente |
| 2 | 3.2 — figura dos elementos | pendente |
| 3 | 3.2 — `[ref]` do least-cost path | pendente |
| 4 | 3.3 — "validação" | resolvido (renomeado) |
| 5 | 2.fundamentals — `$i$?` | resíduo |
| 6 | 2.fundamentals — Tabela relacionada | resolvido (limpar `\hide`) |
| 7 | 6.results — resultados esperados | resolvido |
| 8 | 1.introduction — equidade | pendente |
| 9 | 1.introduction — 4 contribuições | pendente |
