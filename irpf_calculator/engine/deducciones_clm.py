"""Deducciones autonómicas de Castilla-La Mancha en cuota autonómica.
NOTA: cubre las deducciones de mayor probabilidad de uso. Las marcadas
'pendiente_verificar' en el YAML no están implementadas aún -> revisar
params/2026_clm.yaml antes de dar cobertura por completa."""
from __future__ import annotations
from domain.models import PerfilFiscal, TipoDeclaracion


def deduccion_nacimiento_adopcion(perfil: PerfilFiscal, params_clm: dict, nacidos_este_anio: int) -> float:
    if nacidos_este_anio <= 0:
        return 0.0
    d = params_clm["deducciones_autonomicas"]["nacimiento_adopcion"]
    if nacidos_este_anio == 1:
        return d["un_hijo"]
    if nacidos_este_anio == 2:
        return d["dos_hijos"]
    return d["tres_hijos"]  # 3 o más


def deduccion_familia_numerosa(perfil: PerfilFiscal, params_clm: dict, es_especial: bool, hijo_discapacidad_65: bool) -> float:
    d = params_clm["deducciones_autonomicas"]["familia_numerosa"]
    base = d["especial"] if es_especial else d["general"]
    if hijo_discapacidad_65:
        base += d["incremento_discapacidad_65_especial"] if es_especial else d["incremento_discapacidad_65_general"]
    return base


def deduccion_por_descendiente(perfil: PerfilFiscal, params_clm: dict, base_imponible_total: float) -> float:
    d = params_clm["deducciones_autonomicas"]
    conjunta = perfil.datos_personales.tipo_declaracion != TipoDeclaracion.INDIVIDUAL
    tabla = d["por_descendiente_declaracion_conjunta"] if conjunta else d["por_descendiente_declaracion_individual"]

    limite_por_hijo = 0.0
    for tramo in tabla["tramos"]:
        if base_imponible_total <= tramo["base_imponible_hasta"]:
            limite_por_hijo = tramo["limite_por_hijo"]
            break

    n_descendientes = len(perfil.datos_personales.descendientes)
    return limite_por_hijo * n_descendientes


def deduccion_alquiler_vivienda_habitual(perfil: PerfilFiscal, params_clm: dict) -> float:
    h = perfil.hechos_deduccion
    if h.alquiler_vivienda_habitual_como_inquilino <= 0:
        return 0.0
    d = params_clm["deducciones_autonomicas"]["alquiler_vivienda_habitual"]

    colectivo_especial = (
        h.inquilino_menor_36
        or h.inquilino_monoparental
        or h.inquilino_dacion_pago
        or any(dsc for dsc in perfil.datos_personales.descendientes)  # aproximación familia numerosa
        or perfil.datos_personales.discapacidad_propia.value == "65_mas"
    )
    tope = d["tope_colectivos_especiales"] if colectivo_especial else d["tope_general"]
    deduccion = h.alquiler_vivienda_habitual_como_inquilino * d["porcentaje"]
    return min(deduccion, tope)


def total_deducciones_clm(
    perfil: PerfilFiscal,
    params_clm: dict,
    base_imponible_total: float,
    nacidos_este_anio: int = 0,
    familia_numerosa_especial: bool = False,
    familia_numerosa_hijo_discapacidad_65: bool = False,
    es_familia_numerosa: bool = False,
) -> float:
    total = deduccion_por_descendiente(perfil, params_clm, base_imponible_total)
    total += deduccion_alquiler_vivienda_habitual(perfil, params_clm)
    total += deduccion_nacimiento_adopcion(perfil, params_clm, nacidos_este_anio)
    if es_familia_numerosa:
        total += deduccion_familia_numerosa(
            perfil, params_clm, familia_numerosa_especial, familia_numerosa_hijo_discapacidad_65
        )
    return total
