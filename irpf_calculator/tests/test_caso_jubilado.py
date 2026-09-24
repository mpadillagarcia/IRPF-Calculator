"""Caso sintético de validación: jubilado en Castilla-La Mancha con pensión,
un piso en alquiler, algo de capital mobiliario y venta de vivienda habitual
con exención por >65 años. Sirve para verificar el motor de punta a punta.
Contrastar SIEMPRE el resultado contra Renta WEB con los mismos datos."""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.models import (
    PerfilFiscal, DatosPersonales, RendimientoTrabajo, InmuebleArrendado,
    RendimientoCapitalMobiliario, TransmisionPatrimonial, TipoDeclaracion,
)
from engine.liquidacion import liquidar

perfil = PerfilFiscal(
    anio_fiscal=2026,
    es_sintetico=True,
    datos_personales=DatosPersonales(
        edad=68,
        ccaa_residencia="Castilla-La Mancha",
        tipo_declaracion=TipoDeclaracion.INDIVIDUAL,
    ),
    rendimientos_trabajo=[
        RendimientoTrabajo(
            concepto="pension_jubilacion",
            integro_anual=18000,
            retenciones_soportadas=900,
        )
    ],
    inmuebles_arrendados=[
        InmuebleArrendado(
            ingresos_alquiler_anual=6000,
            gastos_ibi=300,
            gastos_comunidad=200,
            valor_adquisicion_construccion=60000,
            es_vivienda_habitual_inquilino=True,
            contrato_posterior_26_05_2025=True,
        )
    ],
    capital_mobiliario=[
        RendimientoCapitalMobiliario(
            concepto="intereses_deposito", importe_bruto=400, retenciones_soportadas=76
        )
    ],
    transmisiones=[
        TransmisionPatrimonial(
            concepto="vivienda_habitual",
            fecha_adquisicion=date(1995, 1, 1),
            fecha_transmision=date(2026, 3, 1),
            valor_adquisicion=60000,
            valor_transmision=150000,
            es_vivienda_habitual=True,
        )
    ],
)

liq = liquidar(perfil, ccaa="Castilla-La Mancha")

print(f"Rendimiento neto trabajo/pensión:      {liq.rendimiento_neto_trabajo:>10.2f} €")
print(f"Rendimiento neto capital inmobiliario: {liq.rendimiento_neto_capital_inmobiliario:>10.2f} €")
print(f"Rendimiento neto capital mobiliario:   {liq.rendimiento_neto_capital_mobiliario:>10.2f} €")
print(f"Ganancia patrimonial neta (exenta 65): {liq.ganancias_patrimoniales_netas:>10.2f} €")
print(f"Mínimo personal y familiar:            {liq.minimo_personal_familiar:>10.2f} €")
print("-" * 50)
print(f"Cuota líquida estatal:                 {liq.cuota_liquida_estatal:>10.2f} €")
print(f"Cuota líquida autonómica:               {liq.cuota_liquida_autonomica:>10.2f} €")
print(f"Cuota resultante total:                {liq.cuota_resultante:>10.2f} €")
print(f"Retenciones soportadas:                {liq.retenciones_totales:>10.2f} €")
print("=" * 50)
signo = "A PAGAR" if liq.resultado_declaracion > 0 else "A DEVOLVER"
print(f"RESULTADO: {abs(liq.resultado_declaracion):.2f} € ({signo})")
print()
for aviso in liq.avisos:
    print(f"[AVISO] {aviso}")
