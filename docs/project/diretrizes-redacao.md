# Artigo final — diretrizes de redação

Foco total em escrever o artigo. Dívida técnica e implementação ficam paradas
até a submissão.

## Regra do processo

- Tradução **seção por seção**, em ordem.
- **Só avançar para a próxima seção após OK explícito do autor.**
- Referência de estilo: `academic-writing.md` (30 princípios, A1–F2), nesta pasta.

## Ordem

`1.introduction` → `2.fundamentals` → `3.methodology` → `3.1.architecture` →
`3.2.penalization` → `3.3.validation` → `5.case_studies` → `6.results` →
`7.discussion` → `8.conclusion`

Itens de conteúdo a resolver durante a tradução de cada seção estão em
`docs/project/proximos-passos.md`, seção "Redação do artigo final".

## Enquadramento obrigatório: computação aplicada / ciência de dados

O trabalho é de **computação aplicada e ciência de dados**, com o urbano como
domínio de aplicação — não um estudo urbanístico com software de apoio.

Sempre que possível, escrever de modo que isso fique evidente SEM uma frase
declarativa do tipo "this is applied computing". Meios:

- Tratar o artefato computacional como contribuição de primeira classe: modelo
  de dados region-agnostic, algoritmo, pipeline reprodutível, configuração
  declarativa.
- Nomear as dificuldades técnicas concretas: CRS heterogêneos, resoluções
  distintas, many-to-many shortest path, custo contínuo vs. categórico,
  integração raster + vetor + censo.
- Quantificar: métricas, cobertura, tempo de execução, comparação entre cidades.
- Usar vocabulário de engenharia de software quando for o caso
  (reprodutibilidade, acoplamento, extensibilidade), sem inflar.

## Risco por seção: a cidade como instância, não como tema

Vale para toda seção, crítico em `5.case_studies`. O município entra como
**instância de avaliação do artefato**, nunca como objeto de estudo urbano.

- Errado: descrever clima, história, urbanização, formação territorial, dados
  socioeconômicos da cidade como se fossem o assunto.
- Certo: apresentar a cidade como configuração de entrada — que camada
  ambiental, com que resolução, com que parâmetro de penalização, que fonte de
  dado socioespacial — e o resultado como validação cruzada entre domínios.

Teste rápido: se o parágrafo continua fazendo sentido depois de trocar o nome da
cidade por "City A", ele está no enquadramento certo. Se só funciona para
Curitiba, o texto derivou para estudos urbanos.

## Terminologia fixada

| Termo | Uso |
|---|---|
| **disruption** | o evento/fenômeno (`climate disruption`) |
| **typical scenario** | estado de referência, sem perturbação |
| **conditioned scenario** | estado com custos reescritos pelas camadas ambientais |

Não usar `perturbed` nem `reference` como sinônimos.

## Princípios mais violados (checar a cada seção)

- **B2/F2** — nunca "not X, but Y". Reescrever positivo.
- **B7** — concisão brutal. Cortar "it is important to note", "in order to",
  "plays an important role".
- **B8** — evitar "delve", "leverage", "landscape", "Moreover/Furthermore"
  em sequência, "crucial/vital/essential" como sinônimos.
- **B5** — uma ideia por frase. Se precisa de "while"/"unlike"/";" para juntar
  duas afirmações, são duas frases.
- **A5** — claim-first: objetivo antes de fórmula/código.
- **A6** — ritmo Goal-Problem-Solution (vale para seção E subseção).
- **B6** — fato empírico assertivo, mecanismo causal com hedge.
- **A2/A4** — encadear parágrafos com transição explícita; fechar cada um.
- **D2/D5/D7** — toda figura referenciada, interpretada, e com legenda
  auto-suficiente.

## Divisão arquitetura / calibração

Valores calibrados (tamanho de célula, `max_snap_distance`, parâmetros `k`) vão
na seção 5, não nas seções de método. O método descreve o mecanismo e o
parâmetro como configurável; a calibração declara o valor usado.
