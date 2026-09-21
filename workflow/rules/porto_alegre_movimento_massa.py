"""Regra de penalização por movimento de massa em Porto Alegre."""


def porto_alegre_movimento_massa(value):
    """Converte a classe de movimento de massa em fator multiplicativo."""
    factors = {
        "Alta": 2.0,
        "Média": 1.5,
        "Baixa": 1.1,
    }
    return factors.get(str(value).strip(), 1.0)
