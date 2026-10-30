"""Regra de penalização por risco de inundação em Porto Alegre.

**Calibração.** Li et al. (2026, *Acta Polytechnica CTU*, DOI
10.14311/app.2026.57.0226) mediram a velocidade de 188 participantes em quatro
lâminas d'água (0 / 0,35 / 0,60 / 0,90 m). Velocidade média da amostra total:

    profundidade   velocidade   fator
    0 m            1,69 m/s     1,00
    0,35 m         0,99 m/s     1,71
    0,60 m         0,91 m/s     1,86
    0,90 m         0,79 m/s     2,14

Fator = v(0) / v(d).

**Pareamento classe → profundidade.** A camada do SGB-CPRM classifica risco
geológico, não lâmina d'água, e não traz profundidade em nenhum campo. As três
classes são aqui tratadas como equivalentes às três profundidades medidas, em
ordem crescente. É hipótese de aplicabilidade, não dado da fonte.
"""

FACTORS = {
    "Alto": 1.69 / 0.79,
    "Médio": 1.69 / 0.91,
    "Baixa": 1.69 / 0.99,
}


def porto_alegre_inundacao(value):
    """Converte a classe de inundação em fator multiplicativo."""
    return FACTORS.get(str(value).strip(), 1.0)
