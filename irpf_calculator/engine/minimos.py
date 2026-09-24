"""Cálculo de mínimo personal y familiar (art. 56-61 Ley 35/2006).
El mínimo NO se resta de la base para tributar aparte: técnicamente se integra
en la escala (tributa a tipo 0 la parte correspondiente al mínimo). Aquí lo
calculamos como importe agregado; la liquidación lo aplica restando su cuota
equivalente a tipo del primer tramo tanto en la parte estatal como autonómica.
"""
from __future__ import annotations
from domain.models import DatosPersonales, GradoDiscapacidad


def minimo_personal(datos: DatosPersonales, params_estatal: dict) -> float:
    mp = params_estatal["minimo_personal"]
    if datos.edad >= 75:
        return mp["mayor_75"]
    if datos.edad >= 65:
        return mp["mayor_65"]
    return mp["general"]


def minimo_descendientes(datos: DatosPersonales, params_estatal: dict) -> float:
    md = params_estatal["minimo_descendientes"]
    total = 0.0
    orden_map = {1: "primero", 2: "segundo", 3: "tercero"}
    computables = [
        d for d in datos.descendientes
        if d.convive and d.rentas_anuales < 8000 and not d.declara_irpf_propio
        and (d.edad < 25 or d.discapacidad != GradoDiscapacidad.NINGUNO)
    ]
    for i, d in enumerate(computables, start=1):
        clave = orden_map.get(i, "cuarto_y_siguientes")
        total += md[clave]
        if d.edad < 3:
            total += md["incremento_menor_3_anios"]
    return total


def minimo_ascendientes(datos: DatosPersonales, params_estatal: dict) -> float:
    ma = params_estatal["minimo_ascendientes"]
    total = 0.0
    for a in datos.ascendientes:
        if not a.convive_mas_6_meses or a.rentas_anuales >= 8000:
            continue
        if a.edad < 65:
            continue
        importe = ma["por_ascendiente"]
        if a.edad >= 75:
            importe += ma["incremento_mayor_75"]
        total += importe
    return total


def minimo_discapacidad(datos: DatosPersonales, params_estatal: dict) -> float:
    mdisc = params_estatal["minimo_discapacidad"]

    def importe_por_grado(grado: GradoDiscapacidad, movilidad_reducida: bool) -> float:
        if grado == GradoDiscapacidad.NINGUNO:
            return 0.0
        base = mdisc["grado_65_mas"] if grado == GradoDiscapacidad.G65_MAS else mdisc["grado_33_65"]
        if movilidad_reducida or grado == GradoDiscapacidad.G65_MAS:
            base += mdisc["incremento_movilidad_reducida_o_65mas"]
        return base

    total = importe_por_grado(datos.discapacidad_propia, datos.movilidad_reducida)
    for d in datos.descendientes:
        total += importe_por_grado(d.discapacidad, False)
    for a in datos.ascendientes:
        total += importe_por_grado(a.discapacidad, False)
    return total


def minimo_total(datos: DatosPersonales, params_estatal: dict) -> float:
    return (
        minimo_personal(datos, params_estatal)
        + minimo_descendientes(datos, params_estatal)
        + minimo_ascendientes(datos, params_estatal)
        + minimo_discapacidad(datos, params_estatal)
    )
