"""Rendimientos del capital inmobiliario (art. 22-24 LIRPF) e imputación de
rentas inmobiliarias (art. 85 LIRPF) para inmuebles no arrendados."""
from __future__ import annotations
from domain.models import InmuebleArrendado, InmuebleNoArrendado


def _porcentaje_reduccion_alquiler(inm: InmuebleArrendado, params_estatal: dict) -> float:
    r = params_estatal["reduccion_capital_inmobiliario_alquiler_vivienda_habitual"]
    if not inm.es_vivienda_habitual_inquilino:
        return 0.0
    if not inm.contrato_posterior_26_05_2025:
        return r["contrato_anterior_26_05_2025"]
    if inm.zona_tensionada and inm.bajada_precio_respecto_anterior:
        return r["zona_tensionada_bajada_precio"]
    if inm.zona_tensionada and inm.inquilino_18_35_anios:
        return r["zona_tensionada_joven_18_35"]
    if inm.vivienda_rehabilitada_2_anios_previos:
        return r["vivienda_rehabilitada_2_anios_previos"]
    return r["general_nuevo"]


def rendimiento_neto_inmueble_arrendado(inm: InmuebleArrendado, params_estatal: dict) -> float:
    gastos = (
        inm.gastos_ibi
        + inm.gastos_comunidad
        + inm.gastos_reparacion_conservacion
        + inm.intereses_financiacion
        + inm.valor_adquisicion_construccion * 0.03  # amortización 3% anual
    )
    neto_previo = max(0.0, inm.ingresos_alquiler_anual - gastos)
    porcentaje_reduccion = _porcentaje_reduccion_alquiler(inm, params_estatal)
    return neto_previo * (1 - porcentaje_reduccion)


def rendimiento_neto_capital_inmobiliario(inmuebles: list[InmuebleArrendado], params_estatal: dict) -> float:
    return sum(rendimiento_neto_inmueble_arrendado(i, params_estatal) for i in inmuebles)


def imputacion_rentas_inmobiliarias(inmuebles: list[InmuebleNoArrendado], params_estatal: dict) -> float:
    p = params_estatal["imputacion_rentas_inmobiliarias"]
    total = 0.0
    for inm in inmuebles:
        pct = p["catastro_revisado_ultimos_10_anios"] if inm.catastro_revisado_ultimos_10_anios else p["general"]
        total += inm.valor_catastral * pct
    return total
