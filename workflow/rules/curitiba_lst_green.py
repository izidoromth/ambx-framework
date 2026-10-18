"""Penalização composta de Curitiba: calor (LST) e sombreamento por vegetação.

A regra recebe **os dois valores no mesmo ponto** e devolve um único fator:
o do calor multiplicado pela redução de tempo atribuída ao sombreamento.

**Por que composta.** O cenário ``green`` sozinho (regra simples sobre a camada
de vegetação) produziria a mesma multiplicação, mas não conseguiria ler as duas
camadas no mesmo ponto amostrado. A regra composta mantém a correspondência
espacial entre LST e vegetação e deixa o mecanismo explícito na configuração.

**Calibração da vegetação.** Jia et al. (2023, *E3S Web of Conferences*
396:05013, Hong Kong) monitoraram 337 pedestres em campo e mediram que árvores
de rua reduzem o tempo de viagem percebido em até **3 s/100 m**, além de
mostrarem que a velocidade cai com o estresse térmico (R² = 0,719).

A 5 km/h, 100 m levam 72 s; com 3 s a menos, 69 s. Logo:

    f_verde = 69 / 72 = 0,9583

Diferente da formulação anterior, a redução **não** é condicionada ao calor:
Jia mede o efeito da árvore sobre o tempo de deslocamento, não sobre o excesso
térmico. Aplicá-la apenas onde há calor seria uma leitura do artigo que ele não
sustenta.
"""

from math import isnan

from workflow.rules.curitiba_lst import lst_factor

# Fator de redução do tempo associado à presença de vegetação.
# 69/72, de 3 s a menos em 100 m a 5 km/h (Jia et al., 2023).
FATOR_VERDE = 69.0 / 72.0


def curitiba_lst_green(values):
    """Fator conjunto de LST e vegetação para um ponto amostrado.

    Acessa ``values["lst"]`` (°C) e ``values["area_verde"]`` (presença).
    Ausência de dado chega como ``None`` ou ``NaN``.

    Onde não há vegetação — ou o pixel está fora do raster —, devolve apenas o
    fator térmico, sem a multiplicação.
    """
    lst = values.get("lst")
    verde = values.get("area_verde")

    if lst is None or isnan(lst):
        return 1.0

    fator = lst_factor(lst)
    tem_verde = verde is not None and not isnan(verde) and verde > 0
    return fator * (FATOR_VERDE if tem_verde else 1.0)
