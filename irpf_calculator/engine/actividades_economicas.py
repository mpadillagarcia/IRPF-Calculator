"""Rendimientos de actividades económicas (art. 28-32 LIRPF)."""
from __future__ import annotations
from domain.models import ActividadEconomica, RegimenActividad


def rendimiento_neto_actividad(act: ActividadEconomica, params_estatal: dict) -> float:
    if act.regimen == RegimenActividad.ESTIMACION_OBJETIVA:
        # módulos: el rendimiento ya viene calculado externamente (tablas por actividad)
        return act.rendimiento_modulos or 0.0

    neto_previo = max(0.0, act.ingresos - act.gastos_deducibles)

    if act.regimen == RegimenActividad.ESTIMACION_DIRECTA_SIMPLIFICADA:
        dg = params_estatal["deduccion_generica_estimacion_directa_simplificada"]
        deduccion = min(neto_previo * dg["porcentaje"], dg["tope_anual"])
        neto_previo = max(0.0, neto_previo - deduccion)

    return neto_previo


def rendimiento_neto_actividades_economicas(
    actividades: list[ActividadEconomica], params_estatal: dict
) -> tuple[float, float]:
    """Devuelve (rendimiento_neto_total, retenciones_totales)."""
    total = sum(rendimiento_neto_actividad(a, params_estatal) for a in actividades)
    retenciones = sum(a.retenciones_soportadas for a in actividades)
    return total, retenciones
