"""Penalizações do caso de uso de Curitiba."""


def curitiba_lst(value):
    """Retorna o fator de penalização em função da temperatura."""
    if value <= 25:
        return 1.0
    if value <= 27:
        return 1.2
    if value <= 30:
        return 1.5
    return 2.0
