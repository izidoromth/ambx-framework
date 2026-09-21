"""Atenuação por presença de área verde em Curitiba."""


def curitiba_green_modifier(_value):
    """Fator aplicado à parte da aresta coberta por área verde.

    A proporção coberta é calculada pelo ``aggregation=mean`` do ambx.
    """
    return 0.75
