"""Interfaz de la calculadora de IRPF. Formulario guiado que construye un
PerfilFiscal y ejecuta el motor de liquidación. Ejecutar con:
    streamlit run app.py
(o usando run.bat, que instala dependencias automáticamente)."""
import sys
import pickle
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from domain.models import (
    PerfilFiscal, DatosPersonales, Descendiente, Ascendiente, GradoDiscapacidad,
    TipoDeclaracion, RendimientoTrabajo, InmuebleArrendado, InmuebleNoArrendado,
    RendimientoCapitalMobiliario, RegimenActividad, ActividadEconomica,
    TransmisionPatrimonial, PerdidaPatrimonialPendiente, AportacionPlanPensiones,
    HechosDeduccion,
)
from engine.liquidacion import liquidar

st.set_page_config(page_title="Calculadora IRPF", layout="wide")

DISCAPACIDAD_LABELS = {
    "Ninguna": GradoDiscapacidad.NINGUNO,
    "33% - 65%": GradoDiscapacidad.G33_65,
    "65% o más": GradoDiscapacidad.G65_MAS,
}

for key, default in [
    ("descendientes", []), ("ascendientes", []), ("rentas_trabajo", []),
    ("inmuebles_alquilados", []), ("inmuebles_no_alquilados", []),
    ("capital_mobiliario", []), ("actividades", []), ("transmisiones", []),
    ("perdidas_pendientes", []), ("aportaciones", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🧾 Calculadora IRPF — Castilla-La Mancha")
st.caption(
    "Herramienta orientativa de cálculo. No constituye asesoramiento fiscal "
    "profesional ni presentación oficial. Verifica siempre el resultado en "
    "Renta WEB (sede.agenciatributaria.gob.es) antes de presentar la declaración."
)

LIST_KEYS = [
    "descendientes", "ascendientes", "rentas_trabajo", "inmuebles_alquilados",
    "inmuebles_no_alquilados", "capital_mobiliario", "actividades",
    "transmisiones", "perdidas_pendientes", "aportaciones",
]
SCALAR_KEYS = [
    "edad", "tipo_decl", "disc_propia", "movilidad",
    "h_vivienda_antes_2013", "h_base_vivienda", "h_madre_trabajadora",
    "h_gastos_guarderia", "h_donativos", "h_donativos_recurrente",
    "h_alquiler_inquilino", "h_inquilino_menor_36", "h_inquilino_monoparental",
    "h_inquilino_dacion",
]

with st.sidebar:
    st.header("Perfil")
    perfil_bytes = pickle.dumps({k: st.session_state.get(k) for k in LIST_KEYS + SCALAR_KEYS})
    st.download_button(
        "💾 Guardar perfil (.irpf)", data=perfil_bytes,
        file_name="perfil_irpf.irpf", mime="application/octet-stream",
        help="Descarga todos los datos introducidos para poder cargarlos más tarde sin repetirlos.",
    )
    perfil_cargado = st.file_uploader("📂 Cargar perfil (.irpf)", type=["irpf"])
    if perfil_cargado is not None:
        if st.button("Confirmar carga (sobrescribe lo actual)"):
            datos_cargados = pickle.loads(perfil_cargado.read())
            for k, v in datos_cargados.items():
                st.session_state[k] = v
            st.rerun()
    st.divider()
    if st.button("🔄 Reiniciar todo", type="secondary"):
        for k in LIST_KEYS:
            st.session_state[k] = []
        for k in SCALAR_KEYS:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

tabs = st.tabs([
    "1. Datos personales", "2. Trabajo/Pensión", "3. Capital inmobiliario",
    "4. Capital mobiliario", "5. Actividades económicas", "6. Ganancias patrimoniales",
    "7. Aportaciones y deducciones", "8. Resultado",
])

# ---------------------------------------------------------------------------
# 1. Datos personales
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Datos del contribuyente")
    col1, col2 = st.columns(2)
    with col1:
        edad = st.number_input("Edad", min_value=16, max_value=110, value=65, key="edad")
        tipo_decl_label = st.selectbox(
            "Tipo de declaración",
            ["Individual", "Conjunta (biparental)", "Conjunta (monoparental)"],
            key="tipo_decl",
        )
    with col2:
        discapacidad_propia_label = st.selectbox(
            "Grado de discapacidad propio", list(DISCAPACIDAD_LABELS.keys()), key="disc_propia"
        )
        movilidad_reducida = st.checkbox("Movilidad reducida", key="movilidad")

    st.markdown("**Descendientes a cargo**")
    st.caption(
        "Los valores del formulario son solo la plantilla para el SIGUIENTE alta — "
        "no se añade nada hasta que pulses 'Añadir'. La lista real es la que ves "
        "debajo del formulario."
    )
    with st.form("form_descendiente", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        d_edad = c1.number_input("Edad", min_value=0, max_value=30, value=0, key="d_edad")
        d_disc = c2.selectbox("Discapacidad", list(DISCAPACIDAD_LABELS.keys()), key="d_disc")
        d_rentas = c3.number_input("Rentas anuales (€)", min_value=0.0, value=0.0, key="d_rentas")
        d_convive = c4.checkbox("Convive", value=True, key="d_convive")
        if st.form_submit_button("➕ Añadir descendiente"):
            st.session_state.descendientes.append(Descendiente(
                edad=d_edad, discapacidad=DISCAPACIDAD_LABELS[d_disc],
                convive=d_convive, rentas_anuales=d_rentas,
            ))
            st.rerun()
    if not st.session_state.descendientes:
        st.info("✅ No hay ningún descendiente añadido. La lista está vacía.")
    else:
        st.markdown(f"**Descendientes añadidos: {len(st.session_state.descendientes)}**")
        for i, d in enumerate(st.session_state.descendientes):
            c1, c2 = st.columns([5, 1])
            c1.write(f"{i+1}. Edad {d.edad}, discapacidad {d.discapacidad.value}, rentas {d.rentas_anuales}€, convive: {'sí' if d.convive else 'no'}")
            if c2.button("🗑️ Eliminar", key=f"del_desc_{i}"):
                st.session_state.descendientes.pop(i)
                st.rerun()

    st.markdown("**Ascendientes a cargo**")
    st.caption(
        "Igual que arriba: rellenar el formulario NO añade nada por sí solo. "
        "Si no pulsas 'Añadir ascendiente', la lista sigue vacía aunque el "
        "campo Edad muestre un valor por defecto."
    )
    with st.form("form_ascendiente", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        a_edad = c1.number_input("Edad", min_value=50, max_value=110, value=75, key="a_edad")
        a_disc = c2.selectbox("Discapacidad", list(DISCAPACIDAD_LABELS.keys()), key="a_disc")
        a_rentas = c3.number_input("Rentas anuales (€)", min_value=0.0, value=0.0, key="a_rentas")
        a_convive = c4.checkbox("Convive >6 meses", value=True, key="a_convive")
        if st.form_submit_button("➕ Añadir ascendiente"):
            st.session_state.ascendientes.append(Ascendiente(
                edad=a_edad, discapacidad=DISCAPACIDAD_LABELS[a_disc],
                convive_mas_6_meses=a_convive, rentas_anuales=a_rentas,
            ))
            st.rerun()
    if not st.session_state.ascendientes:
        st.info("✅ No hay ningún ascendiente añadido. La lista está vacía.")
    else:
        st.markdown(f"**Ascendientes añadidos: {len(st.session_state.ascendientes)}**")
        for i, a in enumerate(st.session_state.ascendientes):
            c1, c2 = st.columns([5, 1])
            c1.write(f"{i+1}. Edad {a.edad}, discapacidad {a.discapacidad.value}, rentas {a.rentas_anuales}€")
            if c2.button("🗑️ Eliminar", key=f"del_asc_{i}"):
                st.session_state.ascendientes.pop(i)
                st.rerun()

# ---------------------------------------------------------------------------
# 2. Rendimientos del trabajo
# ---------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Rendimientos del trabajo (salarios, pensiones, prestaciones)")
    st.caption(
        "Añade una entrada por cada pagador. Puedes introducir los datos tal "
        "como salen en tu nómina (mensual) o directamente en anual."
    )

    modo_entrada = st.radio(
        "Modo de introducción de datos",
        ["Mensual (como en la nómina)", "Anual (directo)"],
        horizontal=True, key="t_modo",
    )

    with st.form("form_trabajo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t_concepto = c1.selectbox("Concepto", ["salario", "pension_jubilacion", "prestacion_desempleo", "otro"], key="t_concepto")

        if modo_entrada == "Mensual (como en la nómina)":
            c2a, c2b = c2.columns(2) if False else (c2, None)
            t_pagas = c1.selectbox("Número de pagas al año", [12, 14, 15], index=0, key="t_pagas")
            c3, c4 = st.columns(2)
            t_bruto_mensual = c3.number_input("Bruto mensual en nómina (€)", min_value=0.0, value=0.0, key="t_bruto_mensual")
            t_retencion_mensual = c4.number_input("Retención IRPF mensual en nómina (€)", min_value=0.0, value=0.0, key="t_retencion_mensual")
            t_cotiz_mensual = st.number_input(
                "Cotización SS mensual (€) — la ves en tu nómina como 'aportación trabajador'",
                min_value=0.0, value=0.0, key="t_cotiz_mensual",
            )
            t_integro = t_bruto_mensual * t_pagas
            t_retenciones = t_retencion_mensual * t_pagas
            t_cotizaciones = t_cotiz_mensual * t_pagas
            st.caption(f"→ Equivale a: {t_integro:,.2f} € íntegros/año · {t_retenciones:,.2f} € retenidos/año · {t_cotizaciones:,.2f} € cotizados/año")
        else:
            c3, c4 = st.columns(2)
            t_integro = c3.number_input("Importe íntegro anual (€)", min_value=0.0, value=0.0, key="t_integro")
            t_retenciones = c4.number_input("Retenciones soportadas anuales (€)", min_value=0.0, value=0.0, key="t_retenciones")
            t_cotizaciones = st.number_input("Cotizaciones SS anuales (€)", min_value=0.0, value=0.0, key="t_cotiz")

        c5, c6 = st.columns(2)
        t_irregular = c5.checkbox("Renta irregular (>2 años)", key="t_irregular")
        t_desempleo_mov = c6.checkbox("Desempleo con movilidad geográfica", key="t_desempleo")

        if st.form_submit_button("➕ Añadir rendimiento del trabajo"):
            st.session_state.rentas_trabajo.append(RendimientoTrabajo(
                concepto=t_concepto, integro_anual=t_integro,
                retenciones_soportadas=t_retenciones, cotizaciones_seguridad_social=t_cotizaciones,
                es_renta_irregular=t_irregular, en_situacion_desempleo_con_movilidad=t_desempleo_mov,
            ))
            st.rerun()

    if not st.session_state.rentas_trabajo:
        st.info("✅ No hay ningún pagador añadido todavía.")
    else:
        st.markdown(f"**Pagadores añadidos: {len(st.session_state.rentas_trabajo)}**")
        if len(st.session_state.rentas_trabajo) > 1:
            total_integro = sum(r.integro_anual for r in st.session_state.rentas_trabajo)
            segundo_pagador_max = sorted((r.integro_anual for r in st.session_state.rentas_trabajo), reverse=True)[1]
            if segundo_pagador_max > 1500:
                st.warning(
                    f"Tienes más de un pagador y el segundo (u otros) supera 1.500€ ({segundo_pagador_max:,.2f}€). "
                    f"El límite para estar obligado a declarar baja de 22.000€ a un umbral menor si el total "
                    f"({total_integro:,.2f}€) lo supera — revisa tu obligación de declarar."
                )
        for i, r in enumerate(st.session_state.rentas_trabajo):
            c1, c2 = st.columns([5, 1])
            c1.write(f"{i+1}. {r.concepto}: {r.integro_anual:,.2f}€ íntegros/año, {r.retenciones_soportadas:,.2f}€ retenidos/año, {r.cotizaciones_seguridad_social:,.2f}€ cotizados/año")
            if c2.button("🗑️ Eliminar", key=f"del_trab_{i}"):
                st.session_state.rentas_trabajo.pop(i)
                st.rerun()

# ---------------------------------------------------------------------------
# 3. Capital inmobiliario
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Inmuebles en alquiler")
    with st.form("form_inmueble_alquilado", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        i_ingresos = c1.number_input("Ingresos alquiler anual (€)", min_value=0.0, value=0.0, key="i_ingresos")
        i_ibi = c2.number_input("IBI anual (€)", min_value=0.0, value=0.0, key="i_ibi")
        i_comunidad = c3.number_input("Comunidad anual (€)", min_value=0.0, value=0.0, key="i_comunidad")
        c4, c5, c6 = st.columns(3)
        i_reparacion = c4.number_input("Reparación/conservación (€)", min_value=0.0, value=0.0, key="i_reparacion")
        i_intereses = c5.number_input("Intereses financiación (€)", min_value=0.0, value=0.0, key="i_intereses")
        i_valor_adq = c6.number_input("Valor adquisición/construcción (€, para amortización)", min_value=0.0, value=0.0, key="i_valor_adq")
        c7, c8, c9 = st.columns(3)
        i_es_vivienda_habitual = c7.checkbox("Es vivienda habitual del inquilino", value=True, key="i_vh")
        i_contrato_nuevo = c8.checkbox("Contrato posterior a 26/05/2025", value=True, key="i_contrato_nuevo")
        i_zona_tensionada = c9.checkbox("Zona tensionada", key="i_zona_tens")
        c10, c11 = st.columns(2)
        i_joven = c10.checkbox("Inquilino 18-35 años", key="i_joven")
        i_rehabilitada = c11.checkbox("Vivienda rehabilitada últimos 2 años", key="i_rehab")
        if st.form_submit_button("➕ Añadir inmueble alquilado"):
            st.session_state.inmuebles_alquilados.append(InmuebleArrendado(
                ingresos_alquiler_anual=i_ingresos, gastos_ibi=i_ibi, gastos_comunidad=i_comunidad,
                gastos_reparacion_conservacion=i_reparacion, intereses_financiacion=i_intereses,
                valor_adquisicion_construccion=i_valor_adq, es_vivienda_habitual_inquilino=i_es_vivienda_habitual,
                contrato_posterior_26_05_2025=i_contrato_nuevo, zona_tensionada=i_zona_tensionada,
                inquilino_18_35_anios=i_joven, vivienda_rehabilitada_2_anios_previos=i_rehabilitada,
            ))
            st.rerun()
    for i, inm in enumerate(st.session_state.inmuebles_alquilados):
        c1, c2 = st.columns([5, 1])
        c1.write(f"Inmueble {i+1}: {inm.ingresos_alquiler_anual}€/año ingresos")
        if c2.button("🗑️", key=f"del_inm_{i}"):
            st.session_state.inmuebles_alquilados.pop(i)
            st.rerun()

    st.subheader("Inmuebles NO alquilados (distintos de vivienda habitual)")
    with st.form("form_inmueble_no_alquilado", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n_valor = c1.number_input("Valor catastral (€)", min_value=0.0, value=0.0, key="n_valor")
        n_revisado = c2.checkbox("Catastro revisado últimos 10 años", key="n_revisado")
        if st.form_submit_button("➕ Añadir inmueble no alquilado"):
            st.session_state.inmuebles_no_alquilados.append(InmuebleNoArrendado(
                valor_catastral=n_valor, catastro_revisado_ultimos_10_anios=n_revisado,
            ))
            st.rerun()
    for i, inm in enumerate(st.session_state.inmuebles_no_alquilados):
        c1, c2 = st.columns([5, 1])
        c1.write(f"Inmueble {i+1}: valor catastral {inm.valor_catastral}€")
        if c2.button("🗑️", key=f"del_ninm_{i}"):
            st.session_state.inmuebles_no_alquilados.pop(i)
            st.rerun()

# ---------------------------------------------------------------------------
# 4. Capital mobiliario
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Capital mobiliario (dividendos, intereses, seguros)")
    with st.form("form_capital_mob", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cm_concepto = c1.selectbox("Concepto", ["dividendos", "intereses_cuenta", "seguro_vida_renta_vitalicia", "otro"], key="cm_concepto")
        cm_importe = c2.number_input("Importe bruto (€)", min_value=0.0, value=0.0, key="cm_importe")
        cm_retenciones = c3.number_input("Retenciones soportadas (€)", min_value=0.0, value=0.0, key="cm_retenciones")
        cm_edad_renta = st.number_input(
            "Edad al constituir la renta vitalicia (solo si aplica; 0 = no aplica)",
            min_value=0, max_value=110, value=0, key="cm_edad_renta",
        )
        if st.form_submit_button("➕ Añadir capital mobiliario"):
            st.session_state.capital_mobiliario.append(RendimientoCapitalMobiliario(
                concepto=cm_concepto, importe_bruto=cm_importe, retenciones_soportadas=cm_retenciones,
                edad_constitucion_renta_vitalicia=cm_edad_renta if cm_edad_renta > 0 else None,
            ))
            st.rerun()
    for i, cm in enumerate(st.session_state.capital_mobiliario):
        c1, c2 = st.columns([5, 1])
        c1.write(f"{cm.concepto}: {cm.importe_bruto}€ bruto")
        if c2.button("🗑️", key=f"del_cm_{i}"):
            st.session_state.capital_mobiliario.pop(i)
            st.rerun()

# ---------------------------------------------------------------------------
# 5. Actividades económicas
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Actividades económicas (autónomos)")
    with st.form("form_actividad", clear_on_submit=True):
        c1, c2 = st.columns(2)
        act_regimen_label = c1.selectbox(
            "Régimen", ["Estimación directa simplificada", "Estimación directa normal", "Estimación objetiva (módulos)"],
            key="act_regimen",
        )
        act_retenciones = c2.number_input("Retenciones soportadas (€)", min_value=0.0, value=0.0, key="act_retenciones")
        c3, c4 = st.columns(2)
        act_ingresos = c3.number_input("Ingresos (€)", min_value=0.0, value=0.0, key="act_ingresos")
        act_gastos = c4.number_input("Gastos deducibles (€)", min_value=0.0, value=0.0, key="act_gastos")
        act_modulos = st.number_input("Rendimiento por módulos (€, solo si objetiva)", min_value=0.0, value=0.0, key="act_modulos")
        if st.form_submit_button("➕ Añadir actividad"):
            regimen_map = {
                "Estimación directa simplificada": RegimenActividad.ESTIMACION_DIRECTA_SIMPLIFICADA,
                "Estimación directa normal": RegimenActividad.ESTIMACION_DIRECTA_NORMAL,
                "Estimación objetiva (módulos)": RegimenActividad.ESTIMACION_OBJETIVA,
            }
            st.session_state.actividades.append(ActividadEconomica(
                regimen=regimen_map[act_regimen_label], ingresos=act_ingresos, gastos_deducibles=act_gastos,
                retenciones_soportadas=act_retenciones, rendimiento_modulos=act_modulos if act_modulos > 0 else None,
            ))
            st.rerun()
    for i, a in enumerate(st.session_state.actividades):
        c1, c2 = st.columns([5, 1])
        c1.write(f"Actividad {i+1}: {a.regimen.value}, ingresos {a.ingresos}€")
        if c2.button("🗑️", key=f"del_act_{i}"):
            st.session_state.actividades.pop(i)
            st.rerun()

# ---------------------------------------------------------------------------
# 6. Ganancias patrimoniales
# ---------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Ventas / transmisiones patrimoniales")
    with st.form("form_transmision", clear_on_submit=True):
        c1, c2 = st.columns(2)
        tr_concepto = c1.selectbox("Concepto", ["vivienda_habitual", "otro_inmueble", "acciones_fondos", "otro"], key="tr_concepto")
        tr_es_vh = c2.checkbox("Es vivienda habitual", key="tr_vh")
        c3, c4 = st.columns(2)
        tr_fecha_adq = c3.date_input("Fecha adquisición", value=date(2000, 1, 1), key="tr_fecha_adq")
        tr_fecha_trans = c4.date_input("Fecha transmisión", value=date.today(), key="tr_fecha_trans")
        c5, c6 = st.columns(2)
        tr_valor_adq = c5.number_input("Valor adquisición (€)", min_value=0.0, value=0.0, key="tr_valor_adq")
        tr_valor_trans = c6.number_input("Valor transmisión (€)", min_value=0.0, value=0.0, key="tr_valor_trans")
        c7, c8 = st.columns(2)
        tr_reinversion_vh = c7.number_input("Reinversión en nueva vivienda habitual (€)", min_value=0.0, value=0.0, key="tr_reinv_vh")
        tr_reinversion_rv = c8.number_input("Reinversión en renta vitalicia (€, solo si >65)", min_value=0.0, value=0.0, key="tr_reinv_rv")
        if st.form_submit_button("➕ Añadir transmisión"):
            st.session_state.transmisiones.append(TransmisionPatrimonial(
                concepto=tr_concepto, fecha_adquisicion=tr_fecha_adq, fecha_transmision=tr_fecha_trans,
                valor_adquisicion=tr_valor_adq, valor_transmision=tr_valor_trans,
                es_vivienda_habitual=tr_es_vh, reinversion_vivienda_habitual=tr_reinversion_vh,
                reinversion_renta_vitalicia=tr_reinversion_rv,
            ))
            st.rerun()
    for i, t in enumerate(st.session_state.transmisiones):
        c1, c2 = st.columns([5, 1])
        c1.write(f"{t.concepto}: compra {t.valor_adquisicion}€ → venta {t.valor_transmision}€")
        if c2.button("🗑️", key=f"del_tr_{i}"):
            st.session_state.transmisiones.pop(i)
            st.rerun()

    st.subheader("Pérdidas patrimoniales pendientes de años anteriores")
    with st.form("form_perdida", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        p_anio = c1.number_input("Año de origen", min_value=2020, max_value=2026, value=2024, key="p_anio")
        p_importe = c2.number_input("Importe pendiente (€)", min_value=0.0, value=0.0, key="p_importe")
        p_tipo = c3.selectbox("Tipo", ["ahorro", "general"], key="p_tipo")
        if st.form_submit_button("➕ Añadir pérdida pendiente"):
            st.session_state.perdidas_pendientes.append(PerdidaPatrimonialPendiente(
                anio_origen=p_anio, importe_pendiente=p_importe, tipo=p_tipo,
            ))
            st.rerun()
    for i, p in enumerate(st.session_state.perdidas_pendientes):
        c1, c2 = st.columns([5, 1])
        c1.write(f"Pérdida {p.anio_origen}: {p.importe_pendiente}€ ({p.tipo})")
        if c2.button("🗑️", key=f"del_perd_{i}"):
            st.session_state.perdidas_pendientes.pop(i)
            st.rerun()

# ---------------------------------------------------------------------------
# 7. Aportaciones y deducciones
# ---------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Aportaciones a planes de pensiones")
    with st.form("form_aportacion", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ap_importe = c1.number_input("Aportación propia anual (€)", min_value=0.0, value=0.0, key="ap_importe")
        ap_empresa = c2.number_input("Aportación de empresa (€)", min_value=0.0, value=0.0, key="ap_empresa")
        if st.form_submit_button("➕ Añadir aportación"):
            st.session_state.aportaciones.append(AportacionPlanPensiones(
                importe=ap_importe, aportacion_empresa=ap_empresa,
            ))
            st.rerun()
    for i, ap in enumerate(st.session_state.aportaciones):
        c1, c2 = st.columns([5, 1])
        c1.write(f"Aportación {i+1}: {ap.importe}€")
        if c2.button("🗑️", key=f"del_ap_{i}"):
            st.session_state.aportaciones.pop(i)
            st.rerun()

    st.subheader("Otros hechos relevantes para deducciones")
    col1, col2 = st.columns(2)
    with col1:
        h_vivienda_antes_2013 = st.checkbox("Vivienda habitual adquirida antes de 2013 (régimen transitorio)", key="h_vivienda_antes_2013")
        h_base_vivienda = st.number_input("Base anual pagada por esa vivienda (€)", min_value=0.0, value=0.0, key="h_base_vivienda")
        h_madre_trabajadora = st.checkbox("Madre trabajadora con hijo menor de 3 años", key="h_madre_trabajadora")
        h_gastos_guarderia = st.number_input("Gastos de guardería anuales (€)", min_value=0.0, value=0.0, key="h_gastos_guarderia")
        h_donativos = st.number_input("Donativos anuales (€)", min_value=0.0, value=0.0, key="h_donativos")
        h_donativos_recurrente = st.checkbox("Donativos a la misma entidad ≥3 años, importe igual o mayor", key="h_donativos_recurrente")
    with col2:
        h_alquiler_inquilino = st.number_input("Alquiler pagado como inquilino, vivienda habitual (€/año)", min_value=0.0, value=0.0, key="h_alquiler_inquilino")
        h_inquilino_menor_36 = st.checkbox("Inquilino menor de 36 años", key="h_inquilino_menor_36")
        h_inquilino_monoparental = st.checkbox("Familia monoparental (como inquilino)", key="h_inquilino_monoparental")
        h_inquilino_dacion = st.checkbox("Situación de dación en pago", key="h_inquilino_dacion")

# ---------------------------------------------------------------------------
# 8. Resultado
# ---------------------------------------------------------------------------
def construir_perfil(rentas_trabajo_override=None) -> PerfilFiscal:
    """Construye el PerfilFiscal a partir del estado actual de la sesión.
    rentas_trabajo_override permite sustituir la lista de rendimientos del
    trabajo por otra (usado por el simulador de subida salarial) sin tocar
    st.session_state."""
    tipo_decl_map = {
        "Individual": TipoDeclaracion.INDIVIDUAL,
        "Conjunta (biparental)": TipoDeclaracion.CONJUNTA_BIPARENTAL,
        "Conjunta (monoparental)": TipoDeclaracion.CONJUNTA_MONOPARENTAL,
    }
    return PerfilFiscal(
        anio_fiscal=2026,
        es_sintetico=False,
        datos_personales=DatosPersonales(
            edad=st.session_state.get("edad", 30),
            ccaa_residencia="Castilla-La Mancha",
            tipo_declaracion=tipo_decl_map[st.session_state.get("tipo_decl", "Individual")],
            discapacidad_propia=DISCAPACIDAD_LABELS[st.session_state.get("disc_propia", "Ninguna")],
            movilidad_reducida=st.session_state.get("movilidad", False),
            descendientes=st.session_state.descendientes,
            ascendientes=st.session_state.ascendientes,
        ),
        rendimientos_trabajo=rentas_trabajo_override if rentas_trabajo_override is not None else st.session_state.rentas_trabajo,
        inmuebles_arrendados=st.session_state.inmuebles_alquilados,
        inmuebles_no_arrendados=st.session_state.inmuebles_no_alquilados,
        capital_mobiliario=st.session_state.capital_mobiliario,
        actividades_economicas=st.session_state.actividades,
        transmisiones=st.session_state.transmisiones,
        perdidas_pendientes=st.session_state.perdidas_pendientes,
        aportaciones_pensiones=st.session_state.aportaciones,
        hechos_deduccion=HechosDeduccion(
            vivienda_habitual_adquirida_antes_2013=st.session_state.get("h_vivienda_antes_2013", False),
            base_deduccion_vivienda_anual=st.session_state.get("h_base_vivienda", 0.0),
            madre_trabajadora_hijo_menor_3=st.session_state.get("h_madre_trabajadora", False),
            gastos_guarderia_anual=st.session_state.get("h_gastos_guarderia", 0.0),
            donativos_anuales=st.session_state.get("h_donativos", 0.0),
            donativos_misma_entidad_3anios_igual_o_mas=st.session_state.get("h_donativos_recurrente", False),
            alquiler_vivienda_habitual_como_inquilino=st.session_state.get("h_alquiler_inquilino", 0.0),
            inquilino_menor_36=st.session_state.get("h_inquilino_menor_36", False),
            inquilino_monoparental=st.session_state.get("h_inquilino_monoparental", False),
            inquilino_dacion_pago=st.session_state.get("h_inquilino_dacion", False),
        ),
    )


def resumen_bruto_neto(perfil: PerfilFiscal, liq, pagas: int) -> dict:
    bruto_anual = sum(
        [r.integro_anual for r in perfil.rendimientos_trabajo]
        + [i.ingresos_alquiler_anual for i in perfil.inmuebles_arrendados]
        + [a.ingresos for a in perfil.actividades_economicas]
        + [c.importe_bruto for c in perfil.capital_mobiliario]
    )
    cotizaciones = sum(r.cotizaciones_seguridad_social for r in perfil.rendimientos_trabajo)
    impuestos = liq.cuota_resultante
    neto_anual = bruto_anual - cotizaciones - impuestos
    return {
        "bruto_anual": bruto_anual, "cotizaciones": cotizaciones, "impuestos": impuestos,
        "neto_anual": neto_anual, "bruto_mensual": bruto_anual / pagas, "neto_mensual": neto_anual / pagas,
        "tipo_efectivo": (impuestos / bruto_anual * 100) if bruto_anual > 0 else 0.0,
    }


def desglose_por_pagador(perfil: PerfilFiscal, liq, pagas: int, bruto_total_referencia: float) -> list[dict]:
    """Desglosa bruto/cotizaciones (exactos) e IRPF/neto (IRPF asignado
    proporcionalmente al peso de cada pagador sobre el bruto total de TODAS
    las fuentes de renta, ya que el IRPF se calcula de forma conjunta y
    progresiva, no aislada por pagador)."""
    filas = []
    for i, r in enumerate(perfil.rendimientos_trabajo):
        share = (r.integro_anual / bruto_total_referencia) if bruto_total_referencia > 0 else 0.0
        irpf_asignado = liq.cuota_resultante * share
        neto_anual = r.integro_anual - r.cotizaciones_seguridad_social - irpf_asignado
        filas.append({
            "Pagador": f"{i+1}. {r.concepto}",
            "Bruto anual (€)": round(r.integro_anual, 2),
            "Cotizaciones SS (€)": round(r.cotizaciones_seguridad_social, 2),
            "IRPF asignado (€)": round(irpf_asignado, 2),
            "Neto anual (€)": round(neto_anual, 2),
            "Bruto mensual (€)": round(r.integro_anual / pagas, 2),
            "Neto mensual (€)": round(neto_anual / pagas, 2),
        })
    return filas


with tabs[7]:
    st.subheader("Calcular liquidación")
    pagas_resultado = st.selectbox(
        "Pagas al año para el desglose mensual del resultado",
        [12, 14, 15], index=0, key="pagas_resultado",
        help="Solo afecta a cómo se reparte el resultado anual en 'mensual' — el cálculo del IRPF siempre es anual.",
    )
    if st.button("🧮 Calcular", type="primary"):
        st.session_state["_calculado"] = True

    if not st.session_state.get("_calculado"):
        st.info("Rellena los datos en las pestañas anteriores y pulsa Calcular.")
    else:
        perfil = construir_perfil()
        liq = liquidar(perfil, ccaa="Castilla-La Mancha")

        st.markdown("### Bases")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rend. neto trabajo/pensión", f"{liq.rendimiento_neto_trabajo:,.2f} €")
        c2.metric("Rend. neto capital inmobiliario", f"{liq.rendimiento_neto_capital_inmobiliario:,.2f} €")
        c3.metric("Imputación rentas inmobiliarias", f"{liq.imputacion_rentas_inmobiliarias:,.2f} €")
        c4, c5, c6 = st.columns(3)
        c4.metric("Rend. neto actividades económicas", f"{liq.rendimiento_neto_actividades:,.2f} €")
        c5.metric("Rend. neto capital mobiliario", f"{liq.rendimiento_neto_capital_mobiliario:,.2f} €")
        c6.metric("Ganancias patrimoniales netas", f"{liq.ganancias_patrimoniales_netas:,.2f} €")

        st.markdown("### Mínimo y cuotas")
        c1, c2, c3 = st.columns(3)
        c1.metric("Mínimo personal y familiar", f"{liq.minimo_personal_familiar:,.2f} €")
        c2.metric("Cuota líquida estatal", f"{liq.cuota_liquida_estatal:,.2f} €")
        c3.metric("Cuota líquida autonómica", f"{liq.cuota_liquida_autonomica:,.2f} €")

        st.markdown("### Deducciones aplicadas")
        c1, c2 = st.columns(2)
        c1.metric("Deducciones estatales", f"{liq.deducciones_estatales:,.2f} €")
        c2.metric("Deducciones autonómicas CLM", f"{liq.deducciones_autonomicas:,.2f} €")

        st.markdown("### Resultado")
        signo = "A PAGAR" if liq.resultado_declaracion > 0 else "A DEVOLVER"
        color = "red" if liq.resultado_declaracion > 0 else "green"
        st.markdown(f"## :{color}[{abs(liq.resultado_declaracion):,.2f} € — {signo}]")
        st.caption(f"Cuota resultante (total IRPF del año): {liq.cuota_resultante:,.2f} € — Retenciones ya soportadas: {liq.retenciones_totales:,.2f} €")

        st.markdown("### Resumen bruto / neto")
        base = resumen_bruto_neto(perfil, liq, pagas_resultado)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bruto anual (todas las fuentes)", f"{base['bruto_anual']:,.2f} €")
        c2.metric("Neto anual (tras SS e IRPF)", f"{base['neto_anual']:,.2f} €")
        c3.metric(f"Bruto mensual (÷{pagas_resultado})", f"{base['bruto_mensual']:,.2f} €")
        c4.metric(f"Neto mensual (÷{pagas_resultado})", f"{base['neto_mensual']:,.2f} €")
        c5, c6, c7 = st.columns(3)
        c5.metric("Total impuestos (IRPF del año)", f"{base['impuestos']:,.2f} €")
        c6.metric("Total cotizaciones SS", f"{base['cotizaciones']:,.2f} €")
        c7.metric("Tipo efectivo medio", f"{base['tipo_efectivo']:.1f} %")
        st.caption(
            "Bruto anual = suma de todos los ingresos íntegros (trabajo, alquiler, "
            "actividad económica, capital mobiliario). No incluye ganancias "
            "patrimoniales (ventas), que se muestran aparte más arriba. "
            "Neto = bruto − cotizaciones SS − IRPF total del año."
        )

        if perfil.rendimientos_trabajo:
            st.markdown("#### Desglose por pagador")
            st.caption(
                "Bruto y cotizaciones son exactos por pagador. El IRPF (y por tanto "
                "el neto) se asigna proporcionalmente al peso de cada pagador sobre "
                "el total de ingresos brutos, porque el IRPF real se calcula de "
                "forma conjunta y progresiva sobre toda tu declaración, no aislado "
                "por pagador — es una estimación de reparto, no un cálculo independiente."
            )
            st.dataframe(
                desglose_por_pagador(perfil, liq, pagas_resultado, base["bruto_anual"]),
                hide_index=True, use_container_width=True,
            )

        for aviso in liq.avisos:
            st.warning(aviso)

        # -------------------------------------------------------------
        # Simulador de subida salarial
        # -------------------------------------------------------------
        st.divider()
        st.markdown("## 📈 Simulador de subida salarial")
        st.caption(
            "Define una subida (o ninguna, dejando el bruto mensual igual) para cada "
            "pagador. Recalcula la liquidación completa del año con todos los cambios "
            "a la vez, así que el efecto en cotizaciones e IRPF respeta la "
            "progresividad real: la suma de las subidas tributa al tipo marginal que "
            "le corresponde sobre el conjunto de tus ingresos, no a tu tipo medio."
        )

        if not perfil.rendimientos_trabajo:
            st.info("Añade al menos un pagador en la pestaña 'Trabajo/Pensión' para poder simular una subida.")
        else:
            rentas_trabajo_escenario = list(perfil.rendimientos_trabajo)
            nuevos_brutos_mensuales = []

            for i, entry in enumerate(perfil.rendimientos_trabajo):
                st.markdown(f"**Pagador {i+1}: {entry.concepto} — {entry.integro_anual:,.2f} €/año actuales**")
                c1, c2, c3 = st.columns(3)
                pagas_job = c1.selectbox("Pagas/año", [12, 14, 15], index=0, key=f"sim_pagas_job_{i}")
                bruto_mensual_actual = entry.integro_anual / pagas_job
                c1.caption(f"Bruto mensual actual: {bruto_mensual_actual:,.2f} €")

                modo_sim = c2.radio("Definir por", ["Bruto mensual", "Bruto anual", "% incremento"], key=f"sim_modo_{i}", horizontal=True)
                if modo_sim == "Bruto mensual":
                    nuevo_bruto_mensual = c3.number_input(
                        "Nuevo bruto mensual (€)", min_value=0.0,
                        value=round(bruto_mensual_actual, 2), step=10.0, key=f"sim_nuevo_bruto_{i}",
                    )
                elif modo_sim == "Bruto anual":
                    nuevo_bruto_anual_input = c3.number_input(
                        "Nuevo bruto anual (€)", min_value=0.0,
                        value=round(entry.integro_anual, 2), step=100.0, key=f"sim_nuevo_bruto_anual_{i}",
                    )
                    nuevo_bruto_mensual = nuevo_bruto_anual_input / pagas_job
                    c3.caption(f"→ Equivale a {nuevo_bruto_mensual:,.2f} €/mes con {pagas_job} pagas")
                else:
                    pct_subida = c3.number_input("% incremento", min_value=-100.0, value=0.0, step=1.0, key=f"sim_pct_{i}")
                    nuevo_bruto_mensual = bruto_mensual_actual * (1 + pct_subida / 100)
                    c3.caption(f"→ Nuevo bruto mensual: {nuevo_bruto_mensual:,.2f} €")

                nuevos_brutos_mensuales.append((nuevo_bruto_mensual, pagas_job))
                nuevo_integro_anual = nuevo_bruto_mensual * pagas_job
                factor = (nuevo_integro_anual / entry.integro_anual) if entry.integro_anual > 0 else 1.0

                rentas_trabajo_escenario[i] = RendimientoTrabajo(
                    concepto=entry.concepto,
                    integro_anual=nuevo_integro_anual,
                    retenciones_soportadas=entry.retenciones_soportadas * factor,
                    cotizaciones_seguridad_social=entry.cotizaciones_seguridad_social * factor,
                    es_renta_irregular=entry.es_renta_irregular,
                    anios_generacion=entry.anios_generacion,
                    en_situacion_desempleo_con_movilidad=entry.en_situacion_desempleo_con_movilidad,
                )
                st.divider()

            perfil_escenario = construir_perfil(rentas_trabajo_override=rentas_trabajo_escenario)
            liq_escenario = liquidar(perfil_escenario, ccaa="Castilla-La Mancha")
            escenario = resumen_bruto_neto(perfil_escenario, liq_escenario, pagas_resultado)

            delta_bruto_anual = escenario["bruto_anual"] - base["bruto_anual"]
            delta_neto_anual = escenario["neto_anual"] - base["neto_anual"]
            delta_impuestos = escenario["impuestos"] - base["impuestos"]
            delta_cotizaciones = escenario["cotizaciones"] - base["cotizaciones"]
            tipo_marginal_subida = (
                (delta_impuestos + delta_cotizaciones) / delta_bruto_anual * 100
                if delta_bruto_anual != 0 else 0.0
            )

            st.markdown("#### Comparativa Actual vs. Escenario (todas las subidas combinadas)")
            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Bruto anual total tras las subidas", f"{escenario['bruto_anual']:,.2f} €",
                delta=f"{delta_bruto_anual:+,.2f} €",
            )
            c2.metric(
                "Neto mensual", f"{escenario['neto_mensual']:,.2f} €",
                delta=f"{escenario['neto_mensual'] - base['neto_mensual']:+,.2f} €",
            )
            c3.metric(
                "Bruto mensual", f"{escenario['bruto_mensual']:,.2f} €",
                delta=f"{escenario['bruto_mensual'] - base['bruto_mensual']:+,.2f} €",
            )

            c4, c5, c6 = st.columns(3)
            c4.metric(
                "IRPF total del año", f"{escenario['impuestos']:,.2f} €",
                delta=f"{delta_impuestos:+,.2f} €", delta_color="inverse",
            )
            c5.metric(
                "Cotizaciones SS del año", f"{escenario['cotizaciones']:,.2f} €",
                delta=f"{delta_cotizaciones:+,.2f} €", delta_color="inverse",
            )
            c6.metric(
                "Neto anual", f"{escenario['neto_anual']:,.2f} €",
                delta=f"{delta_neto_anual:+,.2f} €",
            )

            st.metric(
                "% de la subida total que 'se va' en SS+IRPF",
                f"{tipo_marginal_subida:.1f} %",
                help="(Δ cotizaciones + Δ IRPF) / Δ bruto anual. Tipo marginal real del conjunto de subidas, no tu tipo medio.",
            )

            if delta_bruto_anual != 0:
                st.caption(
                    f"De cada 100 € brutos adicionales (sumando todas las subidas), te quedan netos "
                    f"aproximadamente **{100 - tipo_marginal_subida:.1f} €** — el resto "
                    f"({tipo_marginal_subida:.1f} €) va a cotizaciones SS e IRPF adicional "
                    f"(calculado sobre el conjunto de tu declaración, no de forma aislada por pagador)."
                )

            st.markdown("#### Resultado de la declaración con este escenario")
            signo_esc = "A PAGAR" if liq_escenario.resultado_declaracion > 0 else "A DEVOLVER"
            color_esc = "red" if liq_escenario.resultado_declaracion > 0 else "green"
            delta_resultado = liq_escenario.resultado_declaracion - liq.resultado_declaracion
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"### :{color_esc}[{abs(liq_escenario.resultado_declaracion):,.2f} € — {signo_esc}]")
                st.caption(
                    f"Actual: {abs(liq.resultado_declaracion):,.2f} € "
                    f"({'A PAGAR' if liq.resultado_declaracion > 0 else 'A DEVOLVER'}) "
                    f"→ Variación: {delta_resultado:+,.2f} € "
                    f"({'más a pagar / menos a devolver' if delta_resultado > 0 else 'menos a pagar / más a devolver'})"
                )
            with c2:
                st.metric("Retenciones soportadas (año, escaladas proporcionalmente)", f"{liq_escenario.retenciones_totales:,.2f} €")
                st.caption(
                    "Las retenciones del escenario se han escalado en la misma "
                    "proporción que el aumento de bruto de cada pagador — es una "
                    "aproximación, ya que la retención real depende de la tabla de "
                    "retenciones aplicada por cada empresa, que puede no ser exactamente "
                    "proporcional al salario. El importe A PAGAR/A DEVOLVER final real "
                    "dependerá de la retención efectiva que te apliquen."
                )

            st.markdown("#### Desglose por pagador tras las subidas")
            st.dataframe(
                desglose_por_pagador(perfil_escenario, liq_escenario, pagas_resultado, escenario["bruto_anual"]),
                hide_index=True, use_container_width=True,
            )

