"""Regra de penalização por movimento de massa em Porto Alegre.

**Cenário de evento ocorrido, não de probabilidade.** A literatura não relaciona
deslizamento à redução de velocidade de caminhada: o fenômeno é tratado como
**bloqueio de via** (a área é intransitável, não "mais lenta"). Assim, este
cenário assume que o evento **já ocorreu** nas áreas mapeadas, e interdita as
arestas ali contidas (fator infinito, que o roteamento já reconhece como aresta
intransponível — ver ``PenaltyRule.penalty_fn``).

`Alta` e `Média` interdizem. `Baixa` permanece livre: não é indicação de
ocorrência, e sim de suscetibilidade baixa.

**Consequência a reportar:** como a interdição remove arestas da rede, parte dos
POIs pode ficar inalcançável. Isso é um *resultado* (perda de acesso), não uma
falha — precisa ser medido e apresentado junto ao cenário.
"""

INF = float("inf")

FACTORS = {
    "Alta": INF,
    "Média": INF,
    "Baixa": 1.0,
}


def porto_alegre_movimento_massa(value):
    """Converte a classe de movimento de massa em fator multiplicativo."""
    return FACTORS.get(str(value).strip(), 1.0)
