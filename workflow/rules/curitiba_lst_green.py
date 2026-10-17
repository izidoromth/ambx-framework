"""Penalização composta de Curitiba: calor (LST) atenuado por área verde.

Diferente do cenário ``lst_green`` (duas regras simples em sequência), esta
função recebe **os dois valores no mesmo ponto** e só aplica a atenuação onde
há calor. Sem o condicional de temperatura, o verde descontaria o custo mesmo
em pontos amenos — o mesmo defeito do encadeamento sequencial.
"""

from math import isnan

from workflow.rules.curitiba_lst import lst_factor


def _compose(values, k, t0, atenuacao):
    """Atenua apenas o **excesso** sobre 1,0, nunca a linha de base.

    1,084 com atenuação 0,75 vira 1,0 + (1,084−1,0)·0,75 = 1,063 — e não
    0,813, que seria um bônus por verde em ponto quente.
    """
    lst = values.get("lst")
    verde = values.get("area_verde")

    if lst is None or isnan(lst):
        return 1.0
    fator = lst_factor(lst, k=k, t0=t0)
    excesso = fator - 1.0
    if excesso <= 0:
        return 1.0  # ponto ameno: verde é irrelevante

    tem_verde = verde is not None and not isnan(verde) and verde > 0
    return 1.0 + excesso * (atenuacao if tem_verde else 1.0)


def curitiba_lst_green(values):
    """Calibrado: atenua em 25% o excesso térmico onde há área verde.

    A parcela térmica vem de :func:`lst_factor` (Huang 2018). A atenuação de
    0,75 é **arbitrária** — não há fonte para ela.
    """
    return _compose(values, k=0.0070, t0=23.0, atenuacao=0.75)
