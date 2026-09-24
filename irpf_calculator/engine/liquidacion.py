"""Punto de entrada único: recibe un PerfilFiscal y devuelve la liquidación
completa (bases, cuotas, deducciones, resultado). Orquesta todos los módulos
del motor sin contener lógica fiscal propia."""
from __future__ import annotations
from dataclasses import dataclass, field

from domain.models import PerfilFiscal, TipoDeclaracion
from engine import parametros as P
from engine import minimos as M
from engine import trabajo as T
from engine import capital_inmobiliario as CI
from engine import capital_mobiliario as CM
from engine import actividades_economicas as AE
from engine import ganancias_patrimoniales as GP
from engine import deducciones_estatales as DE
from engine import deducciones_clm as DC


@dataclass
class Liquidacion:
    anio_fiscal: int
    # bases
    rendimiento_neto_trabajo: float = 0.0
    rendimiento_neto_capital_inmobiliario: float = 0.0
    imputacion_rentas_inmobiliarias: float = 0.0
    rendimiento_neto_actividades: float = 0.0
    base_general_previa: float = 0.0
    rendimiento_neto_capital_mobiliario: float = 0.0
    ganancias_patrimoniales_netas: float = 0.0
    base_ahorro: float = 0.0
    # mínimo
    minimo_personal_familiar: float = 0.0
    # cuotas
    cuota_integra_estatal_general: float = 0.0
    cuota_integra_autonomica_general: float = 0.0
    cuota_integra_estatal_ahorro: float = 0.0
    cuota_integra_autonomica_ahorro: float = 0.0
    cuota_minimo_estatal_general: float = 0.0
    cuota_minimo_autonomica_general: float = 0.0
    cuota_liquida_estatal: float = 0.0
    cuota_liquida_autonomica: float = 0.0
    cuota_liquida_total: float = 0.0
    # deducciones
    deducciones_estatales: float = 0.0
    deducciones_autonomicas: float = 0.0
    # resultado
    cuota_resultante: float = 0.0
    retenciones_totales: float = 0.0
    resultado_declaracion: float = 0.0  # positivo = a pagar, negativo = a devolver
    avisos: list[str] = field(default_factory=list)


