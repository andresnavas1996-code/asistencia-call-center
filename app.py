import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN ---
EQUIPOS = {
    "Callcenter Bucaramanga": ["Ana", "Carlos", "Beatriz", "David"],
    "Callcenter Medellin": ["Elena", "Fernando", "Gabriela"],
    "Callcenter Bogota": ["Hugo", "Inés", "Javier"],
    "Servicio al cliente": ["Kevin", "Laura", "Marta"],
    "CallcenterMayoreo Medellin": ["Nancy", "Oscar", "Pablo"],
    "Campo 6": ["Empleado 1", "Empleado 2"],
    "Campo 7": ["Empleado A", "Empleado B"],
    "Campo 8": ["Persona X", "Persona Y"],
    "Campo 9": ["Agente 1", "Agente 2"],
    "Campo 10": ["Nombre 1", "Nombre 2"],
    "Campo 11": ["Test 1", "Test 2"]
}

HORA_INICIO = time(0, 0)
HORA_FIN = time(23, 59)
ARCHIVO_DATOS = 'asistencia_historica.csv'

def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    return pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Estado", "Observacion"])

def guardar_asistencia(df_nuevo):
    df_historico = cargar_datos()
    df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_DATOS, index=False)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Asistencia", layout="wide")
st.title("📋 Malla de Asistencia Diaria - Dinámica")

# Crea las pestañas
tab_asistencia, tab_dashboard = st.tabs(["⚡ Registrar Asistencia", "📊 Dashboard"])

# --- PESTAÑA DE REGISTRO ---
with tab_asistencia:
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            equipo_sel = st.selectbox("Selecciona tu Equipo:", list(EQUIPOS.keys()))
        
        st.info("💡 Usa la fila vacía al final para agregar personas nuevas.")
        
        # Prepara los datos base
        datos = [{"Nombre": p, "Estado": "Presente", "Observacion": ""} for p in EQUIPOS[equipo_sel]]
        df_input = pd.DataFrame(datos)
        
        # Muestra la tabla editable
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre", required=True),
                "Estado": st.column_config.SelectboxColumn("Estado", options=["Presente", "Ausente", "Tarde", "Licencia"], required=True),
                "Observacion": st.column_config.TextColumn("Observación")
            },
            hide_index=True,
            num_rows="dynamic",
            use_container_width=True
        )
        
        # Botón de guardar
        if st.button("💾 Guardar Asistencia"):
            if not df_editado.empty:
                df_final = df_editado.copy()
                df_final["Fecha"] = datetime.now().strftime("%Y-%m-%d")
                df_final["Equipo"] = equipo_sel
                guardar_asistencia(df_final[["Fecha", "Equipo", "Nombre", "Estado", "Observacion"]])
                st.toast("✅ ¡Guardado con éxito!")
    else:
        st.error(f"⛔ Sistema Cerrado ({HORA_INICIO} - {HORA_FIN})")

# --- PESTAÑA DE DASHBOARD ---
with tab_dashboard:
    df = cargar_datos()
    if not df.empty:
        st.metric("Total Registros", len(df))
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aún no hay datos.")
