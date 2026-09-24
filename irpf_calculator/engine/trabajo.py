"""Rendimiento neto del trabajo (art. 17-20 Ley 35/2006)."""
from __future__ import annotations
from domain.models import DatosPersonales, RendimientoTrabajo


def rendimiento_integro_trabajo(rendimientos: list[RendimientoTrabajo]) -> float:
    total = 0.0
    for r in rendimientos:
        integro = r.integro_anual
        if r.es_renta_irregular and r.anios_generacion > 2:
            integro *= 0.70  # reducción 30% por generación en >2 años (con tope 300.000€, no modelado aquí)
        total += integro
    return total


def gastos_deducibles_trabajo(
    rendimientos: list[RendimientoTrabajo],
    datos: DatosPersonales,
    params_estatal: dict,
) -> float:
    gd = params_estatal["gastos_deducibles_trabajo"]
    cotizaciones = sum(r.cotizaciones_seguridad_social for r in rendimientos)
    gastos_generales = gd["general"]

    incremento = 0.0
    if any(r.en_situacion_desempleo_con_movilidad for r in rendimientos):
        incremento = max(incremento, gd["incremento_desempleo_movilidad_geografica"])
    if datos.discapacidad_propia.value == "65_mas" or datos.movilidad_reducida:
        incremento = max(incremento, gd["incremento_discapacidad_65_mas_o_movilidad"])
    elif datos.discapacidad_propia.value == "33_65":
        incremento = max(incremento, gd["incremento_discapacidad_33_65"])

    return cotizaciones + gastos_generales + incremento


def reduccion_por_rendimiento_trabajo(rendimiento_neto_previo: float, params_estatal: dict) -> float:
    """Reducción adicional decreciente para rentas de trabajo bajas/medias."""
    r = params_estatal["reduccion_rendimientos_trabajo"]
    if rendimiento_neto_previo <= 14852:
        return r["reduccion_maxima"]
    if rendimiento_neto_previo < r["rendimiento_neto_hasta"]:
        return max(0.0, r["reduccion_maxima"] - 1.14 * (rendimiento_neto_previo - 14852))
    return 0.0


def rendimiento_neto_trabajo(
    rendimientos: list[RendimientoTrabajo],
    datos: DatosPersonales,
    params_estatal: dict,
) -> tuple[float, float]:
    """Devuelve (rendimiento_neto_reducido, retenciones_totales)."""
    integro = rendimiento_integro_trabajo(rendimientos)
    gastos = gastos_deducibles_trabajo(rendimientos, datos, params_estatal)
    neto_previo = max(0.0, integro - gastos)
    reduccion = reduccion_por_rendimiento_trabajo(neto_previo, params_estatal)
    neto_final = max(0.0, neto_previo - reduccion)
    retenciones = sum(r.retenciones_soportadas for r in rendimientos)
    return neto_final, retenciones
