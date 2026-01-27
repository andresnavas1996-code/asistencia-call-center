import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- 1. CONFIGURACIÓN DE EQUIPOS (Edita aquí los nombres) ---
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

# Configuración del horario (Lo dejé hasta las 11:59 PM para que pruebes ahora)
HORA_INICIO = time(0, 0)   # Desde medianoche
HORA_FIN = time(23, 59)    # Hasta el final del día
ARCHIVO_DATOS = 'asistencia_historica.csv'

# --- 2. FUNCIONES DE CARGA Y GUARDADO ---
def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    else:
        return pd.DataFrame(columns=["Fecha", "Equipo", "Nombre", "Estado", "Observacion"])

def guardar_asistencia(df_nuevo):
    df_historico = cargar_datos()
    df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
    df_final.to_csv(ARCHIVO_DATOS, index=False)
    return df_final

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="Control de Asistencia", layout="wide")
st.title("📋 Malla de Asistencia Diaria - Multiequipos")

# Pestañas
tab_asistencia, tab_dashboard = st.tabs(["⚡ Registrar Asistencia", "📊 Dashboard y Reportes"])

with tab_asistencia:
    ahora = datetime.now().time()
    
    if HORA_INICIO <= ahora <= HORA_FIN:
        st.success(f"Sistema ABIERTO. Tienes hasta las {HORA_FIN} para gestionar.")
        
        # Selector de equipo
        equipo_sel = st.selectbox("Selecciona tu Equipo:", list(EQUIPOS.keys()))
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        st.write(f"### 👥 {equipo_sel} - Fecha: {fecha_hoy}")
        
        # Crear datos iniciales
        datos_equipo = []
        for persona in EQUIPOS[equipo_sel]:
            datos_equipo.append({
                "Fecha": fecha_hoy,
                "Equipo": equipo_sel,
                "Nombre": persona,
                "Estado": "Presente", 
                "Observacion": ""
            })
        
        df_input = pd.DataFrame(datos_equipo)
        
        # Editor interactivo
        df_editado = st.data_editor(
            df_input,
            column_config={
                "Estado": st.column_config.SelectboxColumn(
                    "Estado",
                    options=["Presente", "Ausente", "Tarde", "Licencia", "Vacaciones"],
                    required=True
                ),
                "Observacion": st.column_config.TextColumn("Observación")
            },
            hide_index=True,
            num_rows="fixed",
            use_container_width=True
        )
        
        if st.button("💾 Guardar Asistencia"):
            guardar_asistencia(df_editado)
            st.toast(f"✅ Asistencia de {equipo_sel} guardada con éxito!")
            
    else:
        st.error(f"⛔ El sistema está CERRADO. Horario: {HORA_INICIO} a {HORA_FIN}.")

with tab_dashboard:
    st.header("📊 Reporte General")
    df = cargar_datos()
    
    if not df.empty:
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_equipo = st.multiselect("Filtrar por Equipo:", df["Equipo"].unique(), default=df["Equipo"].unique())
        with col2:
            filtro_estado = st.multiselect("Filtrar por Estado:", df["Estado"].unique(), default=df["Estado"].unique())
        with col3:
            fechas_disp = sorted(df["Fecha"].unique())
            filtro_fecha = st.selectbox("Filtrar por Fecha:", fechas_disp, index=len(fechas_disp)-1)
        
        # Aplicar filtros
        df_filtrado = df[
            df["Equipo"].isin(filtro_equipo) & 
            df["Estado"].isin(filtro_estado) & 
            (df["Fecha"] == filtro_fecha)
        ]
        
        # Métricas
        total = len(df_filtrado)
        presentes = len(df_filtrado[df_filtrado['Estado'] == 'Presente'])
        ausentes = len(df_filtrado[df_filtrado['Estado'] == 'Ausente'])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Personas", total)
        m2.metric("✅ Presentes", presentes)
        m3.metric("❌ Ausentes", ausentes, delta_color="inverse")
        m4.metric("📅 Fecha", filtro_fecha)
        
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.info("Aún no hay datos registrados.")
