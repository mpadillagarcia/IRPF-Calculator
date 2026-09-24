"""
Modelo de dominio del IRPF. Independiente de la fuente de datos (formulario,
generador sintético, importación futura) y de la persistencia. El motor de
cálculo (engine/) solo conoce estos tipos.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Datos personales y familiares
# ---------------------------------------------------------------------------

class TipoDeclaracion(str, Enum):
    INDIVIDUAL = "individual"
    CONJUNTA_BIPARENTAL = "conjunta_biparental"
    CONJUNTA_MONOPARENTAL = "conjunta_monoparental"


class GradoDiscapacidad(str, Enum):
    NINGUNO = "ninguno"
    G33_65 = "33_65"
    G65_MAS = "65_mas"


@dataclass
class Descendiente:
    edad: int
    discapacidad: GradoDiscapacidad = GradoDiscapacidad.NINGUNO
    convive: bool = True
    rentas_anuales: float = 0.0
    declara_irpf_propio: bool = False


@dataclass
class Ascendiente:
    edad: int
    discapacidad: GradoDiscapacidad = GradoDiscapacidad.NINGUNO
    convive_mas_6_meses: bool = True
    rentas_anuales: float = 0.0


@dataclass
class DatosPersonales:
    edad: int
    ccaa_residencia: str
    tipo_declaracion: TipoDeclaracion = TipoDeclaracion.INDIVIDUAL
    discapacidad_propia: GradoDiscapacidad = GradoDiscapacidad.NINGUNO
    movilidad_reducida: bool = False
    descendientes: list[Descendiente] = field(default_factory=list)
    ascendientes: list[Ascendiente] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Rendimientos del trabajo
# ---------------------------------------------------------------------------

@dataclass
class RendimientoTrabajo:
    """Una fuente de rendimiento del trabajo (nómina, pensión, prestación...)."""
    concepto: str  # "salario", "pension_jubilacion", "prestacion_desempleo", ...
    integro_anual: float
    retenciones_soportadas: float = 0.0
    cotizaciones_seguridad_social: float = 0.0
    es_renta_irregular: bool = False
    anios_generacion: int = 1  # para reducción por irregularidad (>2 años)
    en_situacion_desempleo_con_movilidad: bool = False


# ---------------------------------------------------------------------------
# Capital inmobiliario
# ---------------------------------------------------------------------------

@dataclass
class InmuebleArrendado:
    ingresos_alquiler_anual: float
    gastos_ibi: float = 0.0
    gastos_comunidad: float = 0.0
    gastos_reparacion_conservacion: float = 0.0
    intereses_financiacion: float = 0.0
    valor_adquisicion_construccion: float = 0.0  # base para amortización 3%
    es_vivienda_habitual_inquilino: bool = True
    contrato_posterior_26_05_2025: bool = True
    zona_tensionada: bool = False
    bajada_precio_respecto_anterior: bool = False
    inquilino_18_35_anios: bool = False
    vivienda_rehabilitada_2_anios_previos: bool = False


@dataclass
class InmuebleNoArrendado:
    """Distinto de la vivienda habitual y no arrendado -> imputación de renta."""
    valor_catastral: float
    catastro_revisado_ultimos_10_anios: bool = False


# ---------------------------------------------------------------------------
# Capital mobiliario
# ---------------------------------------------------------------------------

@dataclass
class RendimientoCapitalMobiliario:
    concepto: str  # "dividendos", "intereses_cuenta", "seguro_vida", ...
    importe_bruto: float
    retenciones_soportadas: float = 0.0
    edad_constitucion_renta_vitalicia: Optional[int] = None  # solo si aplica


# ---------------------------------------------------------------------------
# Actividades económicas
# ---------------------------------------------------------------------------

class RegimenActividad(str, Enum):
    ESTIMACION_DIRECTA_SIMPLIFICADA = "directa_simplificada"
    ESTIMACION_DIRECTA_NORMAL = "directa_normal"
    ESTIMACION_OBJETIVA = "objetiva_modulos"


@dataclass
class ActividadEconomica:
    regimen: RegimenActividad
    ingresos: float
    gastos_deducibles: float = 0.0
    retenciones_soportadas: float = 0.0
    rendimiento_modulos: Optional[float] = None  # solo si es objetiva


# ---------------------------------------------------------------------------
# Ganancias y pérdidas patrimoniales
# ---------------------------------------------------------------------------

@dataclass
class TransmisionPatrimonial:
    concepto: str  # "vivienda_habitual", "otro_inmueble", "acciones_fondos", ...
    fecha_adquisicion: date
    fecha_transmision: date
    valor_adquisicion: float
    valor_transmision: float
    gastos_adquisicion: float = 0.0
    gastos_transmision: float = 0.0
    es_vivienda_habitual: bool = False
    reinversion_vivienda_habitual: float = 0.0
    reinversion_renta_vitalicia: float = 0.0


@dataclass
class PerdidaPatrimonialPendiente:
    """Pérdidas de ejercicios anteriores pendientes de compensar (hasta 4 años)."""
    anio_origen: int
    importe_pendiente: float
    tipo: str  # "general" o "ahorro"


# ---------------------------------------------------------------------------
# Reducciones y aportaciones
# ---------------------------------------------------------------------------

@dataclass
class AportacionPlanPensiones:
    importe: float
    aportacion_empresa: float = 0.0


# ---------------------------------------------------------------------------
# Otros hechos relevantes para deducciones
# ---------------------------------------------------------------------------

@dataclass
class HechosDeduccion:
    vivienda_habitual_adquirida_antes_2013: bool = False
    base_deduccion_vivienda_anual: float = 0.0
    madre_trabajadora_hijo_menor_3: bool = False
    gastos_guarderia_anual: float = 0.0
    donativos_anuales: float = 0.0
    donativos_misma_entidad_3anios_igual_o_mas: bool = False
    alquiler_vivienda_habitual_como_inquilino: float = 0.0
    inquilino_menor_36: bool = False
    inquilino_monoparental: bool = False
    inquilino_dacion_pago: bool = False


# ---------------------------------------------------------------------------
# Perfil fiscal completo
# ---------------------------------------------------------------------------

@dataclass
class PerfilFiscal:
    anio_fiscal: int
    datos_personales: DatosPersonales
    rendimientos_trabajo: list[RendimientoTrabajo] = field(default_factory=list)
    inmuebles_arrendados: list[InmuebleArrendado] = field(default_factory=list)
    inmuebles_no_arrendados: list[InmuebleNoArrendado] = field(default_factory=list)
    capital_mobiliario: list[RendimientoCapitalMobiliario] = field(default_factory=list)
    actividades_economicas: list[ActividadEconomica] = field(default_factory=list)
    transmisiones: list[TransmisionPatrimonial] = field(default_factory=list)
    perdidas_pendientes: list[PerdidaPatrimonialPendiente] = field(default_factory=list)
    aportaciones_pensiones: list[AportacionPlanPensiones] = field(default_factory=list)
    hechos_deduccion: HechosDeduccion = field(default_factory=HechosDeduccion)
    es_sintetico: bool = True  # flag obligatorio: False solo para datos reales de una persona
