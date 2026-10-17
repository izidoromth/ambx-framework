"""Cenário demonstrativo de Curitiba (``lst_green_composite_demo_k05``).

`k = 0,05/°C`, cerca de 7× a calibração. Como no cenário calibrado, a área verde
atenua apenas o excesso sobre 1,0. **Não tem respaldo empírico.**
"""

from workflow.rules.curitiba_lst import K_DEMO, T0_LITERATURA
from workflow.rules.curitiba_lst_green import _compose


def curitiba_lst_green_demo(values):
    """Fator composto com k = 0,05/°C e atenuação de 25% onde há verde."""
    return _compose(values, k=K_DEMO, t0=T0_LITERATURA, atenuacao=0.75)
