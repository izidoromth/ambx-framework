"""Baixa e prepara a camada de áreas verdes de Curitiba de 2019.

Uso:
    python scripts/etl/download_area_verde_curitiba.py

O ZIP original fica no cache do ETL. O produto processado é salvo como
GeoParquet em ``data/processed/curitiba``.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import geopandas as gpd
import requests


URL = "https://ippuc.org.br/geodownloads/SHAPES_SIRGAS/AREA_VERDE_2019_SIRGAS.zip"
ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "scripts" / "etl" / "cache_area_verde"
ZIP_PATH = CACHE_DIR / "AREA_VERDE_2019_SIRGAS.zip"
EXTRACT_DIR = CACHE_DIR / "AREA_VERDE_2019_SIRGAS"
OUTPUT_DIR = ROOT / "data" / "processed" / "curitiba"
OUTPUT = OUTPUT_DIR / "area_verde_2019.geoparquet"
METADATA = OUTPUT_DIR / "area_verde_2019.json"


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
    gdf = gpd.read_file(source)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(OUTPUT, index=False, compression="zstd")

    metadata = {
        "source": "IPPUC — Dados Geográficos de Curitiba",
        "product": "Área Verde 2019",
        "url": URL,
        "source_format": "Shapefile em ZIP",
        "file": str(OUTPUT.relative_to(ROOT)),
        "crs": gdf.crs.to_string() if gdf.crs else None,
        "features": len(gdf),
        "download_script": "scripts/etl/download_area_verde_curitiba.py",
    }
    METADATA.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(f"Salvo: {OUTPUT}")
    print(f"Feições: {len(gdf):,}")


if __name__ == "__main__":
    main()
