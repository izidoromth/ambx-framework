"""Regra de penalização por suscetibilidade a inundação em Porto Alegre."""


def porto_alegre_inundacao(value):
    """Converte a classe de inundação em fator multiplicativo."""
    factors = {
        "Alto": 2.0,
        "Médio": 1.5,
        "Baixa": 1.1,
    }
    return factors.get(str(value).strip(), 1.0)