def liquidar(perfil: PerfilFiscal, ccaa: str = "Castilla-La Mancha") -> Liquidacion:
    anio = perfil.anio_fiscal
    pe = P.cargar_estatal(anio)
    pc = P.cargar_autonomico(anio, ccaa)
    datos = perfil.datos_personales

    liq = Liquidacion(anio_fiscal=anio)

    # --- Rendimientos del trabajo ---
    liq.rendimiento_neto_trabajo, ret_trabajo = T.rendimiento_neto_trabajo(
        perfil.rendimientos_trabajo, datos, pe
    )

    # --- Capital inmobiliario ---
    liq.rendimiento_neto_capital_inmobiliario = CI.rendimiento_neto_capital_inmobiliario(
        perfil.inmuebles_arrendados, pe
    )
    liq.imputacion_rentas_inmobiliarias = CI.imputacion_rentas_inmobiliarias(
        perfil.inmuebles_no_arrendados, pe
    )

    # --- Actividades económicas ---
    liq.rendimiento_neto_actividades, ret_actividades = AE.rendimiento_neto_actividades_economicas(
        perfil.actividades_economicas, pe
    )

    # --- Base general (antes de reducciones por aportaciones) ---
    liq.base_general_previa = (
        liq.rendimiento_neto_trabajo
        + liq.rendimiento_neto_capital_inmobiliario
        + liq.imputacion_rentas_inmobiliarias
        + liq.rendimiento_neto_actividades
    )
    reduccion_pensiones = sum(
        min(a.importe, 1500) for a in perfil.aportaciones_pensiones
    )
    base_general = max(0.0, liq.base_general_previa - reduccion_pensiones)

    # --- Capital mobiliario y ganancias patrimoniales -> base del ahorro ---
    liq.rendimiento_neto_capital_mobiliario, ret_capital_mob = CM.rendimiento_neto_capital_mobiliario(
        perfil.capital_mobiliario, pe
    )
    liq.ganancias_patrimoniales_netas = GP.resultado_neto_ganancias_patrimoniales(
        perfil.transmisiones, perfil.perdidas_pendientes, datos, pe
    )
    liq.base_ahorro = max(
        0.0, liq.rendimiento_neto_capital_mobiliario + liq.ganancias_patrimoniales_netas
    )

    # --- Reducción por declaración conjunta ---
    if datos.tipo_declaracion == TipoDeclaracion.CONJUNTA_BIPARENTAL:
        base_general = max(0.0, base_general - pe["declaracion_conjunta"]["reduccion_base_imponible"])
    elif datos.tipo_declaracion == TipoDeclaracion.CONJUNTA_MONOPARENTAL:
        base_general = max(0.0, base_general - pe["declaracion_conjunta"]["reduccion_base_imponible_monoparental"])

    # --- Mínimo personal y familiar ---
    liq.minimo_personal_familiar = M.minimo_total(datos, pe)

    # --- Cuotas íntegras (escala general: estatal + autonómica CLM) ---
    liq.cuota_integra_estatal_general = P.aplicar_escala_progresiva(
        base_general, pe["escala_general_estatal"]["tramos"]
    )
    liq.cuota_integra_autonomica_general = P.aplicar_escala_progresiva(
        base_general, pc["escala_general_autonomica"]["tramos"]
    )

    # --- Cuota correspondiente al mínimo (se resta = tributa a tipo 0) ---
    liq.cuota_minimo_estatal_general = P.aplicar_escala_progresiva(
        min(liq.minimo_personal_familiar, base_general), pe["escala_general_estatal"]["tramos"]
    )
    liq.cuota_minimo_autonomica_general = P.aplicar_escala_progresiva(
        min(liq.minimo_personal_familiar, base_general), pc["escala_general_autonomica"]["tramos"]
    )

    # --- Base del ahorro: escala (mínimo remanente se aplica primero al general, resto aquí) ---
    minimo_remanente = max(0.0, liq.minimo_personal_familiar - base_general)
    liq.cuota_integra_estatal_ahorro = P.aplicar_escala_progresiva(
        liq.base_ahorro, pe["escala_ahorro_estatal"]["tramos"]
    )
    liq.cuota_integra_autonomica_ahorro = P.aplicar_escala_progresiva(
        liq.base_ahorro, pc["escala_ahorro_autonomica"]["tramos"]
    )
    cuota_minimo_ahorro_estatal = P.aplicar_escala_progresiva(
        min(minimo_remanente, liq.base_ahorro), pe["escala_ahorro_estatal"]["tramos"]
    )
    cuota_minimo_ahorro_autonomica = P.aplicar_escala_progresiva(
        min(minimo_remanente, liq.base_ahorro), pc["escala_ahorro_autonomica"]["tramos"]
    )

    # --- Cuotas líquidas (íntegra - cuota del mínimo - deducciones) ---
    liq.deducciones_estatales = DE.total_deducciones_estatales(perfil, pe)
    liq.deducciones_autonomicas = DC.total_deducciones_clm(
        perfil, pc, base_imponible_total=base_general + liq.base_ahorro
    )

    cuota_estatal_bruta = (
        liq.cuota_integra_estatal_general - liq.cuota_minimo_estatal_general
        + liq.cuota_integra_estatal_ahorro - cuota_minimo_ahorro_estatal
    )
    cuota_autonomica_bruta = (
        liq.cuota_integra_autonomica_general - liq.cuota_minimo_autonomica_general
        + liq.cuota_integra_autonomica_ahorro - cuota_minimo_ahorro_autonomica
    )

    liq.cuota_liquida_estatal = max(0.0, cuota_estatal_bruta - liq.deducciones_estatales)
    liq.cuota_liquida_autonomica = max(0.0, cuota_autonomica_bruta - liq.deducciones_autonomicas)
    liq.cuota_liquida_total = liq.cuota_liquida_estatal + liq.cuota_liquida_autonomica

    # --- Deducciones "negativas" (familia numerosa/discapacidad): se cobran igual ---
    deduccion_negativa = DE.deduccion_familia_numerosa_y_discapacidad(perfil, pe) if False else 0.0
    # (ya incluida arriba en deducciones_estatales; si supera la cuota, se cobra el exceso -> TODO afinar)

    liq.cuota_resultante = liq.cuota_liquida_total
    liq.retenciones_totales = ret_trabajo + ret_actividades + ret_capital_mob
    liq.resultado_declaracion = liq.cuota_resultante - liq.retenciones_totales

    liq.avisos.append(
        "Motor de cálculo propio, sin homologar por la AEAT. Contrastar siempre "
        "contra el simulador oficial (Renta WEB) antes de presentar."
    )
    if any(getattr(a, "regimen", None) and a.regimen.value == "objetiva_modulos" for a in perfil.actividades_economicas):
        liq.avisos.append("Régimen de módulos: verificar tabla de módulos aplicable a la actividad concreta.")

    return liq
