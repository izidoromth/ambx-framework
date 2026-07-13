"""
ambx — Framework para Avaliação da Acessibilidade Urbana de Curta Distância
sob Perturbações Ambientais (Ambient Access).

Módulos:
    grid        : Geração de malha territorial (hexagonal / quadrada).
    utils       : Utilitários geoespaciais (CRS UTM, geometria).
    network     : Grafo viário a partir do OpenStreetMap.
    pois        : Coleta e categorização de Pontos de Interesse.
    routing     : Roteamento A* e matriz origem-destino.
    environment : Carregamento de camadas ambientais (raster / vetorial).
    penalties   : Funções de penalização ambiental sobre arestas.
"""

__version__ = "0.1.0"

from ambx import (
    grid,
    utils,
    network,
    pois,
    routing,
    environment,
    penalties,
)
