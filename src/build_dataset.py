from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from src.config import LAGOS, RAW_DIR

GRID_STRIDE = 5
NDWI_WATER_THRESHOLD = 0.0
REFLECTANCE_MIN, REFLECTANCE_MAX = 0.0, 1.2
CIANO_MIN, CIANO_MAX = -20.0, 150.0
BAND_NAMES = ("green", "red", "red_edge", "nir")

@dataclass
class RasterArrays:
    green: np.ndarray
    red: np.ndarray
    red_edge: np.ndarray
    nir: np.ndarray
    transform: rasterio.Affine
    crs: str

def read_raw(lago: str, fecha: str) -> RasterArrays:
    tif_path = RAW_DIR / lago / f"{fecha}.tif"
    with rasterio.open(tif_path) as src:
        raw = src.read(masked=True).astype(np.float32)
        transform, crs = src.transform, src.crs
    green, red, red_edge, nir = np.ma.filled(raw, np.nan) / 10000
    return RasterArrays(green, red, red_edge, nir, transform, crs)

def normalized_difference(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    denom = a + b
    with np.errstate(invalid="ignore", divide="ignore"):
        result = (a - b) / denom
    result = np.where(np.abs(denom) < 1e-6, np.nan, result)
    return np.clip(result, -1, 1)

def compute_indices(bands: RasterArrays) -> dict[str, np.ndarray]:
    ndvi = normalized_difference(bands.nir, bands.red)
    ndwi = normalized_difference(bands.green, bands.nir)
    ndci = normalized_difference(bands.red_edge, bands.red)
    cianobacteria = 826.57 * ndci**3 - 176.43 * ndci**2 + 19 * ndci + 4.071
    return {"ndvi": ndvi, "ndwi": ndwi, "ndci": ndci, "cianobacteria": cianobacteria}

def pixel_coords(transform: rasterio.Affine, rows: np.ndarray, cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = rasterio.transform.xy(transform, rows, cols, offset="center")
    return np.asarray(xs), np.asarray(ys)

def build_scene_dataframe(lago: str, fecha: str, grid_stride: int = GRID_STRIDE) -> pd.DataFrame:
    bands = read_raw(lago, fecha)
    indices = compute_indices(bands)

    n_rows, n_cols = bands.green.shape
    row_idx = np.arange(0, n_rows, grid_stride)
    col_idx = np.arange(0, n_cols, grid_stride)
    rr, cc = np.meshgrid(row_idx, col_idx, indexing="ij")
    rr, cc = rr.ravel(), cc.ravel()

    def sample(arr: np.ndarray) -> np.ndarray:
        return arr[rr, cc]

    green, red, red_edge, nir = (sample(bands.green), sample(bands.red), sample(bands.red_edge), sample(bands.nir))
    ndvi, ndwi, ndci, ciano = (sample(indices["ndvi"]), sample(indices["ndwi"]), sample(indices["ndci"]), sample(indices["cianobacteria"]))

    valid = (
        ~np.isnan(green) & ~np.isnan(red) & ~np.isnan(red_edge) & ~np.isnan(nir)
        & (green >= REFLECTANCE_MIN) & (green <= REFLECTANCE_MAX)
        & (red >= REFLECTANCE_MIN) & (red <= REFLECTANCE_MAX)
        & (red_edge >= REFLECTANCE_MIN) & (red_edge <= REFLECTANCE_MAX)
        & (nir >= REFLECTANCE_MIN) & (nir <= REFLECTANCE_MAX)
        & (ndwi > NDWI_WATER_THRESHOLD)
        & ~np.isnan(ciano)
        & (ciano >= CIANO_MIN) & (ciano <= CIANO_MAX)
    )

    if not valid.any():
        return pd.DataFrame()

    x_utm, y_utm = pixel_coords(bands.transform, rr[valid], cc[valid])
    transformer = Transformer.from_crs(bands.crs, "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x_utm, y_utm)

    return pd.DataFrame({
        "lago": lago,
        "fecha": fecha,
        "x_utm": x_utm,
        "y_utm": y_utm,
        "lon": lon,
        "lat": lat,
        "green": green[valid],
        "red": red[valid],
        "red_edge": red_edge[valid],
        "nir": nir[valid],
        "ndvi": ndvi[valid],
        "ndwi": ndwi[valid],
        "ndci": ndci[valid],
        "cianobacteria": ciano[valid],
    })


def build_full_dataset(grid_stride: int = GRID_STRIDE) -> pd.DataFrame:
    frames = []
    for lago, fechas in LAGOS.items():
        for fecha in fechas:
            frames.append(build_scene_dataframe(lago, fecha, grid_stride))
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["lago"] = df["lago"].astype("category")
    return df
