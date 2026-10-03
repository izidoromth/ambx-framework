"""Penalização composta de Curitiba: calor (LST) atenuado por área verde.

Diferente do cenário ``lst_green`` (duas regras simples em sequência), esta
função recebe **os dois valores no mesmo ponto** e só aplica a atenuação onde
há calor. Sem o condicional de temperatura, o verde descontaria o custo mesmo
em pontos amenos — o mesmo defeito do encadeamento sequencial.
"""

from math import isnan


def curitiba_lst_green(values):
    """Fator conjunto de LST e área verde para um ponto amostrado.

    Acessa ``values["lst"]`` (temperatura, °C) e ``values["area_verde"]``
    (presença). Ausência de dado chega como ``None`` ou ``NaN``.

    Regra: acima de 25 °C, o verde atenua em 25%; em ponto ameno, sem efeito.
    """
    lst = values.get("lst")
    verde = values.get("area_verde")

    if lst is None or isnan(lst):
        return 1.0
    if lst <= 25:
        return 1.0  # ponto ameno: verde é irrelevante

    fator = 1.2 if lst <= 27 else 1.5 if lst <= 30 else 2.0
    tem_verde = verde is not None and not isnan(verde) and verde > 0
    return fator * (0.75 if tem_verde else 1.0)
