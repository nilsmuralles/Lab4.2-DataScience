"""Configuración compartida: mismos lagos y fechas usados en la Parte I (Laboratorio 4)."""

from pathlib import Path
import os

BANDS = ["B03", "B04", "B05", "B08"]

LAGOS = {
    "atitlan": [
        "2025-01-18", "2025-04-13", "2025-05-13", "2025-07-17",
        "2025-11-21", "2025-12-29", "2026-02-12", "2026-03-24",
        "2026-04-13", "2026-04-28", "2026-07-22",
    ],
    "amatitlan": [
        "2025-01-28", "2025-04-15", "2025-04-28", "2025-11-24",
        "2026-01-08", "2026-02-02", "2026-02-07", "2026-03-29",
        "2026-04-13", "2026-04-28", "2026-06-19",
    ],
}

RASTER_CRS = "EPSG:32615"

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR = Path(os.environ.get("LAB42_DATA_DIR", _DATA_DIR))

RAW_DIR = DATA_DIR / "raw"
OUT_DIR = DATA_DIR / "processed"
