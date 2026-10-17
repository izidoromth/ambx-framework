"""Regra de penalização por suscetibilidade a inundação em Porto Alegre.

**Calibração (classe Alta).** Xu et al. (2026, *Acta Polytechnica CTU*,
DOI 10.14311/app.2026.57.0226) mediram a velocidade de caminhada de 188
participantes em quatro lâminas d'água (0 / 0,35 / 0,60 / 0,90 m). A 0,35 m a
redução foi de **38,6% (homens) e 44,8% (mulheres)**; o passo encurtou 37% e
32%, e a estabilidade caiu (sway lateral +69% / +133%).

Fator = 1 / (1 − redução). Com a redução feminina (44,8%), 1/0,552 = **1,81**.
Adota-se **2,0** (≈ 1/0,5, ou seja, metade da velocidade) como arredondamento
conservador da pior condição medida.

**Médio e Baixa não têm fonte.** A interpolação entre 1,0 e 2,0 é arbitrária e
deve ser declarada como tal.
"""

# Calibração (classe Alta) — Xu et al. (2026).
FATOR_ALTO = 2.0

# Sem fonte: interpolação arbitrária entre não-penalizado e o fator do Alto.
FATOR_MEDIO = 1.5
FATOR_BAIXA = 1.1

FACTORS = {
    "Alto": FATOR_ALTO,
    "Médio": FATOR_MEDIO,
    "Baixa": FATOR_BAIXA,
}


def porto_alegre_inundacao(value):
    """Converte a classe de inundação em fator multiplicativo."""
    return FACTORS.get(str(value).strip(), 1.0)
