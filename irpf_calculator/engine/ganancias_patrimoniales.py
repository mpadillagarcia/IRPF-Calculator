"""Ganancias y pérdidas patrimoniales (art. 33-39 LIRPF), incluidas exenciones
por reinversión en vivienda habitual y por mayores de 65 años."""
from __future__ import annotations
from domain.models import (
    TransmisionPatrimonial, PerdidaPatrimonialPendiente, DatosPersonales
)


def ganancia_bruta(t: TransmisionPatrimonial) -> float:
    valor_adq_total = t.valor_adquisicion + t.gastos_adquisicion
    valor_trans_neto = t.valor_transmision - t.gastos_transmision
    return valor_trans_neto - valor_adq_total


def _exencion_por_edad_y_reinversion(
    t: TransmisionPatrimonial, ganancia: float, datos: DatosPersonales, params_estatal: dict
) -> float:
    """Devuelve el importe de ganancia EXENTO (a restar de la ganancia bruta)."""
    if ganancia <= 0:
        return 0.0

    exento = 0.0

    # Venta de vivienda habitual con reinversión en otra vivienda habitual
    if t.es_vivienda_habitual and t.reinversion_vivienda_habitual > 0:
        valor_trans_neto = t.valor_transmision - t.gastos_transmision
        proporcion_reinvertida = min(1.0, t.reinversion_vivienda_habitual / valor_trans_neto) if valor_trans_neto else 0
        exento += ganancia * proporcion_reinvertida

    ganancia_restante = ganancia - exento
    if ganancia_restante <= 0:
        return ganancia

    # Exención total por mayores de 65: venta de vivienda habitual (sin exigir reinversión)
    if t.es_vivienda_habitual and datos.edad >= 65 and params_estatal.get("exencion_venta_vivienda_habitual_mayor_65"):
        exento += ganancia_restante
        return exento

    # Exención por mayores de 65: cualquier bien, con reinversión en renta vitalicia (tope 240.000€)
    cfg = params_estatal.get("exencion_venta_cualquier_bien_reinversion_renta_vitalicia", {})
    if datos.edad >= 65 and cfg.get("aplica_mayor_65") and t.reinversion_renta_vitalicia > 0:
        tope = cfg.get("tope_reinversion", 240000)
        base_reinversion = min(t.reinversion_renta_vitalicia, tope)
        valor_trans_neto = t.valor_transmision - t.gastos_transmision
        proporcion = min(1.0, base_reinversion / valor_trans_neto) if valor_trans_neto else 0
        exento += ganancia_restante * proporcion

    return min(exento, ganancia)


def ganancia_neta_transmision(
    t: TransmisionPatrimonial, datos: DatosPersonales, params_estatal: dict
) -> float:
    bruta = ganancia_bruta(t)
    if bruta <= 0:
        return bruta  # pérdida: se devuelve negativa, se compensa después
    exento = _exencion_por_edad_y_reinversion(t, bruta, datos, params_estatal)
    return bruta - exento


def resultado_neto_ganancias_patrimoniales(
    transmisiones: list[TransmisionPatrimonial],
    perdidas_pendientes: list[PerdidaPatrimonialPendiente],
    datos: DatosPersonales,
    params_estatal: dict,
) -> float:
    """Suma ganancias/pérdidas del ejercicio + compensa pérdidas pendientes de
    hasta 4 años atrás. Todo integrado en base del ahorro (simplificación:
    no se modela aquí el matiz de ganancias <1 año a base general, derogado
    desde 2015 salvo casos concretos ya no vigentes)."""
    neto_ejercicio = sum(
        ganancia_neta_transmision(t, datos, params_estatal) for t in transmisiones
    )
    pendiente = sum(p.importe_pendiente for p in perdidas_pendientes if p.tipo == "ahorro")

    if neto_ejercicio >= 0:
        compensar = min(neto_ejercicio, pendiente)
        return neto_ejercicio - compensar
    else:
        # pérdida del ejercicio: se acumula, no reduce aquí (queda para años siguientes)
        return neto_ejercicio
