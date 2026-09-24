"""Carga de parámetros fiscales (YAML) por año y CCAA. Única fuente de verdad
para tramos, mínimos y deducciones -> actualizar un año = añadir un YAML nuevo."""
from __future__ import annotations
from pathlib import Path
import yaml

PARAMS_DIR = Path(__file__).resolve().parent.parent / "params"


def cargar_estatal(anio: int) -> dict:
    path = PARAMS_DIR / f"{anio}_estatal.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No hay parámetros estatales para {anio}. "
            f"Crea {path.name} en params/ antes de calcular ese ejercicio."
        )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cargar_autonomico(anio: int, ccaa: str) -> dict:
    slug = ccaa.lower().replace(" ", "_").replace("-", "_")
    # mapeo simple; "castilla-la mancha" o "Castilla-La Mancha" -> clm
    alias = {"castilla_la_mancha": "clm"}.get(slug, slug)
    path = PARAMS_DIR / f"{anio}_{alias}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No hay parámetros autonómicos para {ccaa} ({anio}). "
            f"Crea {path.name} en params/ antes de calcular ese ejercicio."
        )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def aplicar_escala_progresiva(base: float, tramos: list[dict]) -> float:
    """Aplica una escala progresiva por tramos (lista de {desde, hasta, tipo}).
    'hasta: null' significa sin límite superior."""
    if base <= 0:
        return 0.0
    cuota = 0.0
    for tramo in tramos:
        desde = tramo["desde"]
        hasta = tramo["hasta"]
        tipo = tramo["tipo"]
        if base <= desde:
            break
        techo_tramo = base if hasta is None else min(base, hasta)
        cuota += (techo_tramo - desde) * tipo
        if hasta is not None and base <= hasta:
            break
    return cuota
