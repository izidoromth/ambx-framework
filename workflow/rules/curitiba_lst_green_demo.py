"""Cenário demonstrativo de Curitiba (``lst_green_composite_demo_k05``).

`k = 0,05/°C`, cerca de 7× a calibração; a vegetação aplica o mesmo fator de
redução do cenário calibrado. **Não tem respaldo empírico** no valor de `k`.
"""

from math import isnan

from workflow.rules.curitiba_lst import K_DEMO, lst_factor
from workflow.rules.curitiba_lst_green import FATOR_VERDE


def curitiba_lst_green_demo(values):
    """Fator térmico com k = 0,05/°C, reduzido pela vegetação quando presente."""
    lst = values.get("lst")
    verde = values.get("area_verde")

    if lst is None or isnan(lst):
        return 1.0

    fator = lst_factor(lst, k=K_DEMO)
    tem_verde = verde is not None and not isnan(verde) and verde > 0
    return fator * (FATOR_VERDE if tem_verde else 1.0)
