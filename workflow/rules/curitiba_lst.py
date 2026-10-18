"""Penalização de Curitiba por temperatura de superfície (LST).

**Calibração.** Função linear ancorada em Horiuchi et al. (2018, *Biology Open*
7:bio035121): a "economical walking speed" de homens jovens cai ~7% de 23 °C
para 33 °C, isto é, **k = 0,0070 por °C** com referência termoneutra
**t0 = 23 °C**. A LST entra como *proxy ordinal* de exposição térmica, não como
temperatura do ar — Nascimento et al. (2022, *Atmosphere* 13:491) mostram que LST e
T_ar se correlacionam em São Paulo (r = 0,81/0,82; MAE 1,2–1,9 °C) mas **não
publicam função de conversão**, o que descarta converter LST → T_ar.

Nenhum estudo regride velocidade de caminhada diretamente sobre LST, e a
magnitude do efeito é, portanto, **indicativa, não preditiva**. Ver
``docs/proximos-passos.md`` para a justificativa completa e as limitações.

O cenário demonstrativo (``lst_demo_k05``) usa a mesma função com ``k`` maior; a
diferença fica explícita na configuração, não no código.
"""

from math import isnan

# Calibração principal (literatura).
K_LITERATURA = 0.0070
T0_LITERATURA = 23.0

# Cenário demonstrativo: ~7x a sensibilidade calibrada, para evidenciar a
# resposta do roteamento. Não tem respaldo empírico.
K_DEMO = 0.05

FMAX = 2.0


def lst_factor(value, k=K_LITERATURA, t0=T0_LITERATURA, fmax=FMAX):
    """Fator multiplicativo linear em função da LST.

    ``f(T) = clip(1 + k·(T − t0), 1, fmax)``. O piso 1 impede "bônus" por
    frio (Horiuchi mede perda no calor, não ganho no frio); o teto ``fmax``
    protege contra pixels anômalos do raster.
    """
    if value is None:
        return 1.0
    try:
        t = float(value)
    except (TypeError, ValueError):
        return 1.0
    if isnan(t):
        return 1.0
    return min(max(1.0 + k * (t - t0), 1.0), fmax)


def curitiba_lst(value):
    """Cenário calibrado: k = 0,0070/°C, t0 = 23 °C (Horiuchi et al., 2018)."""
    return lst_factor(value)
