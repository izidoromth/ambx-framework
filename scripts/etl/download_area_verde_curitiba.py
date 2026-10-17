"""Baixa e prepara a camada de áreas verdes de Curitiba de 2019.

Uso:
    python scripts/etl/download_area_verde_curitiba.py

O produto final é um **raster binário** (1 = vegetação, 0 = sem vegetação).
A saída vetorial não é usada: a fonte tem ~126 mil polígonos fragmentados e
qualquer união sobre eles leva minutos, sem ganho — o pipeline só precisa
saber se um ponto está ou não sob vegetação.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.features import rasterize
from scipy import ndimage

URL = "https://ippuc.org.br/geodownloads/SHAPES_SIRGAS/AREA_VERDE_2019_SIRGAS.zip"
ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "scripts" / "etl" / "cache_area_verde"
ZIP_PATH = CACHE_DIR / "AREA_VERDE_2019_SIRGAS.zip"
EXTRACT_DIR = CACHE_DIR / "AREA_VERDE_2019_SIRGAS"
OUTPUT_DIR = ROOT / "data" / "processed" / "curitiba"
OUTPUT = OUTPUT_DIR / "area_verde_2019.tif"
METADATA = OUTPUT_DIR / "area_verde_2019.json"

# Resolução do raster de saída, em metros. Precisa ser menor ou igual à
# dilatação, senão a dilatação de 1 pixel excede o raio pretendido.
RES_M = 5.0

# Raio de sombreamento aplicado à área verde, em metros.
#
# O dado de origem é poligonal (praças, parques, canteiros) e as vias passam
# ao redor deles: apenas 3,4% dos pontos amostrados sobre a rede caem dentro
# de uma mancha verde. Sem dilatação, a vegetação não tem efeito mensurável.
#
# A dilatação modela a sombra projetada pela copa sobre a calçada adjacente.
# 5 m corresponde ao raio de copa de uma árvore urbana adulta (4–8 m) e é
# conservador: não invade a quadra vizinha.
DILATE_M = 5.0

# Expansão em pixels: 5 m de raio a 5 m/pixel = 1 pixel.
DILATE_PX = max(1, round(DILATE_M / RES_M))


def download() -> None:
    if ZIP_PATH.exists():
        print(f"ZIP já existe: {ZIP_PATH}")
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = ZIP_PATH.with_suffix(".zip.part")
    print(f"Baixando: {URL}")
    with requests.get(URL, stream=True, timeout=600) as response:
        response.raise_for_status()
        with temporary.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)
    temporary.replace(ZIP_PATH)


def main() -> None:
    download()
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(EXTRACT_DIR)

    shapefiles = list(EXTRACT_DIR.rglob("*.shp"))
    if not shapefiles:
        raise FileNotFoundError(f"Nenhum Shapefile encontrado em {EXTRACT_DIR}")

    source = shapefiles[0]
    print(f"Lendo: {source}")
    gdf = gpd.read_file(source).to_crs(31982)
    original_features = len(gdf)
    original_area_km2 = gdf.area.sum() / 1e6

    # Grade alinhada à extensão da camada, com 10 m de lado.
    minx, miny, maxx, maxy = gdf.total_bounds
    width = int(np.ceil((maxx - minx) / RES_M))
    height = int(np.ceil((maxy - miny) / RES_M))
    transform = rasterio.transform.from_origin(minx, maxy, RES_M, RES_M)
    print(f"Rasterizando {original_features:,} polígonos em {width}×{height} "
          f"pixels de {RES_M:.0f} m...")

    # Rasterização por centro de pixel: um pixel só é vegetação se seu centro
    # cai dentro do polígono. Com `all_touched=True`, um pixel é marcado se
    # qualquer parte de um polígono o tocar — e com 126 mil fragmentos isso
    # infla a área em ~70% (110,9 → 189,0 km²), embutindo uma dilatação não
    # declarada.
    veg = rasterize(
        ((geom, 1) for geom in gdf.geometry.values),
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype="uint8",
        all_touched=False,
    )

    # Dilatação por estrutura de disco: aproxima o buffer circular de
    # `DILATE_M` metros. Única dilatação aplicada, e explícita.
    print(f"Dilatando {DILATE_M:.0f} m ({DILATE_PX} pixel)...")
    estrutura = ndimage.iterate_structure(
        ndimage.generate_binary_structure(2, 1), DILATE_PX
    )
    veg = ndimage.binary_dilation(veg, structure=estrutura).astype("uint8")

    veg_area_km2 = float(veg.sum()) * (RES_M * RES_M) / 1e6
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        OUTPUT,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="uint8",
        crs="EPSG:31982",
        transform=transform,
        compress="deflate",
    ) as dst:
        dst.write(veg, 1)

    metadata = {
        "source": "IPPUC — Dados Geográficos de Curitiba",
        "product": "Área Verde 2019 (raster booleano, dilatação de sombreamento)",
        "url": URL,
        "source_format": "Shapefile em ZIP",
        "file": str(OUTPUT.relative_to(ROOT)),
        "crs": "EPSG:31982",
        "resolution_m": RES_M,
        "dilation_m": DILATE_M,
        "features_originais": original_features,
        "area_original_km2": round(original_area_km2, 2),
        "area_rasterizada_km2": round(veg_area_km2, 2),
        "download_script": "scripts/etl/download_area_verde_curitiba.py",
    }
    METADATA.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(f"Salvo: {OUTPUT}")
    print(f"Área original: {original_area_km2:.1f} km² → "
          f"com dilatação de {DILATE_M:.0f} m: {veg_area_km2:.1f} km²")


if __name__ == "__main__":
    main()
