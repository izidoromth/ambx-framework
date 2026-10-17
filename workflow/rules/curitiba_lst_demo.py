"""Cenário demonstrativo de Curitiba (``lst_demo_k05``).

`k = 0,05/°C`, cerca de 7× a calibração de Huang et al. (2018). Existe para
evidenciar a resposta da lib a um gradiente térmico severo; **não tem respaldo
empírico** e não deve ser apresentado como resultado.
"""

from workflow.rules.curitiba_lst import K_DEMO, lst_factor


def curitiba_lst_demo(value):
    """Fator com k = 0,05/°C (t0 = 23 °C, fmax = 2,0)."""
    return lst_factor(value, k=K_DEMO)
