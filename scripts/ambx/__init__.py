"""
ambx — Framework para Avaliação da Acessibilidade Urbana de Curta Distância
sob Perturbações Ambientais (Ambient Access).

Módulos:
    grid         : Geração de malha territorial (hexagonal / quadrada).
    utils        : Utilitários geoespaciais (CRS UTM, geometria).
    network      : Grafo viário a partir do OpenStreetMap.
    pois         : Coleta e categorização de Pontos de Interesse.
    routing      : Roteamento A* e matriz origem-destino.
    environment  : Carregamento de camadas ambientais (raster / vetorial).
    penalties    : Funções de penalização ambiental sobre arestas.
    indicators   : Indicadores de acessibilidade (PTh, Gini, F15).
    demographics : Compatibilização de dados censitários com a malha.
"""

__version__ = "0.2.0"

from ambx import (
    grid,
    utils,
    network,
    pois,
    routing,
    environment,
    penalties,
    indicators,
    demographics,
)
