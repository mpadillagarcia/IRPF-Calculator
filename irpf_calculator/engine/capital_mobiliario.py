"""Rendimientos del capital mobiliario (art. 25 LIRPF) -> integran la base del ahorro."""
from __future__ import annotations
from domain.models import RendimientoCapitalMobiliario


def _porcentaje_no_sujeto_renta_vitalicia(edad: int, params_estatal: dict) -> float:
    r = params_estatal["reduccion_capital_mobiliario_seguros_rentas_vitalicias"]
    if edad < 40:
        return r["menor_40"]
    if edad < 50:
        return r["entre_40_49"]
    if edad < 60:
        return r["entre_50_59"]
    if edad < 66:
        return r["entre_60_65"]
    if edad < 70:
        return r["entre_66_69"]
    return r["mayor_70"]


def rendimiento_neto_capital_mobiliario(
    items: list[RendimientoCapitalMobiliario], params_estatal: dict
) -> tuple[float, float]:
    """Devuelve (rendimiento_neto_total, retenciones_totales)."""
    total = 0.0
    retenciones = 0.0
    for item in items:
        importe = item.importe_bruto
        if item.edad_constitucion_renta_vitalicia is not None:
            pct_no_sujeto = _porcentaje_no_sujeto_renta_vitalicia(
                item.edad_constitucion_renta_vitalicia, params_estatal
            )
            importe *= (1 - pct_no_sujeto)
        total += importe
        retenciones += item.retenciones_soportadas
    return total, retenciones
