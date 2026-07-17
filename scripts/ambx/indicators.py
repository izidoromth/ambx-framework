"""
Módulo de indicadores de acessibilidade.

Fornece funções para o cálculo dos três indicadores definidos na
metodologia do framework ambx:

- **PTh** (*Proximity Time*): tempo médio para alcançar os *k* POIs
  mais próximos de cada categoria, por célula da malha.
- **Índice G** (Gini): coeficiente de Gini da distribuição de PTh
  entre células ou grupos.
- **F15**: fração da população residente em zonas onde PTh ≤ 15 min.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# PTh — Proximity Time
# ---------------------------------------------------------------------------


def compute_pth(
    matrix: pd.DataFrame,
    k: int | None = None,
    category_col: str = "poi_category",
    cell_col: str = "cell_idx",
    time_col: str = "travel_time",
) -> pd.DataFrame:
    """
    Calcula o PTh (*Proximity Time*) para cada célula e categoria.

    O PTh de uma célula ``c`` para uma categoria ``cat`` é a média
    do tempo de viagem até os *k* POIs mais próximos daquela
    categoria, descartando pares inalcançáveis (``NaN``).

    Parameters
    ----------
    matrix : pd.DataFrame
        Matriz origem-destino (saída de :func:`ambx.routing.routing_matrix`).
        Deve conter as colunas ``cell_col``, ``category_col`` e
        ``time_col``.
    k : int | None, default None
        Número de POIs a considerar por categoria. Se ``None``,
        usa todos os POIs disponíveis para aquela categoria
        (equivalente à média geral).
    category_col : str, default "poi_category"
        Nome da coluna de categorias dos POIs.
    cell_col : str, default "cell_idx"
        Nome da coluna de identificação das células.
    time_col : str, default "travel_time"
        Nome da coluna com o tempo de viagem (minutos).

    Returns
    -------
    pd.DataFrame
        DataFrame com colunas ``cell_idx``, ``poi_category`` e
        ``pth`` (tempo médio em minutos). Células sem POIs
        alcançáveis em uma categoria recebem ``NaN``.

    Examples
    --------
    >>> matrix = pd.DataFrame({
    ...     "cell_idx": [0, 0, 0, 1, 1],
    ...     "poi_category": ["health", "health", "education", "health", "education"],
    ...     "travel_time": [5.0, 8.0, 12.0, 6.0, 15.0],
    ... })
    >>> compute_pth(matrix, k=2)
       cell_idx poi_category   pth
    0         0      education  12.0
    1         0         health   6.5
    2         1      education  15.0
    3         1         health   6.0
    """
    # Filtra apenas pares alcançáveis
    valid = matrix.dropna(subset=[time_col]).copy()

    if valid.empty:
        return pd.DataFrame(columns=[cell_col, category_col, "pth"])

    # Ordena por tempo dentro de cada grupo (célula, categoria)
    valid = valid.sort_values([cell_col, category_col, time_col])

    # Seleciona os K primeiros de cada grupo
    if k is not None:
        valid = valid.groupby([cell_col, category_col]).head(k)

    # Calcula a média
    pth = valid.groupby([cell_col, category_col])[time_col].mean()
    result = pth.reset_index(name="pth")

    return result


def compute_pth_wide(
    pth_long: pd.DataFrame,
    category_col: str = "poi_category",
    value_col: str = "pth",
) -> pd.DataFrame:
    """
    Converte o PTh de formato longo para largo (wide).

    Útil para ter uma linha por célula com uma coluna para cada
    categoria.

    Parameters
    ----------
    pth_long : pd.DataFrame
        Saída de :func:`compute_pth` no formato longo.
    category_col : str, default "poi_category"
        Nome da coluna de categorias.
    value_col : str, default "pth"
        Nome da coluna com os valores de PTh.

    Returns
    -------
    pd.DataFrame
        DataFrame pivô com ``cell_idx`` como índice e uma coluna
        por categoria de POI.
    """
    return pth_long.pivot_table(
        index="cell_idx",
        columns=category_col,
        values=value_col,
        aggfunc="first",
    )


# ---------------------------------------------------------------------------
# Índice de Gini
# ---------------------------------------------------------------------------


def compute_gini(values: pd.Series) -> float:
    """
    Calcula o coeficiente de Gini para uma série de valores.

    Fórmula (versão para dados amostrais ordenados):

    .. math::

        G = \\frac{2 \\sum_{i=1}^{n} i \\cdot y_i}{n \\sum y_i}
            - \\frac{n + 1}{n}

    onde :math:`y_i` são os valores ordenados de forma crescente.

    Parameters
    ----------
    values : pd.Series
        Série de valores positivos (ex.: PTh por célula).
        Valores ``NaN`` são ignorados.

    Returns
    -------
    float
        Coeficiente de Gini entre 0 (igualdade perfeita) e 1
        (desigualdade máxima). Retorna ``NaN`` se não houver
        dados suficientes.

    Examples
    --------
    >>> compute_gini(pd.Series([10, 10, 10, 10]))
    0.0
    >>> compute_gini(pd.Series([0, 10, 20, 30]))
    0.5
    """
    values = values.dropna()
    n = len(values)

    if n == 0:
        return float("nan")

    # Valores devem ser não-negativos para Gini fazer sentido
    if (values < 0).any():
        raise ValueError(
            "O índice de Gini requer valores não-negativos. "
            f"Encontrados {int((values < 0).sum())} valores negativos."
        )

    if n == 1:
        return 0.0

    sorted_vals = np.sort(values)
    indices = np.arange(1, n + 1)
    numerator = 2 * np.sum(indices * sorted_vals)
    denominator = n * np.sum(sorted_vals)

    if denominator == 0:
        return 0.0

    gini = numerator / denominator - (n + 1) / n
    return float(gini)


# ---------------------------------------------------------------------------
# F15 — Fração da população com acesso em até 15 min
# ---------------------------------------------------------------------------


def compute_f15(
    pth: pd.Series,
    population: pd.Series,
    threshold: float = 15.0,
) -> float:
    """
    Calcula o indicador F15: fração da população residente em
    células onde PTh ≤ *threshold* minutos.

    O indicador é definido como:

    .. math::

        F15 = \\frac{\\sum_{c: PTh_c \\leq 15} pop_c}{\\sum_c pop_c}

    Parameters
    ----------
    pth : pd.Series
        PTh por célula (minutos). Deve estar alinhado com
        ``population`` pelo índice.
    population : pd.Series
        População residente por célula. Valores ``NaN`` são
        tratados como zero.
    threshold : float, default 15.0
        Limiar de tempo em minutos (padrão: 15 min).

    Returns
    -------
    float
        Fração entre 0 e 1. Retorna ``NaN`` se a população
        total for zero.

    Examples
    --------
    >>> pth = pd.Series([5.0, 12.0, 20.0, 8.0])
    >>> pop = pd.Series([100, 200, 150, 50])
    >>> compute_f15(pth, pop)
    0.5
    """
    pop = population.fillna(0)

    total_pop = pop.sum()
    if total_pop == 0:
        return float("nan")

    served = pop[pth <= threshold].sum()
    return float(served / total_pop)


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------


def compute_all_indicators(
    matrix_typ: pd.DataFrame,
    matrix_cond: pd.DataFrame | None = None,
    k: int | None = None,
    population: pd.Series | None = None,
    category_col: str = "poi_category",
    cell_col: str = "cell_idx",
    time_col: str = "travel_time",
    threshold: float = 15.0,
) -> dict:
    """
    Calcula todos os indicadores (PTh, Gini, F15) para um ou dois
    cenários.

    Parameters
    ----------
    matrix_typ : pd.DataFrame
        Matriz OD do cenário típico.
    matrix_cond : pd.DataFrame | None, default None
        Matriz OD do cenário condicionado. Se fornecido, os
        indicadores são calculados para ambos os cenários
        e incluídos no resultado com sufixos ``_typ`` e ``_cond``.
    k : int | None, default None
        Número de POIs por categoria para o PTh.
    population : pd.Series | None, default None
        População por célula (necessário para F15).
    category_col : str, default "poi_category"
    cell_col : str, default "cell_idx"
    time_col : str, default "travel_time"
    threshold : float, default 15.0

    Returns
    -------
    dict
        Dicionário com as chaves:
        - ``"pth_typ"`` : DataFrame — PTh por célula × categoria (típico)
        - ``"pth_cond"`` : DataFrame — PTh por célula × categoria (condicionado, se ``matrix_cond`` fornecido)
        - ``"pth_wide_typ"`` : DataFrame — PTh em formato largo (típico)
        - ``"pth_wide_cond"`` : DataFrame — PTh em formato largo (condicionado)
        - ``"gini_typ"`` : dict — Gini por categoria (típico)
        - ``"gini_cond"`` : dict — Gini por categoria (condicionado)
        - ``"f15_typ"`` : dict — F15 por categoria (típico)
        - ``"f15_cond"`` : dict — F15 por categoria (condicionado)
    """
    result: dict = {}

    def _indicators_for_scenario(matrix, suffix):
        pth_long = compute_pth(
            matrix, k=k, category_col=category_col,
            cell_col=cell_col, time_col=time_col,
        )
        pth_wide = compute_pth_wide(pth_long, category_col=category_col)

        gini_by_cat = {}
        f15_by_cat = {}

        for cat in pth_wide.columns:
            vals = pth_wide[cat].dropna()
            gini_by_cat[cat] = compute_gini(vals)

            if population is not None:
                pop_aligned = population.reindex(vals.index, fill_value=0)
                f15_by_cat[cat] = compute_f15(
                    vals, pop_aligned, threshold=threshold,
                )

        return {
            f"pth_{suffix}": pth_long,
            f"pth_wide_{suffix}": pth_wide,
            f"gini_{suffix}": gini_by_cat,
            f"f15_{suffix}": f15_by_cat,
        }

    result.update(_indicators_for_scenario(matrix_typ, "typ"))

    if matrix_cond is not None:
        result.update(_indicators_for_scenario(matrix_cond, "cond"))

    return result
