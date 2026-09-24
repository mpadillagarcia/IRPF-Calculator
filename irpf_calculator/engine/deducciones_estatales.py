"""Deducciones estatales en cuota íntegra (post-mínimo, post-escala)."""
from __future__ import annotations
from domain.models import PerfilFiscal


def deduccion_vivienda_habitual_transitoria(perfil: PerfilFiscal, params_estatal: dict) -> float:
    h = perfil.hechos_deduccion
    if not h.vivienda_habitual_adquirida_antes_2013:
        return 0.0
    d = params_estatal["deducciones_estatales"]["vivienda_habitual_regimen_transitorio"]
    base = min(h.base_deduccion_vivienda_anual, d["base_maxima_anual"])
    return base * d["porcentaje"]


def deduccion_maternidad(perfil: PerfilFiscal, params_estatal: dict) -> float:
    h = perfil.hechos_deduccion
    if not h.madre_trabajadora_hijo_menor_3:
        return 0.0
    d = params_estatal["deducciones_estatales"]["maternidad"]
    importe = d["importe_anual"]
    if h.gastos_guarderia_anual > 0:
        importe += min(h.gastos_guarderia_anual, d["incremento_guarderia_menor_3"])
    return importe


def deduccion_familia_numerosa_y_discapacidad(perfil: PerfilFiscal, params_estatal: dict) -> float:
    """Deducciones 'negativas': se cobran aunque no haya cuota positiva suficiente."""
    d = params_estatal["deducciones_estatales"]
    total = 0.0
    descendientes = perfil.datos_personales.descendientes
    ascendientes = perfil.datos_personales.ascendientes

    tiene_discapacidad_descendiente = any(dsc.discapacidad.value != "ninguno" for dsc in descendientes)
    tiene_discapacidad_ascendiente = any(asc.discapacidad.value != "ninguno" for asc in ascendientes)

    if tiene_discapacidad_descendiente or tiene_discapacidad_ascendiente:
        total += d["discapacidad_descendiente_o_ascendiente"]["importe_anual"]

    return total


def deduccion_donativos(perfil: PerfilFiscal, params_estatal: dict) -> float:
    h = perfil.hechos_deduccion
    if h.donativos_anuales <= 0:
        return 0.0
    d = params_estatal["deducciones_estatales"]["donativos"]
    primer_tramo = min(h.donativos_anuales, 150)
    resto = max(0.0, h.donativos_anuales - 150)
    pct_resto = d["tramo_2_resto_recurrente_3anios"] if h.donativos_misma_entidad_3anios_igual_o_mas else d["tramo_2_resto"]
    return primer_tramo * d["tramo_1_hasta_150"] + resto * pct_resto


def total_deducciones_estatales(perfil: PerfilFiscal, params_estatal: dict) -> float:
    return (
        deduccion_vivienda_habitual_transitoria(perfil, params_estatal)
        + deduccion_maternidad(perfil, params_estatal)
        + deduccion_familia_numerosa_y_discapacidad(perfil, params_estatal)
        + deduccion_donativos(perfil, params_estatal)
    )
